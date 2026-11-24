#!/bin/bash
# Split a video/audio file into voice and music stems with Demucs.
# Usage: separate_voice.sh <input video or audio> <output dir>
# Produces <output dir>/vocals.wav and <output dir>/no_vocals.wav (44.1 kHz stereo).
set -euo pipefail
IN="${1:?input file}"; OUTDIR="${2:?output dir}"
REPO="${MUSETALK_DIR:-$HOME/MuseTalk}"
source "$REPO/.venv-mac/bin/activate"
mkdir -p "$OUTDIR"
TMP="$(mktemp -d)"
ffmpeg -y -v error -i "$IN" -vn -ar 44100 -ac 2 "$TMP/full_audio.wav"
python -m demucs --two-stems=vocals -n htdemucs -o "$TMP/sep" "$TMP/full_audio.wav"
mv "$TMP/sep/htdemucs/full_audio/vocals.wav" "$TMP/sep/htdemucs/full_audio/no_vocals.wav" "$OUTDIR/"
rm -rf "$TMP"
echo "Wrote $OUTDIR/vocals.wav and $OUTDIR/no_vocals.wav"
