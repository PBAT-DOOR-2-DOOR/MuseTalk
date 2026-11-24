"""Overlay a cut-out talking avatar that glides to a different empty spot on each slide.

Usage: python composite.py <main.mp4> <avatar_talking.mp4> <alpha.png> <out.mp4>
Edit SPOTS to move her: (slide start time s, x, y, size px) in 1024x576 frame coords.
"""
import subprocess
import sys

import cv2
import numpy as np

MAIN, AV, ALPHA, OUT = sys.argv[1:5]
AUDIO = sys.argv[5] if len(sys.argv) > 5 else MAIN  # optional replacement soundtrack

SPOTS = [
    (0.0, 40, 175, 230),    # title: empty dark left side
    (7.0, 620, 52, 168),    # Bala: top, between header and man's cap
    (16.2, 560, 50, 160),   # Ejiro: top-middle, above headwrap
    (24.5, 470, 68, 190),   # Charity: top-middle, left of the bow
    (33.2, 774, 352, 205),  # Choose: below Shettima's card, right side
    (41.5, 22, 288, 180),   # end card: left column, under Tompolo's card
]
MOVE = 0.8  # seconds to glide between spots

# Photo cards on the closing slide: (png, appear at s, x, y, scale, gone at s)
CARDS_DIR = __import__("os").path.join(__import__("os").path.dirname(__file__), "cards")
CARDS = [
    ("tinubu.png", 33.8, 45, 78, 0.85, 41.3),
    ("shettima.png", 35.0, 779, 78, 0.85, 41.3),
    # end card "approved by PBAT Door to Door Movement"
    ("tompolo.png", 42.0, 18, 24, 1.0, 99),
    ("asuku.png", 43.0, 826, 24, 1.0, 99),
]
CARD_IN, CARD_OUT, CARD_RISE = 0.7, 0.4, 40


def load_card(name, scale):
    img = cv2.imread(__import__("os").path.join(CARDS_DIR, name), cv2.IMREAD_UNCHANGED)
    img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img[..., :3].astype(np.float32), img[..., 3:].astype(np.float32) / 255.0


def blend(frame, img, a, x, y):
    h, w = img.shape[:2]
    H_, W_ = frame.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W_), min(y + h, H_)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    si, sa = img[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
    frame[y0:y1, x0:x1] = (si * sa + roi * (1 - sa)).astype(np.uint8)


def draw_cards(frame, t, loaded):
    for (name, t_in, x, y, _s, t_out), (img, a) in zip(CARDS, loaded):
        if t < t_in or t > t_out:
            continue
        p = ease(min((t - t_in) / CARD_IN, 1.0))
        q = ease(min(max((t_out - t) / CARD_OUT, 0.0), 1.0))
        blend(frame, img, a * (p * q), x, y + int(round(CARD_RISE * (1 - p))))


def ease(u):
    return u * u * (3 - 2 * u)


def spot_at(t):
    cur = SPOTS[0]
    for i, s in enumerate(SPOTS):
        if t >= s[0]:
            cur, idx = s, i
    if idx > 0 and t < cur[0] + MOVE:
        prev = SPOTS[idx - 1]
        u = ease((t - cur[0]) / MOVE)
        return tuple(p + (c - p) * u for p, c in zip(prev[1:], cur[1:]))
    return cur[1:]


main = cv2.VideoCapture(MAIN)
fps = main.get(cv2.CAP_PROP_FPS)
W, H = int(main.get(3)), int(main.get(4))
av = cv2.VideoCapture(AV)
av_fps = av.get(cv2.CAP_PROP_FPS)
alpha_full = cv2.imread(ALPHA, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0

enc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
     "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", AUDIO,
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT],
    stdin=subprocess.PIPE)

cards = [load_card(c[0], c[4]) for c in CARDS]
n, av_idx, av_frame = 0, -1, None
while True:
    ok, frame = main.read()
    if not ok:
        break
    t = n / fps
    draw_cards(frame, t, cards)
    want = int(t * av_fps)
    while av_idx < want:
        ok2, f2 = av.read()
        if not ok2:
            break
        av_frame, av_idx = f2, av_idx + 1
    if av_frame is not None:
        x, y, size = spot_at(t)
        x, y, size = int(round(x)), int(round(y)), int(round(size))
        a_img = cv2.resize(av_frame, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
        a = cv2.resize(alpha_full, (size, size), interpolation=cv2.INTER_AREA)[..., None]
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + size, W), min(y + size, H)
        if x1 > x0 and y1 > y0:
            roi = frame[y0:y1, x0:x1].astype(np.float32)
            sub_img = a_img[y0 - y:y1 - y, x0 - x:x1 - x]
            sub_a = a[y0 - y:y1 - y, x0 - x:x1 - x]
            frame[y0:y1, x0:x1] = (sub_img * sub_a + roi * (1 - sub_a)).astype(np.uint8)
    enc.stdin.write(frame.tobytes())
    n += 1

enc.stdin.close()
enc.wait()
print("frames", n, "exit", enc.returncode)
