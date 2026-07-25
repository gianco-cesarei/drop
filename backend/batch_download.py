"""Scarica in blocco i preferiti Spotify importati, per genere, via il backend Drops.

Il backend deve essere attivo su http://127.0.0.1:8000 (./start.sh).
Per ogni brano: cerca i candidati su YouTube, scarica il primo, e il file finisce
in  Music Gianco/<Genere>/Artista - Titolo.mp3

Uso:
  # 1) elenca i generi e quanti brani ciascuno (nessun download):
  python3 backend/batch_download.py

  # 2) scarica un intero genere (MP3 320 di default):
  python3 backend/batch_download.py --genre "Italo Disco - Hi-NRG"

  # opzioni: --quality 128|192|320|flac   --limit N (solo i primi N)

DIRITTI: eseguendo un download confermi di possedere i diritti o di essere
autorizzato a scaricare il materiale (il backend richiede rights_confirmed).
I brani gia' presenti nella cartella di destinazione vengono saltati.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BACKEND = os.environ.get("DROPS_BACKEND", "http://127.0.0.1:8000")
CATALOG = Path.home() / ".drops" / "spotify-library.json"
MUSIC_ROOT = Path(
    os.environ.get("DROPS_MUSIC_DIR", str(Path.home() / "Documents" / "Music Gianco"))
)


def _post(path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(
        BACKEND + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def _get(path: str) -> dict:
    with urllib.request.urlopen(BACKEND + path, timeout=60) as r:
        return json.load(r)


def _safe(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip(" .")
    return cleaned[:100] or "Senza nome"


def _load_catalog() -> list[dict]:
    if not CATALOG.exists():
        sys.exit(f"Catalogo non trovato: {CATALOG}. Esegui prima POST /spotify/import.")
    return json.loads(CATALOG.read_text()).get("tracks", [])


def _already_downloaded(track: dict) -> bool:
    folder = MUSIC_ROOT / _safe(track.get("genre_folder", "Altri Generi"))
    if not folder.exists():
        return False
    stem = _safe(f"{', '.join(track.get('artists', []))} - {track.get('name', '')}")
    return any(p.is_file() and p.stem == stem for p in folder.iterdir())


def _backend_up() -> bool:
    try:
        _get("/health")
        return True
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch download preferiti per genere.")
    ap.add_argument("--genre", help="Nome esatto del genere/cartella da scaricare.")
    ap.add_argument("--quality", default="320", help="128 | 192 | 320 | flac")
    ap.add_argument("--limit", type=int, default=0, help="Solo i primi N brani.")
    args = ap.parse_args()

    tracks = _load_catalog()

    # Modalita' elenco: nessun genere -> mostra distribuzione e esce.
    if not args.genre:
        counts = Counter(t.get("genre_folder", "Altri Generi") for t in tracks)
        print(f"Catalogo: {len(tracks)} brani in {len(counts)} generi.\n")
        for genre, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:4}  {genre}")
        print('\nPer scaricare un genere:')
        print('  python3 backend/batch_download.py --genre "NOME ESATTO"')
        return

    if not _backend_up():
        sys.exit(f"Backend non raggiungibile su {BACKEND}. Avvialo con ./start.sh")

    selection = [t for t in tracks if t.get("genre_folder") == args.genre]
    if args.limit:
        selection = selection[: args.limit]
    if not selection:
        sys.exit(f"Nessun brano per il genere '{args.genre}'. Controlla il nome esatto.")

    print(f"Scarico {len(selection)} brani del genere '{args.genre}' in MP3 {args.quality}.")
    print("Confermi di avere i diritti/autorizzazione sul materiale.\n")

    ok = skip = fail = 0
    for i, track in enumerate(selection, 1):
        label = f"{', '.join(track.get('artists', []))} - {track.get('name', '')}"
        tag = f"[{i}/{len(selection)}]"

        if _already_downloaded(track):
            print(f"{tag} SKIP (gia' presente): {label}")
            skip += 1
            continue

        try:
            cand_resp = _post(f"/spotify/library/{track['spotify_id']}/candidates?limit=5")
            candidates = cand_resp.get("candidates") or []
            if not candidates or not candidates[0].get("url"):
                print(f"{tag} NESSUN CANDIDATO: {label}")
                fail += 1
                continue

            job = _post(
                "/download",
                {
                    "url": candidates[0]["url"],
                    "spotify_track_id": track["spotify_id"],
                    "rights_confirmed": True,
                    "quality": args.quality,
                    "format": "audio",
                },
            )
            job_id = job["job_id"]

            status = {}
            for _ in range(400):  # ~10 min max per brano
                status = _get(f"/status/{job_id}")
                if status.get("status") in ("ready", "error"):
                    break
                time.sleep(1.5)

            if status.get("status") == "ready":
                dest = status.get("library_path") or status.get("file_path", "")
                print(f"{tag} OK: {label}")
                if dest:
                    print(f"       -> {dest}")
                ok += 1
            else:
                print(f"{tag} ERRORE: {label}  {status.get('error', 'timeout')}")
                fail += 1

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            print(f"{tag} HTTP {exc.code}: {label}  {detail}")
            fail += 1
        except Exception as exc:  # noqa: BLE001
            print(f"{tag} ECCEZIONE: {label}  {exc}")
            fail += 1

    print(f"\nFatto. OK: {ok}  SKIP: {skip}  FALLITI: {fail}")
    print(f"Cartella: {MUSIC_ROOT}")


if __name__ == "__main__":
    main()
