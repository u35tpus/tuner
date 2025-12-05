#!/usr/bin/env bash
# Small helper script to download a commonly used Salamander Grand Piano SF2.
# Edit the URL below if you prefer another mirror.

set -euo pipefail
mkdir -p "$(dirname "$0")"
OUT="$(dirname "$0")/SalamanderGrandPiano.sf2"
URL="https://github.com/uriel1998/SalamanderGrandPiano/raw/master/SalamanderGrandPiano-v3.0.sf2"

echo "Downloading Salamander Grand Piano SF2 to $OUT"
curl -L -o "$OUT" "$URL"
echo "Done. If fluidsynth is installed, the trainer can use this SF2."
