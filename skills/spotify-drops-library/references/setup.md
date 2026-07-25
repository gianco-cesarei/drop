# Setup Spotify

1. Creare app in Spotify Developer Dashboard.
2. Aggiungere redirect URI esatta:
   `http://127.0.0.1:8000/spotify/callback`
3. Esportare:

```bash
export SPOTIFY_CLIENT_ID="client-id-della-app"
export SPOTIFY_REDIRECT_URI="http://127.0.0.1:8000/spotify/callback"
export DROPS_MUSIC_DIR="$HOME/Documents/Music Gianco"
```

`DROPS_STATE_DIR` può cambiare cartella locale token/catalogo; default `~/.drops`.

4. Avviare backend dalla cartella `backend`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Scope richiesto: `user-library-read`. Token salvato localmente in
`~/.drops/spotify-token.json`; non inserirlo nel repository.
