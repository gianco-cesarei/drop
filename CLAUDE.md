# Drops — Contesto Strategico per l'Agente

> Questo file va letto **prima di qualsiasi intervento** sul progetto.
> Contiene decisioni architetturali, vincoli tecnici e roadmap.

---

## Cos'è il progetto

**Drops** è un'app desktop macOS per scaricare audio e video da YouTube e SoundCloud in alta qualità. Distribuita come file `.dmg`. Uso personale (Giancarlo), con possibile deploy pubblico futuro.

Stack: Python (FastAPI + yt-dlp) · HTML/JS puro · Tauri v2 (wrapper desktop Rust)

---

## Struttura cartelle

```
mp3-downloader/
├── backend/          → Server Python (FastAPI). Core dell'app.
│   ├── main.py       → Routes + logica download (audio, video, clip)
│   └── requirements.txt
├── frontend/
│   └── index.html    → UI completa in un singolo file HTML/JS
├── src-tauri/        → App desktop Rust (Tauri v2)
│   └── src/main.rs   → Avvia backend Python, apre WebView su :8000
├── assets/           → Icone, schemi, documentazione visuale
│   ├── drops_project_schema.html
│   └── drops_feature_analysis.html
├── deploy/           → Config deploy futuro (render.yaml, netlify.toml)
├── docs/             → Documentazione strategica e roadmap
├── build-dmg.sh      → Compila il DMG (uso: ./build-dmg.sh)
├── launch-desktop.sh → Avvia in modalità dev con Tauri
├── start.sh          → Avvia solo il backend nel browser
└── CHANGELOG.md      → Storico delle modifiche
```

---

## Vincolo architetturale fondamentale

**Il WebView di Tauri carica da `http://127.0.0.1:8000` (URL esterno).**

Questo significa che `window.__TAURI__` **non è iniettato** nel frontend. Di conseguenza:
- Le API native di Tauri (dialog, notification, shell, fs) **non sono accessibili** dal frontend JavaScript
- Notifiche, folder picker nativo, apertura in Finder richiedono workaround

### Workaround adottati (Fase 1)
- **Notifiche**: Web Notifications API (funziona nel WebView senza Tauri)
- **Cartella salvataggio**: backend scrive direttamente in `~/Music` o path configurata via `~/.drops/prefs.json`
- **Apertura file**: download via browser blob (attuale)

### Soluzione futura (Fase 2 — al momento del deploy pubblico)
- Servire frontend da Tauri (`tauri://localhost`) invece che dal backend Python
- Backend diventa pura API su `/api/*`
- Si sbloccano: `tauri-plugin-dialog`, `tauri-plugin-notification`, `tauri-plugin-shell`
- **Non fare questo ora** — rimandare a quando si lavora sul deploy pubblico

---

## File di configurazione runtime

Il backend usa `~/.drops/` come directory di lavoro:
- `~/.drops/cookies.txt` → cookie YouTube (opzionale, per video age-restricted)
- `~/.drops/logs/backend.log` → log rotanti del backend
- `~/.drops/prefs.json` → preferenze utente (da implementare)
- `~/.drops/history.json` → cronologia download (da implementare)

**Non mettere mai cookies.txt nel repository.** È già stato rimosso.

---

## Dipendenze Python

Versioni fisse (requirements.txt e start.sh devono essere sempre allineati):
- `fastapi==0.111.0`
- `uvicorn[standard]==0.29.0`
- `pydantic==2.7.1`
- `python-multipart==0.0.9`
- `yt-dlp>=2025.1.15`

Il venv usa **Python 3.11** (`.venv/bin/python3.11`). È questa versione che `main.rs` cerca all'avvio del DMG — non cambiare senza aggiornare anche il Rust.

---

## Feature implementate

- Download audio: MP3 (128k / 192k / 320k) e FLAC da YouTube e SoundCloud
- Download video: MP4 (480p / 720p / 1080p) da YouTube, con `VIDEO_FORMAT_MAP` che preferisce codec avc1
- Estrazione clip: audio e video, con `download_ranges` yt-dlp (scarica solo la sezione richiesta); fallback `trim_file` via ffmpeg se `download_ranges` non era attivo
- **Progress tracking reale**: `progress_hook` da yt-dlp + `monitor_part_file` thread (scansione file `.part` su disco come fallback, utile con fragment download)
- **Pre-fetch metadata**: stima `expected_bytes` prima del download per progress percentage accurata; scala alla durata della clip se è un clip
- Cronologia sessione (localStorage, si azzera alla chiusura)
- Endpoint `/auth-token` per compatibilità frontend

### Dettaglio architettura progress
Il progress è calcolato a più livelli con fallback:
1. `progress_hook` yt-dlp → `total_bytes` / `downloaded_bytes` → percentuale diretta
2. Se `total_bytes` assente → `fragment_index` / `fragment_count`
3. `monitor_part_file` thread (ogni 0.5s) → scansiona `DOWNLOAD_DIR` per file `{job_id}*` → aggiorna `downloaded_bytes`
4. Frontend usa `downloaded_bytes` / `expected_bytes` (pre-fetchato) come fallback visivo

---

## Roadmap prodotto

Fonte principale: `docs/PRODUCT_ROADMAP.md`.

- V1: download affidabile → updater → libreria locale → player → strumenti DJ.
- V2: Spotify → SoundCloud → YouTube → analytics sviluppatore.

Non aggiungere priorità parallele in questo file: aggiornare roadmap principale.

### Quando implementare playlist: refactor prima
Separare `main.py` in:
- `main.py` → solo routes FastAPI
- `downloader.py` → logica `do_download`, `trim_file`, `ffmpeg_bin`, progress hook
- `playlist.py` → gestione playlist (quando serve)

---

## Architettura futura per distribuzione pubblica

- Servire frontend da Tauri (non da Python)
- Aggiungere Tauri plugin nativi
- Deploy backend su Render, frontend su Netlify (config già in `/deploy/`)
- Autenticazione se pubblico

---

## Regole operative per l'agente

- **Leggere questo file all'inizio di ogni sessione** prima di toccare il codice
- **Aggiornare CHANGELOG.md** dopo ogni sessione di lavoro
- **Non toccare src-tauri/target/** — è generato da Cargo
- **Non ricreare cookies.txt** — è dato privato, vive in `~/.drops/`
- **Non cambiare la versione Python nel venv** senza aggiornare main.rs
- **Non anticipare la Fase 2** — nessuna modifica a Tauri/Rust finché non si decide il deploy
- **Mantenere frontend come singolo file** `index.html` — niente build step, niente framework JS
- Quando si aggiunge una dipendenza Python: aggiornare sia `requirements.txt` che `start.sh` e `launch-desktop.sh`
