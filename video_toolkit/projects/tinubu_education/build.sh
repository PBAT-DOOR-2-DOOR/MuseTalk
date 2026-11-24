#!/bin/bash
# Rebuild the Tinubu education video from the inputs in this folder:
#   TV 1920x1080 25 fps at -23 LUFS, and iPhone 1080x1920 25 fps at -14 LUFS.
#
#   bash build.sh               # uses the saved presenter lipsync (inputs/presenter_talking.mp4)
#   bash build.sh --relipsync   # re-runs MuseTalk on the presenter (~15 min on Apple silicon)
#
# Voice: ElevenLabs "Pastie" (inputs/voice_final.wav = voice_take2.mp3 up to 39.36 s + brought_b.mp3), PBAT written as "Pee-Bat" so it's said as one word.
# Music: the healthcare campaign's music bed (Demucs no_vocals stem). End card: the healthcare end card.
set -euo pipefail
cd "$(dirname "$0")"
P="$PWD"; TK="$(cd ../.. && pwd)"; TOOLS="$TK/tools"; HC="$TK/projects/nigerian_healthcare"
REPO="${MUSETALK_DIR:-$HOME/MuseTalk}"
source "$REPO/.venv-mac/bin/activate"
[ -x /opt/homebrew/bin/brew ] && export PATH="/opt/homebrew/bin:$PATH"
W="$P/work"; OUT="$P/output"; mkdir -p "$W" "$OUT" cards slides
AV="$TK/assets/avatar/presenter_woman.png"; ALPHA="$TK/assets/avatar/presenter_woman_alpha.png"

echo "== 1/6 Voice and music"
ffmpeg -y -v error -i inputs/voice_final.wav -af apad=whole_dur=45.5 -ar 44100 -ac 2 "$W/voice.wav"
[ -s "$W/stems/no_vocals.wav" ] || bash "$TOOLS/separate_voice.sh" "$HC/inputs/original.mp4" "$W/stems"
ffmpeg -y -v error -i "$W/voice.wav" -i "$W/stems/no_vocals.wav" -filter_complex \
  "[0:a]volume=8dB,alimiter=limit=0.89:level=false[v];[1:a]volume=-2dB,atrim=0:45.5,afade=t=out:st=44.0:d=1.5[m];[v][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95:level=false[a]" \
  -map "[a]" -ar 48000 -ac 2 "$W/mix.wav"
bash "$TOOLS/loudnorm.sh" "$W/mix.wav" "$W/mix_tv.wav" -23
bash "$TOOLS/loudnorm.sh" "$W/mix.wav" "$W/mix_social.wav" -14

echo "== 2/6 Presenter lipsync"
if [ "${1:-}" = "--relipsync" ] || [ ! -s inputs/presenter_talking.mp4 ]; then
  ffmpeg -y -v error -loop 1 -i "$AV" -t 45.5 -r 25 -c:v libx264 -pix_fmt yuv420p "$W/presenter_base.mp4"
  ffmpeg -y -v error -i "$W/voice.wav" -af "agate=threshold=0.02:ratio=8:attack=5:release=120" -ar 16000 -ac 1 "$W/voice_16k.wav"
  bash "$TOOLS/run_lipsync.sh" "$W/presenter_base.mp4" "$W/voice_16k.wav" "$P/inputs/presenter_talking.mp4"
fi

echo "== 3/6 Slides (widescreen and vertical)"
python -I make_slides.py slides
python -I make_slides_vertical.py slides_v

echo "== 4/6 Photo cards"
MC="$TOOLS/make_cards.py"
python -I "$MC" "$HC/photos/tinubu.jpg"   "Bola Ahmed Tinubu" 0,0,495,538  cards/tinubu.png   "" 443 491 1.875
python -I "$MC" "$HC/photos/shettima.jpg" "Kashim Shettima"   12,0,531,564 cards/shettima.png "" 443 491 1.875
python -I "$MC" "$HC/photos/tompolo.webp" "High Chief Government Oweizide Ekpemupolo|(Tompolo)" 250,40,770,510 cards/tompolo.png "Grand Patron" 338 300 1.875
python -I "$MC" "$HC/photos/asuku.jpg"    "Comrade Sunday Adekanbi Asuku" 0,0,310,280 cards/asuku.png "National Coordinator" 338 248 1.875
mkdir -p cards_v
python -I "$MC" "$HC/photos/tinubu.jpg"   "Bola Ahmed Tinubu" 0,0,495,520  cards_v/tinubu.png   "" 420 380 1.9
python -I "$MC" "$HC/photos/shettima.jpg" "Kashim Shettima"   20,0,523,455 cards_v/shettima.png "" 420 380 1.9
python -I "$MC" "$HC/photos/tompolo.webp" "High Chief Government Oweizide Ekpemupolo|(Tompolo)" 250,40,770,472 cards_v/tompolo.png "Grand Patron" 420 350 1.9
python -I "$MC" "$HC/photos/asuku.jpg"    "Comrade Sunday Adekanbi Asuku" 0,0,310,258 cards_v/asuku.png "National Coordinator" 420 350 1.9

echo "== 5/6 End card: clean plate + animated 'brought to you by' lines (from the healthcare end card)"
python -I "$HC/patch_source.py" "$HC/inputs/original.mp4" "$W/source_patched.mp4"
ffmpeg -y -v error -sseof -0.4 -i "$W/source_patched.mp4" -frames:v 1 -vf "scale=1920:1080:flags=lanczos" "$W/end_last.png"
python -I make_endcard.py "$W/end_last.png" slides slides_v

echo "== 6/6 Composite"
python -I composite.py slides inputs/presenter_talking.mp4 "$ALPHA" "$W/mix_tv.wav" \
  "$OUT/tinubu_education_presenter_TV_1080p25.mp4"
python -I composite_vertical.py slides_v inputs/presenter_talking.mp4 "$ALPHA" "$W/mix_social.wav" \
  "$OUT/tinubu_education_presenter_iphone.mp4"
echo; ls -lh "$OUT"
