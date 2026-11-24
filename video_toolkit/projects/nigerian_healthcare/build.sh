#!/bin/bash
# Rebuild every deliverable of the Nigerian healthcare video from the inputs in this folder.
#
#   bash build.sh               # uses the saved presenter lipsync (inputs/presenter_talking.mp4)
#   bash build.sh --relipsync   # re-runs MuseTalk on the presenter too (~12 min on Apple silicon)
#
# Outputs go to ./output/: widescreen, iPhone (9:16), TV 1080p25 (-23 LUFS) and the 10 s end slate.
set -euo pipefail
cd "$(dirname "$0")"
P="$PWD"; TK="$(cd ../.. && pwd)"; TOOLS="$TK/tools"
REPO="${MUSETALK_DIR:-$HOME/MuseTalk}"
source "$REPO/.venv-mac/bin/activate"
[ -x /opt/homebrew/bin/brew ] && export PATH="/opt/homebrew/bin:$PATH"
W="$P/work"; OUT="$P/output"; mkdir -p "$W" "$OUT" cards cards_v cards_tv
AV="$TK/assets/avatar/presenter_woman.png"; ALPHA="$TK/assets/avatar/presenter_woman_alpha.png"

echo "== 1/7 Separate the original voiceover from the music"
bash "$TOOLS/separate_voice.sh" inputs/original.mp4 "$W/stems"

echo "== 2/7 Female voice: Pastie take with the end line replaced by the 'Pee-Bat' take"
ffmpeg -y -v error -i inputs/voice_pastie_full.mp3 -ar 44100 -ac 2 "$W/voice_full.wav"
ffmpeg -y -v error -i inputs/voice_pastie_endline_PeeBat.mp3 \
  -af "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse" \
  -ar 44100 -ac 2 "$W/endline.wav"
ffmpeg -y -v error -i "$W/voice_full.wav" -i "$W/endline.wav" -filter_complex \
  "[0:a]volume=enable='gte(t,42.0)':volume=0[a];[1:a]volume=-0.9dB,adelay=42070|42070[b];[a][b]amix=inputs=2:normalize=0:duration=first" \
  -ar 44100 -ac 2 "$W/voice.wav"
ffmpeg -y -v error -i "$W/voice.wav" -i "$W/stems/no_vocals.wav" -filter_complex \
  "[0:a]volume=12dB,alimiter=limit=0.89:level=false[v];[v][1:a]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.95:level=false[a]" \
  -map "[a]" -ar 44100 -ac 2 "$W/mix.wav"
bash "$TOOLS/loudnorm.sh" "$W/mix.wav" "$W/mix_tv.wav" -23

echo "== 3/7 Presenter lipsync"
if [ "${1:-}" = "--relipsync" ]; then
  ffmpeg -y -v error -loop 1 -i "$AV" -t 47.5 -r 25 -c:v libx264 -pix_fmt yuv420p "$W/presenter_base.mp4"
  ffmpeg -y -v error -i "$W/voice.wav" -af "agate=threshold=0.02:ratio=8:attack=5:release=120" -ar 16000 -ac 1 "$W/voice_16k.wav"
  bash "$TOOLS/run_lipsync.sh" "$W/presenter_base.mp4" "$W/voice_16k.wav" "$W/presenter_talking.mp4"
  TALK="$W/presenter_talking.mp4"
else
  TALK="$P/inputs/presenter_talking.mp4"
fi

echo "== 4/7 End-card text: 'This message is approved by the' + new disclosure line"
python -I patch_source.py inputs/original.mp4 "$W/source_patched.mp4"

echo "== 5/7 Photo cards (widescreen, iPhone, TV sizes)"
MC="python -I $TOOLS/make_cards.py"
TOMPOLO="High Chief Government Oweizide Ekpemupolo|(Tompolo)"; ASUKU="Comrade Sunday Adekanbi Asuku"
$MC photos/tinubu.jpg   "Bola Ahmed Tinubu" 0,0,495,538  cards/tinubu.png
$MC photos/shettima.jpg "Kashim Shettima"   12,0,531,564 cards/shettima.png
$MC photos/tompolo.webp "$TOMPOLO" 250,40,770,510 cards/tompolo.png "Grand Patron" 180 160
$MC photos/asuku.jpg    "$ASUKU"   0,0,310,280    cards/asuku.png   "National Coordinator" 180 132
$MC photos/tinubu.jpg   "Bola Ahmed Tinubu" 0,0,495,520  cards_v/tinubu.png   "" 420 380 1.9
$MC photos/shettima.jpg "Kashim Shettima"   20,0,523,455 cards_v/shettima.png "" 420 380 1.9
$MC photos/tompolo.webp "$TOMPOLO" 250,40,770,472 cards_v/tompolo.png "Grand Patron" 420 350 1.9
$MC photos/asuku.jpg    "$ASUKU"   0,0,310,258    cards_v/asuku.png   "National Coordinator" 420 350 1.9
$MC photos/tinubu.jpg   "Bola Ahmed Tinubu" 0,0,495,538  cards_tv/tinubu.png   "" 443 491 1.875
$MC photos/shettima.jpg "Kashim Shettima"   12,0,531,564 cards_tv/shettima.png "" 443 491 1.875
$MC photos/tompolo.webp "$TOMPOLO" 250,40,770,510 cards_tv/tompolo.png "Grand Patron" 338 300 1.875
$MC photos/asuku.jpg    "$ASUKU"   0,0,310,280    cards_tv/asuku.png   "National Coordinator" 338 248 1.875

echo "== 6/7 Widescreen, iPhone and TV versions"
python -I composite.py "$W/source_patched.mp4" "$TALK" "$ALPHA" "$OUT/nigerian_healthcare_presenter.mp4" "$W/mix.wav"
python -I composite_vertical.py "$W/source_patched.mp4" "$TALK" "$ALPHA" "$W/mix.wav" "$OUT/nigerian_healthcare_presenter_iphone.mp4"
ffmpeg -y -v error -i "$W/source_patched.mp4" -vf "fps=25,scale=1920:1080:flags=lanczos" -c:v libx264 -crf 10 -preset medium -pix_fmt yuv420p -an "$W/source_tv.mp4"
python -I composite_tv.py "$W/source_tv.mp4" "$TALK" "$ALPHA" "$OUT/nigerian_healthcare_presenter_TV_1080p25.mp4" "$W/mix_tv.wav"

echo "== 7/7 End slate (10 s, TV spec)"
ffmpeg -y -v error -ss 46 -i "$W/source_tv.mp4" -frames:v 1 "$W/endcard_bg.png"
ffmpeg -y -v error -ss 37.5 -t 10 -i "$W/stems/no_vocals.wav" -i "$W/endline.wav" -filter_complex \
  "[0:a]afade=t=in:d=0.4[m];[1:a]volume=11.1dB,adelay=500|500,apad[v];[v][m]amix=inputs=2:normalize=0:duration=shortest,alimiter=limit=0.95:level=false" \
  -ar 48000 -ac 2 "$W/endslate_raw.wav"
bash "$TOOLS/loudnorm.sh" "$W/endslate_raw.wav" "$W/endslate_audio.wav" -23
python -I make_endslate.py "$W/endcard_bg.png" "$W/endslate_audio.wav" "$OUT/PBAT_endslate_TV_1080p25.mp4"

echo; echo "Done. Videos in $OUT:"; ls -lh "$OUT"
