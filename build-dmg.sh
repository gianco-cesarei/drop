#!/bin/bash
# ─── Build Drops.dmg ────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

echo "🔨 Build Drops DMG..."

SIGNING_IDENTITY="${APPLE_SIGNING_IDENTITY:-}"
NOTARY_PROFILE="${DROPS_NOTARY_PROFILE:-}"

if [ -n "$NOTARY_PROFILE" ] && [ -z "$SIGNING_IDENTITY" ]; then
  echo "❌ DROPS_NOTARY_PROFILE richiede APPLE_SIGNING_IDENTITY."
  echo "   Un DMG notarizzato deve contenere un'app firmata Developer ID."
  exit 1
fi

if [ -n "$SIGNING_IDENTITY" ]; then
  if ! security find-identity -v -p codesigning | grep -Fq "$SIGNING_IDENTITY"; then
    echo "❌ Certificato non trovato nel Portachiavi:"
    echo "   $SIGNING_IDENTITY"
    echo "   Identità disponibili:"
    security find-identity -v -p codesigning || true
    exit 1
  fi
  echo "🔐 Firma Developer ID attiva."
else
  echo "⚠️  Build locale non firmata."
  echo "   Gatekeeper mostrerà un avviso sui Mac diversi da questo."
  echo "   Per distribuzione senza avvisi configura APPLE_SIGNING_IDENTITY"
  echo "   e DROPS_NOTARY_PROFILE. Vedi docs/DISTRIBUTION.md."
fi

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
  "yt-dlp>=2025.1.15" \
  "pyinstaller>=6.0"

echo "📦 Compilando backend locale..."
pyinstaller --clean --noconfirm backend/drops-backend.spec
mkdir -p src-tauri/binaries
cp dist/drops-backend src-tauri/binaries/drops-backend
chmod +x src-tauri/binaries/drops-backend

echo "🎞  Preparando ffmpeg locale..."
if [ -e src-tauri/binaries/ffmpeg ]; then
  chmod u+w src-tauri/binaries/ffmpeg
fi
cp "$(command -v ffmpeg)" src-tauri/binaries/ffmpeg
chmod +x src-tauri/binaries/ffmpeg
deactivate

# Installa dipendenze npm
echo "📦 Installando dipendenze npm..."
npm install

# Build DMG
echo "🏗  Compilando app (ci vuole qualche minuto la prima volta)..."
# Tauri ricopia risorse sopra output precedente; ffmpeg può conservare modo 555.
find src-tauri/target/release -path "*/ffmpeg/ffmpeg" -exec chmod u+w {} \; 2>/dev/null || true
npm run tauri build

# Trova artefatti prodotti
APP=$(find src-tauri/target/release/bundle/macos -name "*.app" -type d -print -quit 2>/dev/null)
DMG=$(find src-tauri/target/release/bundle/dmg -name "*.dmg" -type f -print -quit 2>/dev/null)

if [ -z "$APP" ]; then
  echo "❌ Drops.app non trovata dopo la build."
  exit 1
fi

if [ -n "$SIGNING_IDENTITY" ]; then
  echo "🔎 Verifica firma applicazione..."
  codesign --verify --deep --strict --verbose=2 "$APP"
  codesign -dv --verbose=2 "$APP" 2>&1 | grep -E "Authority=|TeamIdentifier="
fi

if [ -n "$DMG" ]; then
  GUIDE="$(dirname "$DMG")/INSTALLAZIONE_DROPS_MAC.txt"
  cp "INSTALLAZIONE_DROPS_MAC.txt" "$GUIDE"

  if [ -n "$NOTARY_PROFILE" ]; then
    echo "📨 Invio DMG ad Apple per notarizzazione..."
    xcrun notarytool submit "$DMG" \
      --keychain-profile "$NOTARY_PROFILE" \
      --wait

    echo "📎 Applico ticket notarizzazione al DMG..."
    xcrun stapler staple "$DMG"
    xcrun stapler validate "$DMG"

    echo "🛡  Verifica finale Gatekeeper..."
    spctl --assess \
      --type open \
      --context context:primary-signature \
      --verbose=4 \
      "$DMG"
  elif [ -n "$SIGNING_IDENTITY" ]; then
    echo "⚠️  App firmata ma DMG non notarizzato."
    echo "   Configura DROPS_NOTARY_PROFILE per distribuzione pubblica."
  fi

  echo ""
  echo "✅ DMG pronto: $DMG"
  echo "✅ Guida pronta: $GUIDE"
  if [ -n "$NOTARY_PROFILE" ]; then
    echo "✅ Firma e notarizzazione verificate. Gatekeeper dovrebbe aprirlo normalmente."
  else
    echo "ℹ️  Build locale/test. Segui docs/INSTALLAZIONE_MACOS.md."
  fi
  open "$(dirname "$DMG")"
else
  echo "❌ DMG non trovato. Controlla gli errori sopra."
  exit 1
fi
