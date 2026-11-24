"""Cut a presenter out of a flat, plain background (for a still avatar image).

Flood-fills the background from the top and upper side edges, feathers the edge and fades the
bottom so the chest crop isn't a hard line. Only the mouth moves after lipsync, so this one mask
works for every frame of the talking video.

Usage: python make_alpha.py <avatar.png> <alpha_out.png> [tolerance=5] [side_seed_max_y_fraction=0.62]
Check the result: <alpha_out>_check.png shows the cut-out over green.
"""
import sys

import cv2
import numpy as np

src, out = sys.argv[1:3]
tol = int(sys.argv[3]) if len(sys.argv) > 3 else 5
side_frac = float(sys.argv[4]) if len(sys.argv) > 4 else 0.62

im = cv2.imread(src)
h, w = im.shape[:2]
ff = np.zeros((h + 2, w + 2), np.uint8)
flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
side_max = int(h * side_frac)            # don't seed the sides below the shoulders
seeds = ([(x, 0) for x in range(0, w, 16)] + [(0, y) for y in range(0, side_max, 16)]
         + [(w - 1, y) for y in range(0, side_max, 16)])
for x, y in seeds:
    if ff[y + 1, x + 1] == 0:
        cv2.floodFill(im, ff, (x, y), 0, (tol,) * 3, (tol,) * 3, flags)
bg = ff[1:-1, 1:-1] > 0
alpha = (~bg).astype(np.uint8) * 255
alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
alpha = cv2.GaussianBlur(cv2.erode(alpha, np.ones((3, 3), np.uint8)), (5, 5), 0)
fade = max(8, h // 13)
ramp = np.ones(h)
ramp[h - fade:] = np.linspace(1, 0, fade)
alpha = (alpha * ramp[:, None]).astype(np.uint8)
cv2.imwrite(out, alpha)
check = im.copy()
check[alpha < 128] = (40, 120, 30)
cv2.imwrite(out.rsplit(".", 1)[0] + "_check.png", check)
print(f"background fraction {bg.mean():.2f}; wrote {out}")
