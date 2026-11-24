#!/bin/bash
# Usage: overlay.sh <main video> <talking avatar video> <output.mp4> [size px] [margin px]
set -eu
MAIN="$1"; AV="$2"; OUT="$3"; D="${4:-190}"; M="${5:-18}"; R=6   # R = green ring width
DI=$((D-2*R))
ffmpeg -y -v error -i "$MAIN" -i "$AV" -filter_complex "
[1:v]fps=30,scale=${DI}:${DI},format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-1),255,0)'[face];
color=c=0x1B7A3E:s=${D}x${D}:r=30,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-1),255,0)'[ring];
[ring][face]overlay=${R}:${R}:shortest=1[badge];
[0:v][badge]overlay=W-w-${M}:H-h-106:eof_action=pass,format=yuv420p[v]" \
 -map "[v]" -map 0:a -c:v libx264 -crf 18 -preset medium -c:a copy -movflags +faststart "$OUT"
