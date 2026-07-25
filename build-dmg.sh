#!/bin/bash
# ─── Build Drops.dmg ────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "🔨 Build Drops DMG..."

# Controlla dipendenze
if ! command -v brew &>/dev/null; then
  echo "❌ Homebrew non trovato. Installa da https://brew.sh"; exit 1
fi
if ! command -v cargo &>/dev/null; then
  echo "📦 Installando Rust..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  source "$HOME/.cargo/env"
fi
if ! command -v npm &>/dev/null; then
  echo "📦 Installando Node.js..."
  brew install node
fi
if ! command -v ffmpeg &>/dev/null; then
  echo "📦 Installando ffmpeg..."
  brew install ffmpeg
fi
if ! command -v python3.11 &>/dev/null; then
  echo "🐍 Installando Python 3.11..."
  brew install python@3.11
fi

# Aggiorna/crea il venv Python con le dipendenze corrette
echo "🐍 Aggiornando ambiente Python..."
if [ ! -d ".venv" ]; then
  python3.11 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet \
  "fastapi==0.111.0" \
  "uvicorn[standard]==0.29.0" \
  "pydantic==2.7.1" \
  "python-multipart==0.0.9" \
  "yt-dlp>=2025.1.15"
deactivate

# Installa dipendenze npm
echo "📦 Installando dipendenze npm..."
npm install

# Build DMG
echo "🏗  Compilando app (ci vuole qualche minuto la prima volta)..."
npm run tauri build

# Trova e mostra il DMG prodotto
DMG=$(find src-tauri/target/release/bundle/dmg -name "*.dmg" 2>/dev/null | head -1)
if [ -n "$DMG" ]; then
  echo ""
  echo "✅ DMG pronto: $DMG"
  open "$(dirname "$DMG")"
else
  echo "⚠️  DMG non trovato. Controlla gli errori sopra."
fi
