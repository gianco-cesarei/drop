# Changelog — Drops

---

## [Unreleased]

---

## 2026-07-25 (v1.1.0 — fix installer Windows: UI non caricava)

### Fix: frontend non impacchettato nell'exe Windows
- **Sintomo**: dopo l'installazione del `.exe` su Windows, all'avvio compariva testo/codice grezzo a schermo con errore, invece dell'interfaccia di Drops.
- **Causa**: `serve_frontend()` in `backend/main.py` cercava `frontend/index.html` con un path relativo a `__file__` (`.parent.parent`). Nell'exe PyInstaller (frozen) quel percorso non esiste e il file non era nemmeno incluso nel bundle → la route `/` sollevava `FileNotFoundError` → HTTP 500 → il WebView mostrava il dump d'errore grezzo.
- **Fix `backend/main.py`**: aggiunto `import sys`; nuovo helper `_frontend_index_path()` che risolve `index.html` in modalità frozen via `sys._MEIPASS` (e accanto a `sys.executable`) con fallback al layout sorgente `backend/../frontend/`. `serve_frontend()` ora restituisce un 500 con messaggio chiaro e log se il file manca davvero, invece di un traceback grezzo.
- **Fix `backend/drops-backend.spec`**: `frontend/index.html` aggiunto ai `datas` di PyInstaller → la UI viene estratta in `_MEIPASS/frontend/` e servita correttamente. Build macOS (venv, non-frozen) invariata: usa il ramo di fallback.
- **Versione**: bump a **1.1.0** in `tauri.conf.json`, `package.json`, `src-tauri/Cargo.toml`.
- **CI smoke test** (`.github/workflows/windows-build.yml`): dopo la build del backend, il runner Windows avvia `drops-backend.exe` e verifica che `/` risponda `200` con HTML e che `/health` sia OK. Se la UI non viene servita la build fallisce prima di generare l'installer → il bug non può più arrivare in Release.
- **CI download reale (best-effort)**: step aggiuntivo che scarica davvero un MP3 da un link YouTube corto tramite l'exe impacchettato (valida yt-dlp + ffmpeg end-to-end). È `continue-on-error` per non far fallire la Release se YouTube blocca l'IP del runner CI; l'esito è visibile nei log. Il test di download definitivo resta comunque quello manuale sul PC Windows.

---

## 2026-07-25 (sessione — supporto build Windows)

### Installer Windows via GitHub Actions (backend impacchettato)
- **Obiettivo**: produrre un installer `.exe` di Drops per Windows. Tauri non fa cross-compile affidabile da macOS → build su runner `windows-latest` in CI, così non serve un PC Windows.
- **Backend cross-platform** (`backend/main.py`): discovery ffmpeg ora gestisce `ffmpeg.exe` e la cartella impacchettata via env `DROPS_FFMPEG_DIR`; PATH Homebrew forzato solo su macOS/Linux; `DOWNLOAD_DIR` usa `tempfile.gettempdir()` (era `/tmp/downloads`, hard-coded Unix) con override `DROPS_DOWNLOAD_DIR`; `ffmpeg_bin()` restituisce il nome eseguibile corretto per piattaforma.
- **Backend impacchettato**: `backend/run_backend.py` (entry point che passa l'oggetto `app` a uvicorn) + `backend/drops-backend.spec` (PyInstaller onefile: FastAPI+uvicorn+yt-dlp → `drops-backend.exe`). Nessun Python richiesto sul PC utente.
- **Tauri Windows** (`src-tauri/tauri.windows.conf.json`): mappa risorse `drops-backend.exe` + `ffmpeg/ffmpeg.exe`, WebView2 `downloadBootstrapper`, icona `.ico`. File ignorato fuori da Windows → build macOS invariata.
- **`src-tauri/src/main.rs`**: avvio backend per-piattaforma. Su Windows esegue il backend impacchettato dalle risorse passando `DROPS_FFMPEG_DIR`; ramo macOS = comportamento storico (venv). Aggiunta attesa readiness sulla porta 8000 (sostituisce lo `sleep(2s)` fisso) e kill del backend su `RunEvent::Exit`.
- **CI** (`.github/workflows/windows-build.yml`): PyInstaller → stage `drops-backend.exe`, download ffmpeg statico (BtbN), `tauri icon`, `tauri build --bundles nsis`, upload installer come artifact. Trigger manuale (`workflow_dispatch`) o tag `v*`.
- **Doc**: `docs/WINDOWS_BUILD.md`. `.gitignore`: aggiunto `src-tauri/binaries/` (generati in CI).
- **Nota**: verificati su Mac sintassi Python, JSON e YAML; la compilazione Windows va confermata dal primo run del workflow (richiede un remote GitHub, attualmente assente).

### Release pubblica automatica
- Il workflow ora, sui tag `v*`, pubblica una **GitHub Release** con l'installer allegato (`softprops/action-gh-release`, `permissions: contents: write`). Il link di download della Release è pubblico: un utente esterno scarica l'`.exe` senza account GitHub (l'artifact di Actions invece è scaricabile solo da utenti loggati con accesso al repo).

---

## 2026-07-24 (sessione — debug Spotify 403)

### Fix integrazione Spotify
- **Risolto `403 "The user is not registered for this application"`** su `/v1/me` e `/v1/me/tracks`. Causa: token stantìo in `~/.drops/spotify-token.json` legato a una vecchia sessione/account; il refresh continuava a rinnovare l'identità sbagliata. Config app Spotify (Web API attiva, redirect URI, allowlist) era corretta.
- **`spotify_agent.create_authorization()`**: aggiunto `show_dialog=true` ai parametri OAuth → Spotify mostra sempre il selettore account, evita di riusare silenziosamente una sessione errata.
- **Procedura di reset**: `rm ~/.drops/spotify-token.json ~/.drops/spotify-auth-state.json` + nuovo login forzato risolve login su account sbagliato.
- Dopo il fix: import legge correttamente 720 preferiti (account `31bnpr6snvsmbihbkfb6w2wkvzvq`, Giancarlo Cesarei).

### Import resistente al rate limit Spotify (429 QUOTA_EXCEEDED)
- **Problema**: `POST /spotify/import` con 720 preferiti fa una chiamata `/v1/artists/{id}` per artista (endpoint batch rimosso in Development Mode); esaurisce la quota, e al primo 429 l'intero import falliva con 500 senza salvare nulla.
- **`_request_json`**: aggiunto retry sul 429 che rispetta l'header `Retry-After` (solo se ≤ 30s, altrimenti rilancia), max 5 tentativi.
- **Cache generi su disco**: `~/.drops/spotify-artist-genres.json`. I generi già letti non vengono richiesti di nuovo → ogni import riparte da dove si era fermato.
- **Import resiliente**: sul 429 di quota, `import_saved_tracks` salva i progressi (cache + catalogo con tutti i 720 brani) e ritorna `genres_complete: false` + `hint` invece di crashare. Rilanciare l'import completa i generi in modo incrementale.
- La risposta ora include `artists_total`, `artists_resolved`, `genres_complete`, `hint`.

### Generi da MusicBrainz invece che da Spotify (rimossa dipendenza dalla quota)
- **Motivazione**: la quota Spotify di Development Mode (`429 QUOTA_EXCEEDED`) rende inaffidabile leggere i generi via `/v1/artists/{id}` per 780 artisti. Scelta: `import_saved_tracks` ora ricava i generi da **MusicBrainz** (per nome artista) — nessuna autenticazione, nessuna quota.
- **`_musicbrainz_tags(name)`**: interroga `musicbrainz.org/ws/2/artist`, ritorna i tag/generi; `None` su errore transitorio (non viene messo in cache, si ritenta dopo). Richiede `User-Agent` e throttle ~1 req/s (`MB_THROTTLE_S`).
- **`_request_json`**: il retry con backoff ora copre anche `502/503/504` (MusicBrainz risponde 503 sotto carico), non solo `429`.
- **Cache** `~/.drops/spotify-artist-genres.json` ora keyata per **nome artista** (lowercase). Import resumibile: max `MB_MAX_NEW_PER_RUN` (200) nuove ricerche a run, poi `genres_complete:false` → rilanciare per continuare.
- **Verificato** su campione (Sade, Depeche Mode, Linkin Park, Pink Floyd, Patrick Cowley, My Mine, ecc.): mappatura corretta sulle cartelle `GENRE_RULES`. Nota: New Order finisce in "House" per precedenza regole (ha tag misti synth/house) — da affinare se necessario.
- `/spotify/import` ora usa Spotify solo per leggere i preferiti (`/me/tracks`, poche chiamate); i generi non toccano piu' Spotify.

### Copertura generi ampliata (recupero "Altri Generi")
- Analisi dei tag MusicBrainz finiti in "Altri Generi" (~286/722, 40%) via `backend/analyze_genres.py`: grossi cluster non coperti (hip hop/rap/trap, techno, pop, electronic/EDM, disco, punk, latin).
- **`GENRE_RULES` estese** con nuove cartelle, aggiunte in coda per non alterare le classificazioni esistenti: `Hip-hop - Rap`, `Techno`, `Disco - Nu-disco`, `Punk - Ska`, `Latin`, `Pop`, `Elettronica` (fallback generico ultimo). Rimappatura istantanea (tag già in cache), basta rilanciare `/spotify/import`.

### Strumenti
- **Aggiunto `backend/analyze_genres.py`**: legge la cache e stampa i tag più frequenti tra i brani in "Altri Generi", per guidare l'estensione delle regole. Nessuna chiamata di rete.
- **Aggiunto `backend/batch_download.py`**: scarica in blocco i preferiti per genere via il backend (candidati → download → `Music Gianco/<Genere>/`). Senza argomenti elenca i generi con i conteggi; salta i brani già presenti (resumibile).
- **Aggiunto `backend/diagnose_spotify.py`**: script standalone (solo stdlib, no `yt_dlp`) che isola il livello del blocco chiamando `/me` e `/me/tracks`; non stampa mai il token. Va lanciato col venv (`.venv/bin/python3.11`) per avere i certificati SSL.

---

## 2026-05-29 (sessione 3)

### Ottimizzazione clip
- **Skip pre-fetch metadata per clip**: per richieste clip, il round-trip a YouTube per stimare `expected_bytes` viene saltato → risparmio 3-5s di latenza iniziale; il `progress_hook` yt-dlp è sufficiente per clip brevi
- **`force_keyframes_at_cuts`**: aggiunto per clip video → yt-dlp forza un keyframe al punto di taglio, il muxing ffmpeg è più preciso e scarica meno dati extra
- **Logging timing**: aggiunto `logger.debug` per pre-fetch e `logger.info` per tempo totale yt-dlp → `~/.drops/logs/backend.log` ora mostra dove va il tempo
- **Audio format**: `bestaudio` → `bestaudio/best` come fallback (più compatibile)

### Organizzazione progetto
- **Aggiornato `CLAUDE.md`**: sezione feature implementate riscritta con architettura progress tracking dettagliata
- **Creato `.gitignore`**: esclude `src-tauri/target/`, `.venv/`, `cookies.txt`, log, `.DS_Store`, `node_modules/`, `.env`

---

## 2026-05-29 (sessione 2)

### Backend — miglioramenti progress tracking (aggiunti da Giancarlo)
- **`progress_hook` yt-dlp**: calcola percentuale da `downloaded_bytes`/`total_bytes`; fallback su `fragment_index`/`fragment_count` per stream segmentati
- **`monitor_part_file` thread**: thread daemon che ogni 0.5s scansiona `DOWNLOAD_DIR` per file `{job_id}*`, aggiorna `downloaded_bytes` anche quando il progress_hook non si attiva (es. download con `external_downloader=ffmpeg`)
- **Pre-fetch metadata** prima del download: stima `expected_bytes` per audio e video; scala proporzionalmente alla durata del clip se richiesto; aggiunge ~5% overhead per muxing video
- **`download_ranges`**: clip audio/video ora usa `download_ranges` yt-dlp → scarica solo la sezione richiesta dal server, niente trim post-download (più veloce, meno dati)
- **Endpoint `/status`**: ora espone `downloaded_bytes` e `expected_bytes` per progress visivo frontend

### Organizzazione progetto
- **Creato `.gitignore`**: esclude `src-tauri/target/`, `.venv/`, `cookies.txt`, `.DS_Store`, `.env`, log, `node_modules/`
- **Aggiornato `CLAUDE.md`**: sezione feature implementate aggiornata con progress tracking e architettura dettagliata

---

## 2026-05-29

### Fix critici
- **Aggiunto endpoint `/auth-token`** nel backend — era assente, causava il fallimento silenzioso di tutti i download (il frontend lo chiamava all'avvio per ottenere il token di autenticazione)
- **Reso campo `password` opzionale** in `DownloadRequest` — era `str` obbligatorio, ora `str | None = None`
- **Fix bottone download**: in `showReady()` il testo "Scarica MP3/MP4" ora usa `(data.format || format)` come fallback, così funziona anche se il backend non restituisce il campo `format`

### Nuove feature
- **Download video MP4** — aggiunto selettore Audio/Video nel frontend, qualità 480p/720p/1080p
- **Video clip** — la feature clip ora funziona anche per MP4 (re-encode con libx264 per allineamento keyframe)
- **`VIDEO_FORMAT_MAP`** nel backend con formati yt-dlp ottimizzati per compatibilità (preferisce codec avc1)
- **Progress hook reale** da yt-dlp + monitor thread per fallback su file .part

### Organizzazione progetto
- Eliminati file spuri: `cookies.txt` (root), `backend/cookies.txt`, `backend/index.html`
- Creata cartella `assets/` con icone e file di documentazione visuale
- Creata cartella `deploy/` con `render.yaml` e `netlify.toml`
- Creata cartella `docs/` con `DISTRIBUTION.md`, `SETUP.md`, `Drops_Roadmap_Strategica.docx`
- Aggiunto `assets/drops_project_schema.html` — schema struttura progetto
- Aggiunto `assets/drops_feature_analysis.html` — analisi roadmap feature

### Dipendenze
- Allineate versioni tra `requirements.txt`, `start.sh` e `launch-desktop.sh` (erano inconsistenti: pydantic v1 vs v2, fastapi 0.95 vs 0.111)
- `yt-dlp` aggiornato a `>=2025.1.15`

### Script
- **Creato `build-dmg.sh`** — script completo per compilare il DMG: installa Rust/Node/ffmpeg/Python se mancanti, aggiorna il venv, esegue `npm run tauri build`, apre la cartella con il DMG prodotto

### Documentazione
- **Creato `CLAUDE.md`** — file strategico letto dall'agente prima di operare: architettura, vincoli, roadmap, regole operative
- **Creato `CHANGELOG.md`** — questo file

---

## Prima del 2026-05-29 (stato iniziale)

- Backend FastAPI con download audio MP3/FLAC
- Feature clip audio (parzialmente funzionante)
- Frontend HTML singolo file con UI dark
- Tauri v2 wrapper desktop
- Script `start.sh` e `launch-desktop.sh`
