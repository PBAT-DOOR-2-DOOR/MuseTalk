"""Replace text lines baked into the end card, each following its original fade-in.

Usage: python patch_source.py <in.mp4> <out.mp4>
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC, OUT = sys.argv[1:3]
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
T_START = 41.55                    # end card visible (after the fade through black)

# each: new text, font size, weight index (5 Medium, 7 Regular), RGB colour,
#       box to clear (x0,y0,x1,y1), text centre, original-text detector threshold
LINES = [
    ("This message is approved by the", 30, 5, (239, 251, 242),
     (262, 232, 762, 275), ((302 + 721) / 2, (239 + 266) / 2), 160),
    ("Some people shown are illustrative; named individuals are real.", 17, 7, (188, 233, 208),
     (230, 512, 794, 536), (512, (516 + 531) / 2), 120),
]


def coons(frame, box):
    """Fill box with a Coons patch built from the pixels just outside all four edges."""
    x0, y0, x1, y1 = box
    f = frame.astype(np.float32)
    left = f[y0:y1, x0 - 6:x0 - 1].mean(1)
    right = f[y0:y1, x1 + 1:x1 + 6].mean(1)
    # median along the edge so stray glyph pixels (e.g. descenders of the line above) don't streak
    top = cv2.medianBlur(f[y0 - 4:y0 - 1, x0:x1].mean(0)[None].astype(np.uint8), 31)[0].astype(np.float32)
    bottom = cv2.medianBlur(f[y1 + 1:y1 + 4, x0:x1].mean(0)[None].astype(np.uint8), 31)[0].astype(np.float32)
    h, w = y1 - y0, x1 - x0
    u = np.linspace(0, 1, w)[None, :, None]
    v = np.linspace(0, 1, h)[:, None, None]
    tl, tr, bl, br = top[0], top[-1], bottom[0], bottom[-1]
    return ((1 - v) * top[None] + v * bottom[None]
            + (1 - u) * left[:, None] + u * right[:, None]
            - ((1 - u) * (1 - v) * tl + u * (1 - v) * tr + (1 - u) * v * bl + u * v * br))


cap = cv2.VideoCapture(SRC)
fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(3)), int(cap.get(4))
cap.set(cv2.CAP_PROP_POS_MSEC, 46000)
_, ref = cap.read()

prepared = []
for text, size, weight, rgb, box, center, thr in LINES:
    x0, y0, x1, y1 = box
    sub = ref[y0:y1, x0:x1].astype(int)
    mask = sub.min(2) > thr                                   # original text pixels
    contrast = (ref[y0:y1, x0:x1].astype(np.float32) - coons(ref, box)).mean(2)[mask].mean()
    layer = Image.new("L", (W, H), 0)
    ImageDraw.Draw(layer).text(center, text, font=ImageFont.truetype(AVENIR, size, index=weight),
                               fill=255, anchor="mm")
    alpha = np.asarray(layer, np.float32)[y0:y1, x0:x1, None] / 255.0
    prepared.append((box, mask, contrast, alpha, np.array(rgb[::-1], np.float32)[None, None, :]))

cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
enc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
     "-r", str(fps), "-i", "-", "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
     "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", OUT],
    stdin=subprocess.PIPE)
n = 0
while True:
    ok, f = cap.read()
    if not ok:
        break
    if n / fps >= T_START:
        for (x0, y0, x1, y1), mask, ref_c, alpha, colour in prepared:
            bg = coons(f, (x0, y0, x1, y1))
            c = (f[y0:y1, x0:x1].astype(np.float32) - bg).mean(2)[mask].mean()
            k = float(np.clip(c / ref_c, 0, 1))              # follow the original fade-in
            a = alpha * k
            f[y0:y1, x0:x1] = np.clip(bg * (1 - a) + colour * a, 0, 255).astype(np.uint8)
    enc.stdin.write(f.tobytes())
    n += 1
enc.stdin.close()
enc.wait()
print("frames", n, "exit", enc.returncode)
