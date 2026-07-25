#!/usr/bin/env bash
# Drops — build Drops.icns from the included PNGs
# Run on macOS:  bash build-icns.sh
set -e

cd "$(dirname "$0")"

# rename *-2x.png -> *@2x.png inside the iconset
cd Drops.iconset
for f in *-2x.png; do
  [ -e "$f" ] || continue
  mv "$f" "${f/-2x.png/@2x.png}"
done
cd ..

# build the .icns
iconutil -c icns Drops.iconset -o Drops.icns
echo "✓ Drops.icns created"
