import os
import sys
import uuid
import time
import tempfile
import threading
import shutil
import logging
import json
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
import yt_dlp
from spotify_agent import (
    SpotifyAgentError,
    approved_download_context,
    create_authorization,
    exchange_code,
    get_catalog,
    import_saved_tracks,
    search_candidates,
)

# ─── Logging Setup ──────────────────────────────────────────────────────────
DROPS_DIR = Path(os.environ.get("DROPS_STATE_DIR", str(Path.home() / ".drops"))).expanduser()
DROPS_DIR.mkdir(exist_ok=True)
LOGS_DIR = DROPS_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("drops")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    LOGS_DIR / "backend.log",
    maxBytes=10_000_000,
    backupCount=5,
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ─── Cookies ────────────────────────────────────────────────────────────────
COOKIES_FILE = DROPS_DIR / "cookies.txt"

# ─── ffmpeg: discovery cross-platform ────────────────────────────────────────
IS_WINDOWS = os.name == "nt"
FFMPEG_EXE = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"

# Su macOS/Linux forziamo i path Homebrew nel PATH (comportamento storico).
_BREW_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
if not IS_WINDOWS:
    os.environ["PATH"] = os.pathsep.join(_BREW_PATHS) + os.pathsep + os.environ.get("PATH", "")


def find_ffmpeg() -> str | None:
    # 1) cartella impacchettata dal wrapper desktop (Tauri su Windows passa DROPS_FFMPEG_DIR)
    bundled = os.environ.get("DROPS_FFMPEG_DIR")
    if bundled and Path(bundled, FFMPEG_EXE).exists():
        return bundled
    # 2) path Homebrew noti (macOS)
    if not IS_WINDOWS:
        for folder in _BREW_PATHS:
            if Path(folder, FFMPEG_EXE).exists():
                return folder
    # 3) ffmpeg presente nel PATH di sistema
    found = shutil.which("ffmpeg")
    return str(Path(found).parent) if found else None


FFMPEG_LOCATION = find_ffmpeg()

# ─── Config ─────────────────────────────────────────────────────────────────
DOWNLOAD_DIR = Path(
    os.environ.get("DROPS_DOWNLOAD_DIR", str(Path(tempfile.gettempdir()) / "drops-downloads"))
)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_CONCURRENT = 3
FILE_TTL = 600  # 10 minuti

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Drops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── State ──────────────────────────────────────────────────────────────────
jobs: dict = {}
semaphore = threading.Semaphore(MAX_CONCURRENT)

ALLOWED_DOMAINS = [
    "youtube.com", "youtu.be",
    "soundcloud.com",
    "music.youtube.com",
]

AUDIO_QUALITY_MAP = {
    "128": ("mp3", "128"),
    "192": ("mp3", "192"),
    "320": ("mp3", "0"),   # 0 = VBR best
    "flac": ("flac", None),
}

VIDEO_FORMAT_MAP = {
    "1080": "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080][ext=mp4]/best[height<=1080]",
    "720":  "bestvideo[height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720][ext=mp4]/best[height<=720]",
    "480":  "bestvideo[height<=480][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480][ext=mp4]/best[height<=480]",
}

# ─── Models ─────────────────────────────────────────────────────────────────
class DownloadRequest(BaseModel):
    url: str
    quality: str = "320"
    password: str | None = None          # opzionale (app locale)
    format: str = "audio"                # "audio" | "video"
    video_quality: str = "1080"          # "1080" | "720" | "480"
    start_time: int | None = None        # secondi (clip)
    duration: int | None = None          # secondi (clip)
    spotify_track_id: str | None = None
    rights_confirmed: bool = False


# ─── Helpers ────────────────────────────────────────────────────────────────
def cleanup_old_files():
    now = time.time()
    to_delete = []
    for job_id, job in list(jobs.items()):
        if now - job["created_at"] > FILE_TTL:
            fp = job.get("file_path")
            if fp and os.path.exists(fp) and not job.get("library_path"):
                try:
                    os.remove(fp)
                except Exception:
                    pass
            to_delete.append(job_id)
    for jid in to_delete:
        jobs.pop(jid, None)


def safe_filename(name: str, ext: str) -> str:
    clean = "".join(c for c in name if c.isalnum() or c in " .-_()[]").strip()
    clean = clean[:80]
    return f"{clean}.{ext}" if clean else f"audio.{ext}"


def ffmpeg_bin() -> str:
    if FFMPEG_LOCATION:
        return str(Path(FFMPEG_LOCATION) / FFMPEG_EXE)
    return FFMPEG_EXE


def trim_file(input_path: Path, output_path: Path, start: int, dur: int, is_video: bool) -> bool:
    """Ritaglia start → start+dur dal file. Ritorna True se ok."""
    cmd = [ffmpeg_bin(), "-ss", str(start), "-i", str(input_path), "-t", str(dur)]
    if is_video:
        # Re-encode per allineamento keyframe preciso
        cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]
    cmd += ["-y", str(output_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg trim error: {result.stderr[:300]}")
    return result.returncode == 0 and output_path.exists()


def do_download(
    job_id: str,
    url: str,
    quality: str,
    fmt: str = "audio",
    video_quality: str = "1080",
    start_time: int | None = None,
    duration: int | None = None,
    library_context: dict | None = None,
):
    with semaphore:
        try:
            jobs[job_id]["status"] = "downloading"
            is_clip = start_time is not None and duration is not None
            is_video = fmt == "video"

            logger.info(
                f"Download - Job:{job_id} fmt:{fmt} q:{quality if not is_video else video_quality}"
                + (f" clip:{start_time}s+{duration}s" if is_clip else "")
            )

            # Pre-fetch metadata per stimare size attesa
            # Saltato per i clip: sono brevi, il progress_hook yt-dlp è sufficiente
            # e il round-trip a YouTube aggiunge 3-5s di latenza inutile
            expected_bytes = None
            if not is_clip:
                try:
                    t0 = time.time()
                    meta_opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
                    with yt_dlp.YoutubeDL(meta_opts) as ydl_meta:
                        meta = ydl_meta.extract_info(url, download=False)
                        full_duration = meta.get("duration") or 0
                        section_secs = full_duration
                        if section_secs > 0:
                            formats = meta.get("formats", []) or []

                            def fmt_bytes(f):
                                """Stima byte di un format: filesize esatto se presente, altrimenti tbr * duration."""
                                fs = f.get("filesize") or f.get("filesize_approx")
                                if fs:
                                    return int(fs * section_secs / full_duration) if full_duration else fs
                                tbr = f.get("tbr") or f.get("vbr") or f.get("abr") or 0
                                return int(tbr * 1000 / 8 * section_secs)

                            if is_video:
                                max_h = int(video_quality)
                                video_fmts = [f for f in formats
                                              if f.get("vcodec") not in (None, "none")
                                              and (f.get("height") or 0) <= max_h
                                              and (f.get("height") or 0) > 0]
                                audio_fmts = [f for f in formats
                                              if f.get("acodec") not in (None, "none")
                                              and f.get("vcodec") in (None, "none")]
                                best_v = max(video_fmts, key=lambda f: f.get("height") or 0, default=None)
                                best_a = max(audio_fmts, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
                                v_bytes = fmt_bytes(best_v) if best_v else 0
                                a_bytes = fmt_bytes(best_a) if best_a else 0
                                expected_bytes = int((v_bytes + a_bytes) * 1.05)
                            else:
                                audio_fmts = [f for f in formats if f.get("acodec") not in (None, "none")]
                                best_a = max(audio_fmts, key=lambda f: f.get("abr") or f.get("tbr") or 0, default=None)
                                expected_bytes = fmt_bytes(best_a) if best_a else 0

                            if expected_bytes and expected_bytes > 0:
                                jobs[job_id]["expected_bytes"] = expected_bytes
                            jobs[job_id]["title"] = meta.get("title")
                    logger.debug(f"Pre-fetch metadata - Job:{job_id} - {time.time()-t0:.1f}s")
                except Exception as e:
                    logger.warning(f"Pre-fetch metadata fallito - Job:{job_id}: {e}")

            def progress_hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    jobs[job_id]["downloaded_bytes"] = downloaded
                    if total > 0:
                        pct = int(downloaded * 100 / total)
                        jobs[job_id]["progress"] = min(pct, 99)
                    elif d.get("fragment_index") and d.get("fragment_count"):
                        pct = int(d["fragment_index"] * 100 / d["fragment_count"])
                        jobs[job_id]["progress"] = min(pct, 99)
                elif d.get("status") == "finished":
                    jobs[job_id]["progress"] = 99

            # Monitor thread: scansiona file su disco per progress fallback
            # (utile con download_ranges + external_downloader=ffmpeg dove progress_hook non si attiva)
            stop_monitor = threading.Event()
            def monitor_part_file():
                while not stop_monitor.wait(0.5):
                    try:
                        files = [p for p in DOWNLOAD_DIR.glob(f"{job_id}*") if p.is_file()]
                        if files:
                            total_size = sum(p.stat().st_size for p in files)
                            if total_size > jobs[job_id].get("downloaded_bytes", 0):
                                jobs[job_id]["downloaded_bytes"] = total_size
                    except Exception:
                        pass
            monitor_thread = threading.Thread(target=monitor_part_file, daemon=True)
            monitor_thread.start()

            output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
            cookies = str(COOKIES_FILE) if COOKIES_FILE.exists() else None
            ffmpeg_kw = {"ffmpeg_location": FFMPEG_LOCATION} if FFMPEG_LOCATION else {}

            # download_ranges: scarica solo la sezione richiesta (evita download dell'intero video per clip)
            download_ranges = None
            if is_clip:
                end_time = start_time + duration
                def _ranges(info_dict, ydl):
                    return [{"start_time": start_time, "end_time": end_time}]
                download_ranges = _ranges

            if is_video:
                video_fmt = VIDEO_FORMAT_MAP.get(video_quality, VIDEO_FORMAT_MAP["1080"])
                ydl_opts = {
                    "format": video_fmt,
                    "merge_output_format": "mp4",
                    "outtmpl": output_template,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "socket_timeout": 30,
                    "cookiefile": cookies,
                    "progress_hooks": [progress_hook],
                    "concurrent_fragment_downloads": 4,
                    **ffmpeg_kw,
                }
                if download_ranges:
                    ydl_opts["download_ranges"] = download_ranges
                    # force_keyframes_at_cuts: yt-dlp forza un keyframe al punto di taglio
                    # → il muxing ffmpeg è più preciso e veloce, evita secondi extra scaricati
                    ydl_opts["force_keyframes_at_cuts"] = True
                output_ext = "mp4"
            else:
                codec, q = AUDIO_QUALITY_MAP.get(quality, ("mp3", "0"))
                if codec == "flac":
                    postprocessors = [{"key": "FFmpegExtractAudio", "preferredcodec": "flac"}]
                    output_ext = "flac"
                else:
                    postprocessors = [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": q,
                    }]
                    output_ext = "mp3"

                ydl_opts = {
                    "format": "bestaudio/best",
                    "postprocessors": postprocessors,
                    "outtmpl": output_template,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "socket_timeout": 30,
                    "cookiefile": cookies,
                    "progress_hooks": [progress_hook],
                    "concurrent_fragment_downloads": 4,
                    **ffmpeg_kw,
                }
                if download_ranges:
                    ydl_opts["download_ranges"] = download_ranges

            try:
                t_start = time.time()
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "audio")
                    total_duration = info.get("duration", 0)
                logger.info(f"yt-dlp completato - Job:{job_id} - {time.time()-t_start:.1f}s")
            finally:
                stop_monitor.set()

            # Trova file reale prodotto da yt-dlp/ffmpeg (estensione può differire dall'attesa)
            candidates = sorted(
                DOWNLOAD_DIR.glob(f"{job_id}.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            # Filtra file .part residui
            candidates = [p for p in candidates if not p.name.endswith(".part")]

            if not candidates:
                jobs[job_id].update({"status": "error", "error": "File non trovato dopo il download"})
                logger.error(f"File mancante - Job:{job_id} - glob vuoto in {DOWNLOAD_DIR}")
                return

            file_path = candidates[0]
            actual_ext = file_path.suffix.lstrip(".")
            if actual_ext != output_ext:
                logger.warning(f"Estensione diversa da attesa - Job:{job_id} atteso:{output_ext} reale:{actual_ext}")
                output_ext = actual_ext

            # Trim post-download solo se download_ranges non era disponibile (yt-dlp ha già tagliato)
            # download_ranges scarica solo la sezione richiesta → niente trim necessario
            if is_clip and not download_ranges:
                trimmed_path = DOWNLOAD_DIR / f"{job_id}_trimmed.{output_ext}"
                ok = trim_file(file_path, trimmed_path, start_time, duration, is_video)
                if ok:
                    file_path.unlink()
                    file_path = trimmed_path
                    logger.info(f"Trim completato - Job:{job_id}")
                else:
                    logger.warning(f"Trim fallito, uso file completo - Job:{job_id}")

            size = file_path.stat().st_size
            final_duration = duration if is_clip else total_duration

            if library_context:
                target_dir = Path(library_context["target_dir"]).expanduser()
                target_dir.mkdir(parents=True, exist_ok=True)
                artist = safe_filename(" - ".join(library_context["artists"]), "").rstrip(".")
                track_name = safe_filename(library_context["name"], output_ext)
                destination = target_dir / f"{artist} - {track_name}"
                counter = 2
                while destination.exists():
                    destination = (
                        target_dir
                        / f"{artist} - {Path(track_name).stem} ({counter}).{output_ext}"
                    )
                    counter += 1
                shutil.move(str(file_path), destination)
                file_path = destination
                size = file_path.stat().st_size

            jobs[job_id].update({
                "status": "ready",
                "file_path": str(file_path),
                "title": title,
                "duration": final_duration,
                "size": size,
                "ext": output_ext,
                "format": fmt,
                "progress": 100,
                "library_path": str(file_path) if library_context else None,
            })
            logger.info(f"Pronto - Job:{job_id} '{title}' {size} bytes")

        except Exception as e:
            jobs[job_id].update({"status": "error", "error": str(e)})
            logger.error(f"Eccezione - Job:{job_id}", exc_info=True)


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    active = sum(1 for j in jobs.values() if j["status"] in ("pending", "downloading"))
    return {"status": "ok", "active_jobs": active, "total_jobs": len(jobs)}


@app.get("/auth-token")
def auth_token():
    """Endpoint di compatibilità – app locale, nessuna autenticazione reale."""
    return {"token": "local-drops"}


@app.post("/download")
def start_download(req: DownloadRequest):
    cleanup_old_files()

    if not any(d in req.url for d in ALLOWED_DOMAINS):
        raise HTTPException(status_code=400, detail="URL non supportato. Usa YouTube o SoundCloud.")

    if req.format == "audio" and req.quality not in AUDIO_QUALITY_MAP:
        raise HTTPException(status_code=400, detail="Qualità audio non valida")

    if req.format == "video" and req.video_quality not in VIDEO_FORMAT_MAP:
        raise HTTPException(status_code=400, detail="Qualità video non valida")

    active = sum(1 for j in jobs.values() if j["status"] in ("pending", "downloading"))
    if active >= MAX_CONCURRENT:
        raise HTTPException(status_code=429, detail="Troppi download in corso, riprova tra 30 secondi")

    library_context = None
    if req.spotify_track_id:
        if not req.rights_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Conferma di possedere diritti o autorizzazione richiesta",
            )
        try:
            library_context = approved_download_context(req.spotify_track_id, req.url)
        except SpotifyAgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "title": None,
        "file_path": None,
        "error": None,
        "created_at": time.time(),
        "quality": req.quality,
        "format": req.format,
        "video_quality": req.video_quality,
        "size": None,
        "duration": None,
        "ext": None,
        "progress": 0,
        "library_path": None,
    }

    t = threading.Thread(
        target=do_download,
        args=(
            job_id,
            req.url,
            req.quality,
            req.format,
            req.video_quality,
            req.start_time,
            req.duration,
            library_context,
        ),
        daemon=True,
    )
    t.start()

    return {"job_id": job_id}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job non trovato")
    j = jobs[job_id]
    return {
        "status": j["status"],
        "title": j["title"],
        "error": j["error"],
        "size": j["size"],
        "duration": j["duration"],
        "quality": j["quality"],
        "video_quality": j.get("video_quality"),
        "format": j.get("format", "audio"),
        "ext": j.get("ext"),
        "progress": j.get("progress", 0),
        "downloaded_bytes": j.get("downloaded_bytes", 0),
        "expected_bytes": j.get("expected_bytes", 0),
        "library_path": j.get("library_path"),
    }


@app.get("/spotify/connect")
def spotify_connect():
    try:
        authorization = create_authorization()
        return RedirectResponse(authorization["authorization_url"])
    except SpotifyAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/spotify/callback")
def spotify_callback(code: str, state: str):
    try:
        exchange_code(code, state)
    except SpotifyAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(
        "<h1>Spotify collegato a Drops</h1>"
        "<p>Chiudi questa finestra e importa tutti i preferiti.</p>"
    )


@app.post("/spotify/import")
def spotify_import():
    try:
        return import_saved_tracks()
    except SpotifyAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/spotify/library")
def spotify_library(offset: int = 0, limit: int = 100):
    return get_catalog(max(offset, 0), max(1, min(limit, 500)))


@app.post("/spotify/library/{track_id}/candidates")
def spotify_candidates(track_id: str, limit: int = 5):
    try:
        return search_candidates(track_id, limit)
    except SpotifyAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/file/{job_id}")
def get_file(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job non trovato")

    j = jobs[job_id]
    if j["status"] != "ready":
        raise HTTPException(status_code=400, detail="File non ancora pronto")

    fp = j.get("file_path")
    if not fp or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="File non trovato sul server")

    if j.get("library_path"):
        return FileResponse(
            fp,
            media_type="audio/flac" if j.get("ext") == "flac" else "audio/mpeg",
            filename=Path(fp).name,
        )

    ext = j.get("ext", "mp3")
    filename = safe_filename(j["title"] or "audio", ext)

    if ext == "mp4":
        media_type = "video/mp4"
    elif ext == "flac":
        media_type = "audio/flac"
    else:
        media_type = "audio/mpeg"

    def delete_after():
        time.sleep(5)
        try:
            os.remove(fp)
        except Exception:
            pass
        jobs.pop(job_id, None)

    background_tasks.add_task(delete_after)
    return FileResponse(fp, media_type=media_type, filename=filename)


def _frontend_index_path() -> Path | None:
    """Trova frontend/index.html sia in dev che nell'exe PyInstaller (frozen).

    In modalità frozen (Windows/DMG impacchettato) i file sono estratti in
    sys._MEIPASS e il layout relativo a __file__ non esiste. Proviamo più
    posizioni candidate e restituiamo la prima esistente.
    """
    candidates = []
    if getattr(sys, "frozen", False):
        # PyInstaller: risorse estratte in _MEIPASS, e file accanto all'exe
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "frontend" / "index.html")
        candidates.append(Path(sys.executable).parent / "frontend" / "index.html")
    # Dev / sorgente: backend/../frontend/index.html
    candidates.append(Path(__file__).parent.parent / "frontend" / "index.html")
    for p in candidates:
        if p.is_file():
            return p
    return None


@app.get("/")
def serve_frontend():
    html_path = _frontend_index_path()
    if html_path is None:
        logger.error("index.html non trovato (frozen=%s)", getattr(sys, "frozen", False))
        raise HTTPException(status_code=500, detail="Frontend non trovato nell'installazione.")
    content = html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)
