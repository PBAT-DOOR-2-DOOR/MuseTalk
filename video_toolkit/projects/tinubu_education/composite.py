"""TV 1920x1080 25 fps: animated slides + gliding lipsynced presenter + photo cards + end card.

Usage: python composite.py <slides_dir> <presenter_talking.mp4> <alpha.png> <audio.wav> <out.mp4>
Slide and text timings are in composite_timeline.py; presenter SPOTS and CARDS below.
Numbers count up and text layers animate in via anim.py (specs in slides/<name>_anim.json).
"""
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
import anim  # noqa: E402
from composite_timeline import DIP, SEGS, TIMES, XF  # noqa: E402

SLIDES, AV, ALPHA, AUDIO, OUT = sys.argv[1:6]
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, DUR = 1920, 1080, 25, 45.5

TEXT_IN, TEXT_DELAY, TEXT_RISE = 0.6, 0.15, 30
ZOOM = 0.025        # slow push-in over each slide

SPOTS = [           # (from s, x, y, size) presenter position, glides between them
    (0.0, 70, 330, 430),     # title: empty dark left side
    (7.2, 950, 95, 310),     # Ngozi: top middle, left of the student
    (17.55, 880, 100, 260),  # Aisha: top middle, above the desk, left of the hijabs
    (25.35, 1000, 100, 290), # Tunde: top middle, left of the technician
    (34.85, 1429, 640, 384), # Choose: under Shettima's card
    (39.1, 101, 540, 337),   # end card: under Tompolo's card
]
MOVE = 0.8

CARDS = [           # (png, in s, x, y, scale, out s)
    ("tinubu.png", 35.2, 101, 146, 0.85, 39.1),
    ("shettima.png", 36.0, 1444, 146, 0.85, 39.1),
    ("tompolo.png", 40.3, 101, 56, 1.0, 99),
    ("asuku.png", 42.3, 1481, 56, 1.0, 99),
]
CARD_IN, CARD_OUT, CARD_RISE = 0.7, 0.4, 75
ease = anim.ease


def blend(frame, img, a, x, y):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    si, sa = img[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
    frame[y0:y1, x0:x1] = (si * sa + roi * (1 - sa)).astype(np.uint8)


def load_rgba(path, scale=1.0):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img[..., :3].astype(np.float32), img[..., 3:].astype(np.float32) / 255.0


slides = {}
for name, _ in SEGS:
    bg = cv2.imread(os.path.join(SLIDES, f"{name}_bg.png"))
    fg, fa = load_rgba(os.path.join(SLIDES, f"{name}_fg.png"))
    slides[name] = (bg, fg, fa, anim.load(SLIDES, name))
cards = [load_rgba(os.path.join(HERE, "cards", c[0]), c[4]) for c in CARDS]
av = cv2.VideoCapture(AV)
alpha_full = cv2.imread(ALPHA, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0


def render_slide(i, t):
    name, t0 = SEGS[i]
    bg, fg, fa, spec = slides[name]
    t1 = SEGS[i + 1][1] + XF if i + 1 < len(SEGS) else DUR
    s = 1 + ZOOM * ease((t - t0) / (t1 - t0))
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
    frame = cv2.warpAffine(bg, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    p = ease((t - t0 - TEXT_DELAY) / TEXT_IN)
    dy = int(round(TEXT_RISE * (1 - p)))
    if p > 0:
        blend(frame, fg, fa * p, 0, dy)
    for c in spec["counters"]:
        anim.draw_counter(frame, c, (t - t0 - TEXT_DELAY) / anim.COUNT_DUR, p, dy, blend)
    for lay in spec["layers"]:
        anim.draw_layer(frame, lay, t, TIMES[lay["key"]], blend)
    return frame


def spot_at(t):
    idx = max(i for i, s in enumerate(SPOTS) if t >= s[0])
    cur = SPOTS[idx]
    if idx > 0 and t < cur[0] + MOVE:
        u = ease((t - cur[0]) / MOVE)
        return tuple(p + (c - p) * u for p, c in zip(SPOTS[idx - 1][1:], cur[1:]))
    return cur[1:]


enc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
     "-i", "-", "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
     "-shortest", OUT], stdin=subprocess.PIPE)

av_idx, av_frame = -1, None
for n in range(int(DUR * FPS)):
    t = n / FPS
    i = max(k for k, s in enumerate(SEGS) if t >= s[1])
    t_start = SEGS[i][1]
    if i > 0 and SEGS[i][0] in DIP and t < t_start + 2 * XF:  # previous slide -> black -> this slide
        u = (t - t_start) / XF
        frame = (render_slide(i - 1, t) * (1 - ease(u))).astype(np.uint8) if u < 1 else \
            (render_slide(i, t) * ease(u - 1)).astype(np.uint8)
    else:
        frame = render_slide(i, t)
        if i > 0 and t < t_start + XF:
            u = ease((t - t_start) / XF)
            frame = cv2.addWeighted(render_slide(i - 1, t), 1 - u, frame, u, 0)
    for (name, t_in, x, y, _s, t_out), (img, a) in zip(CARDS, cards):
        if t_in <= t <= t_out:
            p, q = ease((t - t_in) / CARD_IN), ease((t_out - t) / CARD_OUT)
            blend(frame, img, a * (p * q), x, y + int(round(CARD_RISE * (1 - p))))
    while av_idx < int(t * FPS):
        ok, f2 = av.read()
        if not ok:
            break
        av_frame, av_idx = f2, av_idx + 1
    if av_frame is not None:
        x, y, size = (int(round(v)) for v in spot_at(t))
        a_img = cv2.resize(av_frame, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
        a = cv2.resize(alpha_full, (size, size), interpolation=cv2.INTER_AREA)[..., None]
        blend(frame, a_img, a, x, y)
    enc.stdin.write(frame.tobytes())

enc.stdin.close()
enc.wait()
print("frames", n + 1, "exit", enc.returncode)
