#!/bin/bash
# Two-pass loudness normalisation to a target, 48 kHz stereo WAV out.
# Usage: loudnorm.sh <in audio/video> <out.wav> [target LUFS, default -23 (TV/EBU R128); use -14 for social]
set -euo pipefail
IN="${1:?input}"; OUT="${2:?output wav}"; I="${3:--23}"
J=$(ffmpeg -hide_banner -i "$IN" -vn -af "loudnorm=I=$I:TP=-2:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
get() { echo "$J" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
ffmpeg -y -v error -i "$IN" -vn -af "loudnorm=I=$I:TP=-2:LRA=11:measured_I=$(get input_i):measured_TP=$(get input_tp):measured_LRA=$(get input_lra):measured_thresh=$(get input_thresh):offset=$(get target_offset):linear=true,aresample=48000" -ar 48000 -ac 2 "$OUT"
echo "Input was $(get input_i) LUFS; wrote $OUT at $I LUFS"
