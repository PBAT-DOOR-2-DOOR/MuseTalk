#!/bin/bash
# Usage: bash ~/MuseTalk/run_lipsync.sh <base video> <audio wav> [output.mp4] [mps|cpu]
# Tries the Apple GPU first, then falls back to CPU if no video is produced.
set -u
REPO="$HOME/MuseTalk"
VID="${1:?base video}"; AUD="${2:?audio file}"
OUT="${3:-$HOME/projects/musetalk/out_musetalk.mp4}"; DEV="${4:-auto}"
[ -x /opt/homebrew/bin/brew ] && export PATH="/opt/homebrew/bin:$PATH"
VID="$(cd "$(dirname "$VID")" && pwd)/$(basename "$VID")"; AUD="$(cd "$(dirname "$AUD")" && pwd)/$(basename "$AUD")"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT";; esac
cd "$REPO" || exit 1
source .venv-mac/bin/activate
rm -rf data/local results/local; mkdir -p data/local results/local "$(dirname "$OUT")"
ffmpeg -y -v error -i "$VID" -an -c:v libx264 -pix_fmt yuv420p -r 25 data/local/base.mp4 || { echo "Could not read video $VID"; exit 1; }
ffmpeg -y -v error -i "$AUD" -ar 16000 -ac 1 data/local/voice.wav || { echo "Could not read audio $AUD"; exit 1; }
printf 'task_0:\n video_path: "data/local/base.mp4"\n audio_path: "data/local/voice.wav"\n result_name: "out.mp4"\n' > configs/inference/local.yaml
RES="results/local/v15/out.mp4"
run_once() {
  echo ">>> running on: $1"; rm -f "$RES"
  MUSETALK_DEVICE="$1" PYTORCH_ENABLE_MPS_FALLBACK=1 /usr/bin/time -l python -m scripts.inference \
    --inference_config configs/inference/local.yaml --result_dir results/local \
    --unet_model_path models/musetalkV15/unet.pth --unet_config models/musetalkV15/musetalk.json \
    --version v15 --batch_size 4 --ffmpeg_path "$(dirname "$(command -v ffmpeg)")"
  [ -s "$RES" ]
}
if [ "$DEV" = "auto" ]; then run_once mps || run_once cpu; else run_once "$DEV"; fi
if [ -s "$RES" ]; then cp "$RES" "$OUT"; echo "LIPSYNC_RESULT=OK $OUT"; else echo "LIPSYNC_RESULT=FAILED"; exit 1; fi
