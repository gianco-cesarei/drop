"""Import Spotify favorites as metadata and prepare authorized Drops jobs."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yt_dlp

SPOTIFY_AUTHORIZE = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_API = "https://api.spotify.com/v1"
SCOPE = "user-library-read"

DROPS_HOME = Path(
    os.environ.get("DROPS_STATE_DIR", str(Path.home() / ".drops"))
).expanduser()
TOKEN_FILE = DROPS_HOME / "spotify-token.json"
CATALOG_FILE = DROPS_HOME / "spotify-library.json"
ARTIST_CACHE_FILE = DROPS_HOME / "spotify-artist-genres.json"
MUSIC_ROOT = Path(
    os.environ.get("DROPS_MUSIC_DIR", str(Path.home() / "Documents" / "Music Gianco"))
).expanduser()

GENRE_RULES = (
    (("italo", "hi-nrg"), "Italo Disco - Hi-NRG"),
    (("french house", "filter house"), "French Touch"),
    (("deep house",), "Deep House"),
    (("tech house",), "Tech House"),
    (("house",), "House"),
    (("synthpop", "synth-pop", "new wave", "post-punk"), "Synth-pop - Post-punk"),
    (("neo soul", "neo-soul", "soul", "r&b"), "Soul - R&B"),
    (("trip hop", "trip-hop"), "Trip-hop"),
    (("ambient",), "Ambient"),
    (("progressive rock", "psychedelic rock"), "Progressive - Psychedelic Rock"),
    (("alternative rock", "nu metal", "nu-metal"), "Alternative Rock - Nu-metal"),
    (("rock",), "Rock"),
    (("jazz", "funk"), "Jazz - Funk"),
    # --- Regole aggiunte per recuperare gli "Altri Generi" (ordine: specifico
    #     prima di generico; "electronic" resta ultimo come fallback). ---
    (("hip hop", "hip-hop", "rap", "trap", "grime"), "Hip-hop - Rap"),
    (("techno",), "Techno"),
    (("nu disco", "nu-disco", "disco"), "Disco - Nu-disco"),
    (("punk", "ska"), "Punk - Ska"),
    (("latin", "reggaeton", "ranchera", "cumbia", "salsa"), "Latin"),
    (("pop",), "Pop"),
    (("electronic", "electronica", "edm", "electroclash", "idm", "dance and electronica"), "Elettronica"),
)


class SpotifyAgentError(RuntimeError):
    pass


def _atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    _attempt: int = 0,
) -> dict[str, Any]:
    body = urllib.parse.urlencode(form).encode() if form else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if form:
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        # Ritenta su errori transitori: 429 (rate limit, rispetta Retry-After) e
        # 502/503/504 (servizio momentaneamente non disponibile, es. MusicBrainz).
        # Solo se l'attesa e' breve; altrimenti rilancia l'errore.
        if exc.code in (429, 502, 503, 504) and _attempt < 5:
            if exc.code == 429:
                try:
                    wait = int(exc.headers.get("Retry-After", "2") or "2")
                except (TypeError, ValueError):
                    wait = 2
            else:
                wait = 2 * (_attempt + 1)  # backoff lineare per 5xx transitori
            if wait <= 30:
                time.sleep(wait + 1)
                return _request_json(
                    url,
                    method=method,
                    headers=headers,
                    form=form,
                    _attempt=_attempt + 1,
                )
        detail = exc.read().decode("utf-8", "replace")
        endpoint = urllib.parse.urlsplit(url).path
        raise SpotifyAgentError(
            f"Spotify HTTP {exc.code} su {endpoint}: {detail[:300]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SpotifyAgentError(f"Spotify non raggiungibile: {exc.reason}") from exc


def _client_id() -> str:
    value = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    if not value:
        raise SpotifyAgentError("Configura SPOTIFY_CLIENT_ID")
    return value


def _redirect_uri() -> str:
    return os.environ.get(
        "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/spotify/callback"
    )


def create_authorization() -> dict[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    _atomic_json(
        DROPS_HOME / "spotify-auth-state.json",
        {"state": state, "verifier": verifier, "created_at": time.time()},
    )
    params = {
        "client_id": _client_id(),
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": SCOPE,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": state,
        "show_dialog": "true",
    }
    return {"authorization_url": f"{SPOTIFY_AUTHORIZE}?{urllib.parse.urlencode(params)}"}


def exchange_code(code: str, state: str) -> dict[str, bool]:
    saved = _read_json(DROPS_HOME / "spotify-auth-state.json", {})
    if not saved or not secrets.compare_digest(state, saved.get("state", "")):
        raise SpotifyAgentError("Stato OAuth Spotify non valido")
    if time.time() - float(saved.get("created_at", 0)) > 600:
        raise SpotifyAgentError("Login Spotify scaduto: ripeti connessione")
    token = _request_json(
        SPOTIFY_TOKEN,
        method="POST",
        form={
            "client_id": _client_id(),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
            "code_verifier": saved["verifier"],
        },
    )
    token["expires_at"] = time.time() + int(token.get("expires_in", 3600)) - 60
    _atomic_json(TOKEN_FILE, token)
    return {"connected": True}


def _access_token() -> str:
    token = _read_json(TOKEN_FILE, {})
    if not token:
        raise SpotifyAgentError("Spotify non collegato")
    if time.time() >= float(token.get("expires_at", 0)):
        refresh = token.get("refresh_token")
        if not refresh:
            raise SpotifyAgentError("Sessione Spotify scaduta: ricollega account")
        renewed = _request_json(
            SPOTIFY_TOKEN,
            method="POST",
            form={
                "client_id": _client_id(),
                "grant_type": "refresh_token",
                "refresh_token": refresh,
            },
        )
        renewed["refresh_token"] = renewed.get("refresh_token", refresh)
        renewed["expires_at"] = time.time() + int(renewed.get("expires_in", 3600)) - 60
        _atomic_json(TOKEN_FILE, renewed)
        token = renewed
    return token["access_token"]


def _spotify_get(path_or_url: str) -> dict[str, Any]:
    url = path_or_url if path_or_url.startswith("https://") else SPOTIFY_API + path_or_url
    return _request_json(url, headers={"Authorization": f"Bearer {_access_token()}"})


def genre_folder(genres: list[str]) -> str:
    normalized = [genre.lower() for genre in genres]
    for needles, folder in GENRE_RULES:
        if any(needle in genre for genre in normalized for needle in needles):
            return folder
    return "Altri Generi"


def safe_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .")
    return cleaned[:100] or "Senza nome"


# --- Fonte generi indipendente da Spotify: MusicBrainz ---------------------
# Nessuna autenticazione, nessuna quota; richiede solo un User-Agent e ~1 req/s.
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/artist"
MUSICBRAINZ_UA = "Drops/1.0 (organizzatore musicale personale)"
MB_THROTTLE_S = 1.1          # rispetta il rate limit MusicBrainz (~1 req/s)
MB_MAX_NEW_PER_RUN = 200     # nuove ricerche per import: tiene la richiesta breve


def _musicbrainz_tags(artist_name: str) -> list[str] | None:
    """Tag/generi di un artista da MusicBrainz.

    Ritorna una lista (anche vuota se l'artista esiste ma non ha tag), oppure
    None se la chiamata fallisce (rete/5xx): in quel caso NON va messa in cache,
    va ritentata a un import successivo.
    """
    query = urllib.parse.quote(f'artist:"{artist_name}"')
    url = f"{MUSICBRAINZ_URL}?query={query}&fmt=json&limit=1"
    try:
        data = _request_json(url, headers={"User-Agent": MUSICBRAINZ_UA})
    except SpotifyAgentError:
        return None
    artists = data.get("artists") or []
    if not artists:
        return []
    top = artists[0]
    tags = [t.get("name") for t in top.get("tags", []) if t.get("name")]
    genres = [g.get("name") for g in top.get("genres", []) if g.get("name")]
    return sorted(set(tags + genres))


def import_saved_tracks() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    next_url: str | None = f"{SPOTIFY_API}/me/tracks?limit=50"
    while next_url:
        page = _spotify_get(next_url)
        items.extend(page.get("items", []))
        next_url = page.get("next")

    # I generi arrivano da MusicBrainz (per nome artista), non piu' da Spotify:
    # niente quota, niente 429. Cache su disco per nome (lowercase): ogni import
    # riparte da dove era arrivato. Per tenere breve la richiesta si risolvono
    # al massimo MB_MAX_NEW_PER_RUN nuovi artisti a run; rilanciare per finire.
    artist_genres: dict[str, list[str]] = _read_json(ARTIST_CACHE_FILE, {})
    artist_names = sorted(
        {
            (artist.get("name") or "").strip()
            for item in items
            for artist in (item.get("track") or {}).get("artists", [])
            if (artist.get("name") or "").strip()
        }
    )
    genres_incomplete = False
    resolved_this_run = 0
    consecutive_failures = 0
    for name in artist_names:
        key = name.lower()
        if key in artist_genres:
            continue
        if resolved_this_run >= MB_MAX_NEW_PER_RUN:
            genres_incomplete = True
            break
        tags = _musicbrainz_tags(name)
        if tags is None:
            # Errore transitorio: non cachare, ritenta al prossimo import.
            genres_incomplete = True
            consecutive_failures += 1
            if consecutive_failures >= 5:
                break  # MusicBrainz probabilmente down: fermati e riprova dopo
            time.sleep(MB_THROTTLE_S)
            continue
        consecutive_failures = 0
        artist_genres[key] = tags
        resolved_this_run += 1
        time.sleep(MB_THROTTLE_S)
    _atomic_json(ARTIST_CACHE_FILE, artist_genres)

    tracks = []
    for item in items:
        track = item.get("track") or {}
        if not track.get("id"):
            continue
        artists = track.get("artists", [])
        genres = sorted(
            {
                genre
                for artist in artists
                for genre in artist_genres.get((artist.get("name") or "").strip().lower(), [])
            }
        )
        tracks.append(
            {
                "spotify_id": track["id"],
                "name": track.get("name", ""),
                "artists": [artist.get("name", "") for artist in artists],
                "album": (track.get("album") or {}).get("name", ""),
                "duration_ms": track.get("duration_ms"),
                "isrc": (track.get("external_ids") or {}).get("isrc"),
                "spotify_url": (track.get("external_urls") or {}).get("spotify"),
                "added_at": item.get("added_at"),
                "genres": genres,
                "genre_folder": genre_folder(genres),
                "candidates": [],
                "status": "pending_search",
            }
        )
    catalog = {"updated_at": time.time(), "total": len(tracks), "tracks": tracks}
    _atomic_json(CATALOG_FILE, catalog)
    resolved = sum(1 for name in artist_names if name.lower() in artist_genres)
    return {
        "total": len(tracks),
        "catalog_file": str(CATALOG_FILE),
        "artists_total": len(artist_names),
        "artists_resolved": resolved,
        "artists_resolved_this_run": resolved_this_run,
        "genre_source": "musicbrainz",
        "genres_complete": not genres_incomplete,
        "hint": (
            "Generi completi."
            if not genres_incomplete
            else f"Risolti {resolved}/{len(artist_names)} artisti. Rilancia "
            "/spotify/import per continuare (riparte dalla cache)."
        ),
    }


def get_catalog(offset: int = 0, limit: int = 100) -> dict[str, Any]:
    catalog = _read_json(CATALOG_FILE, {"tracks": []})
    tracks = catalog.get("tracks", [])
    return {
        "total": len(tracks),
        "offset": offset,
        "limit": limit,
        "tracks": tracks[offset : offset + limit],
    }


def find_track(track_id: str) -> dict[str, Any]:
    for track in _read_json(CATALOG_FILE, {"tracks": []}).get("tracks", []):
        if track.get("spotify_id") == track_id:
            return track
    raise SpotifyAgentError("Brano non trovato nel catalogo importato")


def search_candidates(track_id: str, limit: int = 5) -> dict[str, Any]:
    catalog = _read_json(CATALOG_FILE, {"tracks": []})
    track = next(
        (item for item in catalog.get("tracks", []) if item.get("spotify_id") == track_id),
        None,
    )
    if not track:
        raise SpotifyAgentError("Brano non trovato nel catalogo importato")
    query = f"{' '.join(track['artists'])} {track['name']} official audio"
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        result = ydl.extract_info(
            f"ytsearch{max(1, min(limit, 10))}:{query}", download=False
        )
    candidates = [
        {
            "url": entry.get("webpage_url") or entry.get("url"),
            "title": entry.get("title"),
            "channel": entry.get("channel") or entry.get("uploader"),
            "duration": entry.get("duration"),
        }
        for entry in result.get("entries", [])
        if entry
    ]
    track["candidates"] = candidates
    track["status"] = "awaiting_approval"
    _atomic_json(CATALOG_FILE, catalog)
    return {"track": track, "candidates": candidates}


def approved_download_context(track_id: str, url: str) -> dict[str, Any]:
    track = find_track(track_id)
    if url not in {candidate.get("url") for candidate in track.get("candidates", [])}:
        raise SpotifyAgentError("URL non presente tra candidati verificati")
    return {
        "spotify_id": track_id,
        "artists": track["artists"],
        "name": track["name"],
        "genre_folder": safe_component(track["genre_folder"]),
        "target_dir": str(MUSIC_ROOT / safe_component(track["genre_folder"])),
    }
