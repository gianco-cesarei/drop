"""Diagnosi Spotify per Drops (standalone, solo stdlib).

Isola il livello del blocco 403 su /v1/me/tracks:
- chiama /v1/me  (endpoint innocuo -> chi sei davvero?)
- chiama /v1/me/tracks?limit=1  (l'endpoint che fallisce)

Non richiede yt_dlp ne' il venv: gira col Python di sistema.
NON stampa mai il token. Gestisce da solo il refresh se scaduto.

Uso:
    cd "/Users/gianco/Documents/Claude/Projects/mp3-downloader"
    export SPOTIFY_CLIENT_ID="7b99b9653fba45ae974edcd553312387"
    python3 backend/diagnose_spotify.py
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SPOTIFY_TOKEN = "https://accounts.spotify.com/api/token"
SPOTIFY_API = "https://api.spotify.com/v1"
CLIENT_ID = os.environ.get(
    "SPOTIFY_CLIENT_ID", "7b99b9653fba45ae974edcd553312387"
).strip()

DROPS_HOME = Path(
    os.environ.get("DROPS_STATE_DIR", str(Path.home() / ".drops"))
).expanduser()
TOKEN_FILE = DROPS_HOME / "spotify-token.json"


def _request_json(url, method="GET", headers=None, form=None):
    body = urllib.parse.urlencode(form).encode() if form else None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if form:
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        endpoint = urllib.parse.urlsplit(url).path
        raise RuntimeError(f"Spotify HTTP {exc.code} su {endpoint}: {detail[:300]}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Spotify non raggiungibile: {exc.reason}")


def _access_token():
    if not TOKEN_FILE.exists():
        raise RuntimeError(f"Token non trovato: {TOKEN_FILE} - fai login da /spotify/connect")
    token = json.loads(TOKEN_FILE.read_text())
    if not token.get("access_token"):
        raise RuntimeError("Token file presente ma senza access_token: ricollega account")
    if time.time() >= float(token.get("expires_at", 0)):
        refresh = token.get("refresh_token")
        if not refresh:
            raise RuntimeError("Sessione scaduta e nessun refresh_token: ricollega account")
        print("  (token scaduto, provo refresh...)")
        renewed = _request_json(
            SPOTIFY_TOKEN,
            method="POST",
            form={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh,
            },
        )
        renewed["refresh_token"] = renewed.get("refresh_token", refresh)
        renewed["expires_at"] = time.time() + int(renewed.get("expires_in", 3600)) - 60
        tmp = TOKEN_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(renewed))
        tmp.replace(TOKEN_FILE)
        token = renewed
    return token["access_token"]


def _get(path):
    url = path if path.startswith("https://") else SPOTIFY_API + path
    return _request_json(url, headers={"Authorization": f"Bearer {_access_token()}"})


def _line(label, value):
    print(f"  {label:<14} {value}")


def main():
    print("=" * 60)
    print("DIAGNOSI SPOTIFY DROPS")
    print("=" * 60)
    _line("Client ID", CLIENT_ID)
    _line("Token file", str(TOKEN_FILE))

    print("\n[1] GET /me  (identita' account autenticato)")
    me_ok = False
    try:
        me = _get("/me")
        print("  OK - token valido, account raggiunto:")
        _line("id", me.get("id"))
        _line("display_name", me.get("display_name"))
        _line("email", me.get("email", "(scope email non richiesto)"))
        _line("product", me.get("product"))
        _line("country", me.get("country"))
        me_ok = True
    except Exception as exc:
        print(f"  FALLITO: {exc}")

    print("\n[2] GET /me/tracks?limit=1  (i preferiti)")
    tracks_ok = False
    try:
        data = _get("/me/tracks?limit=1")
        total = data.get("total")
        print(f"  OK - libreria accessibile. Totale preferiti: {total}")
        items = data.get("items") or []
        if items:
            tr = items[0].get("track", {})
            artists = ", ".join(a.get("name", "") for a in tr.get("artists", []))
            _line("primo brano", f"{artists} - {tr.get('name')}")
        tracks_ok = True
    except Exception as exc:
        print(f"  FALLITO: {exc}")

    print("\n" + "=" * 60)
    print("VERDETTO")
    print("=" * 60)
    if me_ok and tracks_ok:
        print("  Tutto funziona. Il 403 e' risolto: puoi lanciare /spotify/import.")
    elif me_ok and not tracks_ok:
        print("  /me funziona ma /me/tracks NO -> blocco 100% lato Spotify")
        print("  (allowlist / Web API dell'app / quota), NON il codice Drops.")
        print("  Azione: nel Dashboard verifica 'APIs used' = Web API e che")
        print("  l'account sopra (id) sia in User Management e proprietario dell'app.")
    else:
        print("  Nemmeno /me funziona -> token legato a account non autorizzato,")
        print("  sessione scaduta, o Web API non attiva.")
        print("  Azione: rifai login da http://127.0.0.1:8000/spotify/connect")
        print("  con l'account proprietario dell'app DROP.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
