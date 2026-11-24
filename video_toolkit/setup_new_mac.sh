#!/bin/bash
# One-time setup of the lipsync + video editing toolkit on an Apple-silicon Mac (M1 or newer).
#
#   bash setup_new_mac.sh                                   # downloads model weights (~4 GB)
#   MODELS_FROM=/Volumes/USB/models bash setup_new_mac.sh   # or copy weights from a drive
#
# Safe to run again: every step skips what is already in place. Takes 30-60 min the first time
# (mmcv is compiled from source). Installs into ~/MuseTalk unless MUSETALK_DIR is set.
set -euo pipefail
TK_SRC="$(cd "$(dirname "$0")" && pwd)"
REPO="${MUSETALK_DIR:-$HOME/MuseTalk}"
MUSETALK_COMMIT=0a89dec           # the MuseTalk version this toolkit was built and tested on
log()  { printf "\n\033[1;32m==> %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m!! %s\033[0m\n" "$*"; }

[ "$(uname -m)" = "arm64" ] || { echo "This setup is for Apple-silicon Macs (M1 or newer)."; exit 1; }

log "1/9 Xcode command line tools (compiler needed for mmcv)"
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install || true
  echo "Finish the installer window that just opened, then run this script again."; exit 1
fi

log "2/9 Homebrew, Python 3.10, ffmpeg, git"
if [ ! -x /opt/homebrew/bin/brew ]; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.10 ffmpeg git

log "3/9 MuseTalk source code"
if [ ! -d "$REPO/.git" ]; then
  git clone https://github.com/TMElyralab/MuseTalk.git "$REPO"
  git -C "$REPO" checkout -q "$MUSETALK_COMMIT"
fi
PATCH="$TK_SRC/patches/inference_mps_device.patch"
if git -C "$REPO" apply --check "$PATCH" 2>/dev/null; then
  git -C "$REPO" apply "$PATCH" && echo "Applied Apple-GPU (MPS) patch to scripts/inference.py"
else
  echo "MPS patch already applied"
fi

log "4/9 Toolkit files"
if [ "$TK_SRC" != "$REPO/video_toolkit" ]; then
  mkdir -p "$REPO/video_toolkit"
  rsync -a --exclude work --exclude output "$TK_SRC/" "$REPO/video_toolkit/"
fi
cp "$REPO/video_toolkit/tools/run_lipsync.sh" "$REPO/run_lipsync.sh"
chmod +x "$REPO"/video_toolkit/tools/*.sh "$REPO"/video_toolkit/projects/*/build.sh "$REPO/run_lipsync.sh"

log "5/9 Python environment (exact versions from the original Mac)"
cd "$REPO"
[ -d .venv-mac ] || /opt/homebrew/bin/python3.10 -m venv .venv-mac
source .venv-mac/bin/activate
pip install -q --upgrade pip "setuptools<70" wheel
pip install -q torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2
pip install -q -r "$REPO/video_toolkit/requirements-mac.txt"
if python -c "import mmcv.ops" 2>/dev/null; then
  echo "mmcv with ops already installed"
else
  echo "Compiling mmcv 2.0.1 with ops (10-20 minutes, this is normal)..."
  # Xcode 26+ (macOS 26 SDK) rejects a std::is_arithmetic specialisation in torch 2.0's headers
  # ("'is_arithmetic' cannot be specialized"); this flag turns that back into an ignorable warning.
  CFLAGS="${CFLAGS:-} -Wno-invalid-specialization" CXXFLAGS="${CXXFLAGS:-} -Wno-invalid-specialization" \
    MMCV_WITH_OPS=1 pip install --no-build-isolation --no-cache-dir mmcv==2.0.1
fi

log "6/9 Model weights (~4 GB)"
mkdir -p models/musetalkV15 models/dwpose models/face-parse-bisent models/sd-vae models/whisper
if [ -n "${MODELS_FROM:-}" ]; then
  rsync -a --progress "$MODELS_FROM/" models/
fi
hf() { # repo, local dir, files... (skips when all files exist)
  local repo="$1" dir="$2"; shift 2; local missing=0
  for f in "$@"; do [ -s "$dir/$f" ] || missing=1; done
  [ $missing = 0 ] && { echo "have $repo"; return; }
  huggingface-cli download "$repo" --local-dir "$dir" --include "$@"
}
hf TMElyralab/MuseTalk     models             musetalkV15/musetalk.json musetalkV15/unet.pth
hf stabilityai/sd-vae-ft-mse models/sd-vae    config.json diffusion_pytorch_model.bin
hf openai/whisper-tiny     models/whisper     config.json pytorch_model.bin preprocessor_config.json
hf yzd-v/DWPose            models/dwpose      dw-ll_ucoco_384.pth
if [ ! -s models/face-parse-bisent/79999_iter.pth ]; then
  gdown --id 154JgKpzCPW82qINcVieuPH3fZ2e0P812 -O models/face-parse-bisent/79999_iter.pth \
    || warn "Google Drive refused the face-parse download. Copy models/face-parse-bisent/79999_iter.pth from the old Mac (see README)."
fi
[ -s models/face-parse-bisent/resnet18-5c106cde.pth ] || \
  curl -L https://download.pytorch.org/models/resnet18-5c106cde.pth -o models/face-parse-bisent/resnet18-5c106cde.pth

log "7/9 Voice separation (Demucs) and transcription (Whisper) models"
python -c "from demucs.pretrained import get_model; get_model('htdemucs'); print('demucs model ready')"
python -c "from transformers import WhisperProcessor as P, WhisperForConditionalGeneration as M; P.from_pretrained('openai/whisper-small'); M.from_pretrained('openai/whisper-small'); print('whisper-small ready')"

log "8/9 Claude memory (house rules such as PBAT pronunciation)"
for dir in "$REPO" "$REPO/video_toolkit"; do
  MEM="$HOME/.claude/projects/$(echo "$dir" | sed 's#[^A-Za-z0-9]#-#g')/memory"
  mkdir -p "$MEM"
  for f in "$REPO"/video_toolkit/claude/*.md; do
    cp "$f" "$MEM/"
    name="$(basename "$f")"
    grep -q "($name)" "$MEM/MEMORY.md" 2>/dev/null || \
      echo "- [$(sed -n 's/^name: //p' "$f")]($name) — $(sed -n 's/^description: //p' "$f" | sed 's/^"//; s/"$//; s/\\"/"/g')" >> "$MEM/MEMORY.md"
  done
done
echo "Memory installed for Claude sessions in $REPO and $REPO/video_toolkit"

log "9/9 Self-test: 3-second lipsync on the Apple GPU"
T="$(mktemp -d)"
ffmpeg -y -v error -loop 1 -i video_toolkit/assets/avatar/presenter_woman.png -t 3 -r 25 -c:v libx264 -pix_fmt yuv420p "$T/base.mp4"
ffmpeg -y -v error -ss 1 -t 3 -i video_toolkit/projects/nigerian_healthcare/inputs/voice_pastie_full.mp3 -ar 16000 -ac 1 "$T/voice.wav"
if bash "$REPO/run_lipsync.sh" "$T/base.mp4" "$T/voice.wav" "$T/test.mp4" > "$T/log.txt" 2>&1 && [ -s "$T/test.mp4" ]; then
  echo "Lipsync works."
else
  warn "Lipsync self-test failed; last lines of the log:"; tail -20 "$T/log.txt"; exit 1
fi
rm -rf "$T"

printf "\n\033[1;32mAll set.\033[0m Rebuild the Nigerian healthcare videos with:\n  bash %s/video_toolkit/projects/nigerian_healthcare/build.sh\n" "$REPO"
