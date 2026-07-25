#!/bin/bash

echo "🎵 Avvio Drops Desktop..."

cd "$(dirname "$0")"

# Killa istanze precedenti (uvicorn + Drops.app) per evitare port collision
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "Drops.app/Contents/MacOS/drops" 2>/dev/null
sleep 1

# Controlla Homebrew
if ! command -v brew &>/dev/null; then
  echo "❌ Homebrew non trovato. Installa da https://brew.sh"
  exit 1
fi

# Installa dipendenze sistema se mancanti
if ! command -v ffmpeg &>/dev/null; then
  echo "📦 Installando ffmpeg..."
  brew install ffmpeg
fi

if ! command -v yt-dlp &>/dev/null; then
  echo "📦 Installando yt-dlp..."
  brew install yt-dlp
fi

# Installa Python 3.11 se mancante
if ! command -v python3.11 &>/dev/null; then
  echo "🐍 Installando Python 3.11..."
  brew install python@3.11
fi

# Crea venv se non esiste
if [ ! -d ".venv" ]; then
  echo "🐍 Creando ambiente Python..."
  python3.11 -m venv .venv
fi

# Installa dipendenze Python (allineate a requirements.txt)
source .venv/bin/activate
pip install --quiet \
  "fastapi==0.111.0" \
  "uvicorn[standard]==0.29.0" \
  "pydantic==2.7.1" \
  "python-multipart==0.0.9" \
  "yt-dlp>=2025.1.15"

# Installa dipendenze npm se mancanti
if [ ! -d "node_modules" ]; then
  echo "📦 Installando dipendenze npm..."
  npm install
fi

# Avvia il backend in background
echo "⚙️  Avviando backend..."
source .venv/bin/activate
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# Aspetta che il backend sia pronto (max 30 secondi)
echo "⏳ Aspettando il backend..."
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend pronto!"
    break
  fi
  sleep 1
done

echo ""
echo "✅ Avvio finestra desktop..."
echo "🛑 Per fermare: chiudi la finestra o premi Ctrl+C"
echo ""

# Avvia l'app Tauri
npm run tauri dev

# Quando Tauri si chiude, killa il backend
kill $BACKEND_PID 2>/dev/null
echo "👋 Drops chiuso."
