#!/bin/bash

echo "🎵 Avvio Drops..."

# Vai nella cartella del progetto
cd "$(dirname "$0")"

# Killa istanze precedenti per evitare port collision
pkill -f "uvicorn main:app" 2>/dev/null
sleep 1

# Controlla Homebrew
if ! command -v brew &>/dev/null; then
  echo "❌ Homebrew non trovato. Installa da https://brew.sh"
  exit 1
fi

# Installa ffmpeg se mancante
if ! command -v ffmpeg &>/dev/null; then
  echo "📦 Installando ffmpeg..."
  brew install ffmpeg
fi

# Installa yt-dlp se mancante
if ! command -v yt-dlp &>/dev/null; then
  echo "📦 Installando yt-dlp..."
  brew install yt-dlp
fi

# Python 3.11+ richiesto per compatibilità con pydantic v2
if ! command -v python3.11 &>/dev/null && ! command -v python3.12 &>/dev/null && ! command -v python3.13 &>/dev/null; then
  echo "🐍 Installando Python 3.11..."
  brew install python@3.11
fi

# Scegli il python disponibile
PYTHON_BIN=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3)

# Crea virtual environment se non esiste
if [ ! -d ".venv" ]; then
  echo "🐍 Creando ambiente Python..."
  "$PYTHON_BIN" -m venv .venv
fi

# Forza PATH Homebrew
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Attiva venv e installa dipendenze (allineate a requirements.txt)
source .venv/bin/activate
pip install --quiet \
  "fastapi==0.111.0" \
  "uvicorn[standard]==0.29.0" \
  "pydantic==2.7.1" \
  "python-multipart==0.0.9" \
  "yt-dlp>=2025.1.15"

# Porta
PORT=8000

echo ""
echo "✅ Tutto pronto!"
echo "🌐 Aprendo http://localhost:$PORT"
echo "🛑 Per fermare: Ctrl+C"
echo ""

# Apri il browser dopo 2 secondi
(sleep 2 && open "http://localhost:$PORT") &

# Avvia il server dalla cartella backend
cd backend
uvicorn main:app --host 0.0.0.0 --port $PORT
