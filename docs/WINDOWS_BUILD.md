# Build Windows di Drops

Questo documento spiega come si produce l'installer `.exe` di Drops per Windows.

## Perché serve la CI (non si compila dal Mac)

Tauri **non** fa cross-compile affidabile verso Windows da macOS. L'installer va
quindi costruito su una macchina Windows. Il progetto usa **GitHub Actions**
(runner `windows-latest`) così non serve un PC Windows fisico.

## Architettura della build Windows

A differenza della build macOS — dove `main.rs` lancia il Python del venv del
progetto — su Windows l'app è **autonoma**:

1. **Backend impacchettato**: `backend/run_backend.py` viene congelato con
   PyInstaller (`backend/drops-backend.spec`) in un singolo `drops-backend.exe`
   che contiene FastAPI, uvicorn e yt-dlp. Nessun Python richiesto sul PC utente.
2. **ffmpeg**: un `ffmpeg.exe` statico viene scaricato e impacchettato come
   risorsa Tauri.
3. **Tauri**: `src-tauri/tauri.windows.conf.json` dichiara le risorse
   (`drops-backend.exe` + `ffmpeg/ffmpeg.exe`). All'avvio, `main.rs` (ramo
   `#[cfg(target_os = "windows")]`) esegue il backend dalle risorse, gli passa la
   cartella di ffmpeg via `DROPS_FFMPEG_DIR`, attende che la porta 8000 risponda,
   poi apre la WebView.

Il backend Python è stato reso cross-platform (`backend/main.py`): rileva
`ffmpeg.exe`, usa una cartella temporanea di sistema per i download e non forza
più i path Homebrew su Windows.

## Come lanciare la build

Serve un repository GitHub (attualmente il progetto non ha un `remote`).

1. Crea un repo su GitHub e collegalo:
   ```bash
   git init            # se non già inizializzato
   git add .
   git commit -m "Setup build Windows"
   git remote add origin https://github.com/<utente>/drops.git
   git push -u origin main
   ```
2. Su GitHub apri **Actions → Build Windows Installer → Run workflow**
   (trigger `workflow_dispatch`). In alternativa, un push di un tag `v*`
   (es. `git tag v1.0.0 && git push --tags`) avvia la build automaticamente.
3. A fine build scarica l'artifact **`drops-windows-installer`**: contiene il
   `Drops_x.y.z_x64-setup.exe` (installer NSIS).

## File coinvolti

- `.github/workflows/windows-build.yml` — pipeline CI
- `backend/drops-backend.spec` — spec PyInstaller
- `backend/run_backend.py` — entry point del backend congelato
- `src-tauri/tauri.windows.conf.json` — config Tauri specifica Windows
- `src-tauri/src/main.rs` — avvio backend per-piattaforma

## Note e limiti

- La build macOS resta invariata: `tauri.windows.conf.json` è ignorato fuori da
  Windows e il ramo macOS di `main.rs` è quello storico.
- L'icona `.ico` (assente nel repo) viene generata in CI con `tauri icon`.
- Prima build reale = primo vero test: qui è stato validato tutto ciò che è
  verificabile su Mac (sintassi Python, JSON, YAML), ma la compilazione Windows
  va confermata dal primo run del workflow.
- ffmpeg è una build **GPL** statica (BtbN): rilevante solo per un'eventuale
  distribuzione pubblica.
