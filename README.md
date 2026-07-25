# Drops — MP3 Downloader

Stack: FastAPI + yt-dlp (Render) · HTML statico (Netlify) · Totalmente gratuito.

## Agente Spotify → Drops → Music Gianco

Agente importa tutti i “Brani che ti piacciono” come metadati, prepara
candidati esterni e salva download autorizzati in:

```text
~/Documents/Music Gianco/<Genere>/Artista - Titolo.mp3
```

Configurazione:

1. Crea app nel [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Registra redirect URI `http://127.0.0.1:8000/spotify/callback`.
3. Imposta `SPOTIFY_CLIENT_ID`. Opzionali:
   `SPOTIFY_REDIRECT_URI` e `DROPS_MUSIC_DIR`.
4. Avvia backend locale.
5. Apri `http://127.0.0.1:8000/spotify/connect` nel browser, completa login,
   poi chiama `POST /spotify/import`.

API agente:

- `GET /spotify/connect`
- `GET /spotify/callback`
- `POST /spotify/import`
- `GET /spotify/library?offset=0&limit=100`
- `POST /spotify/library/{spotify_id}/candidates`
- `POST /download` con `spotify_track_id` e `rights_confirmed`

Spotify fornisce solo catalogo e generi. Conferma diritti richiesta prima di
ogni download legato alla libreria.

---

## Struttura

```
mp3-downloader/
├── backend/
│   ├── main.py           ← API FastAPI
│   ├── requirements.txt
│   └── render.yaml       ← config deploy Render
└── frontend/
    ├── index.html        ← app web
    └── netlify.toml      ← config deploy Netlify
```

---

## Deploy — passo per passo

### 1. Crea il repo su GitHub

1. Vai su github.com → **New repository**
2. Nome: `drops-mp3` (o quello che vuoi), **Private**
3. Carica tutti i file mantenendo la struttura di cartelle sopra

### 2. Deploy Backend su Render

1. Vai su [render.com](https://render.com) → Sign up con GitHub
2. **New** → **Web Service**
3. Collega il repo `drops-mp3`
4. Impostazioni:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. **Environment Variables** (tab "Environment"):
   - `APP_PASSWORD` = `culo`
6. Clicca **Create Web Service**
7. Aspetta 3-5 minuti. Render ti darà un URL tipo:
   `https://drops-mp3-xxxx.onrender.com`
   **Copialo — ti serve nel passo successivo.**

### 3. Aggiorna il Frontend con l'URL del backend

Apri `frontend/index.html` e cerca questa riga (~riga 220):

```js
const API_URL = (
  window.__API_URL__ ||
  localStorage.getItem('__api_url__') ||
  'https://mp3-downloader-api.onrender.com'  // ← CAMBIA QUESTO
);
```

Sostituisci `https://mp3-downloader-api.onrender.com` con il tuo URL Render, es:
```js
  'https://drops-mp3-xxxx.onrender.com'
```

Salva e fai push su GitHub.

### 4. Deploy Frontend su Netlify

1. Vai su [netlify.com](https://netlify.com) → Sign up con GitHub
2. **Add new site** → **Import an existing project**
3. Collega il repo `drops-mp3`
4. Impostazioni:
   - **Base directory**: `frontend`
   - **Publish directory**: `frontend`
   - Build command: *(lascia vuoto)*
5. Clicca **Deploy site**
6. Netlify ti darà un URL tipo `https://amazing-drops-123.netlify.app`
   Puoi rinominarlo in **Site settings → Change site name**

### 5. UptimeRobot — tieni sveglio Render

Render free si addormenta dopo 15 min. Per evitarlo:

1. Vai su [uptimerobot.com](https://uptimerobot.com) → Sign up
2. **Add New Monitor**:
   - Monitor Type: HTTP(s)
   - Friendly Name: Drops API
   - URL: `https://il-tuo-url.onrender.com/health`
   - Monitoring Interval: **Every 5 minutes**
3. Salva. Fine — il backend resterà sempre sveglio.

---

## Condividi con gli amici

Manda il link Netlify + la password:

> 🎵 **Drops** — https://il-tuo-sito.netlify.app
> Password: `culo`

---

## Aggiornare yt-dlp (importante)

YouTube cambia le sue API regolarmente. Se smette di funzionare, aggiorna yt-dlp in `requirements.txt`:

```
yt-dlp==ULTIMA_VERSIONE
```

Controlla la versione più recente su: https://github.com/yt-dlp/yt-dlp/releases

Poi fai commit → push → Render si ribuilderà automaticamente.

---

## Cambiare la password

Nel dashboard Render → **Environment** → modifica `APP_PASSWORD` → **Save Changes**.
Il servizio si riavvia automaticamente con la nuova password.

---

## Qualità disponibili

| Selezione | Formato | Note |
|-----------|---------|------|
| 128k | MP3 | Leggero, streaming quality |
| 192k | MP3 | Buona qualità |
| 320k | MP3 VBR | Default — qualità massima |
| FLAC | FLAC | Lossless, file grandi (~30MB/brano) |

---

## Troubleshooting

**Il sito dà errore di connessione al primo utilizzo** → Render sta facendo il cold start (30s). Aspetta e riprova.

**"URL non supportato"** → Funziona con YouTube, YouTube Music, SoundCloud. Non Spotify (streaming protetto).

**Il download si blocca** → yt-dlp potrebbe essere outdated. Aggiorna come descritto sopra.
