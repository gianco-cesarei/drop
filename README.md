# Drops

Desktop downloader per macOS basato su Tauri, FastAPI, yt-dlp e FFmpeg.

## Stato

| Piattaforma | Stato |
|---|---|
| macOS Apple Silicon | supportata, build privata `1.0.5` in verifica |
| Windows 10/11 | sperimentale, non ancora verificata da utente |

`1.0.5` diventa `1.1.0` solo dopo superamento checklist macOS.

## Funzioni

- download MP3 da YouTube e SoundCloud;
- qualità 128k, 192k, 320k e FLAC;
- download video 480p, 720p e 1080p;
- taglio clip in modalità Video;
- coda fino a 100 link;
- massimo 3 download simultanei;
- salvataggio automatico in Download;
- cartella alternativa o volume rimovibile;
- controllo nuova Release GitHub.

Usa Drops solo per contenuti che puoi legalmente scaricare.

## Struttura

```text
backend/        API locale, download e integrazioni
frontend/       interfaccia desktop
src-tauri/      shell nativa e configurazione bundle
docs/           installazione, build e distribuzione
deploy/         configurazioni web legacy
```

Materiali personali, PDF, roadmap e mockup non fanno parte del repository.

## Sviluppo macOS

Prerequisiti:

- Python 3.11;
- Node.js 20;
- Rust;
- FFmpeg.

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm install
./launch-desktop.sh
```

## Build macOS

Build privata non notarizzata:

```bash
./build-dmg.sh
```

Build pubblica:

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: NOME (TEAM_ID)"
export DROPS_NOTARY_PROFILE="drops-notary"
./build-dmg.sh
```

Firma e notarizzazione pubblica richiedono Apple Developer Program.

## Windows

Build Windows avviabile manualmente da GitHub Actions. Installer resta artifact
interno finché test Windows 10/11 non passa.

Vedi:

- `docs/WINDOWS_BUILD.md`;
- `docs/RELEASE.md`;
- `docs/DISTRIBUTION.md`;
- `docs/INSTALLAZIONE_MACOS.md`.

## Dati locali

Configurazione e log:

```text
~/.drops/
~/.drops/logs/backend.log
```

Download predefiniti:

```text
~/Downloads
```
