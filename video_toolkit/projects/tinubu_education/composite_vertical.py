"""iPhone 9:16 (1080x1920, 25 fps) version: native vertical slides, presenter, cards, end card.

Usage: python composite_vertical.py <slides_v_dir> <presenter_talking.mp4> <alpha.png> <audio> <out.mp4>
Same timeline and animations as composite.py (composite_timeline.py and anim.py).
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
W, H, FPS, DUR = 1080, 1920, 25, 45.5
TEXT_IN, TEXT_DELAY, TEXT_RISE, ZOOM = 0.6, 0.15, 36, 0.025
DISCLOSURE_IN = 40.0   # phone-width AI disclosure fades in here (slides_v/disclosure_fg.png)

SPOTS = [
    (0.0, 390, 1488, 300),    # title: under the CTA
    (7.2, 790, 1630, 270),    # story slides: bottom-right corner
    (34.85, 400, 1505, 285),  # Choose: under the tiles, centred
    (39.1, 395, 1440, 300),   # end card: under the Tompolo / Asuku cards, above the disclosure
]
MOVE = 0.8

CARDS = [
    ("tinubu.png", 35.2, 100, 770, 39.1),
    ("shettima.png", 36.0, 560, 770, 39.1),
    ("tompolo.png", 40.3, 70, 860, 99),
    ("asuku.png", 42.3, 590, 860, 99),
]
CARD_IN, CARD_OUT, CARD_RISE = 0.7, 0.4, 60
ease = anim.ease


def blend(frame, img, a, x, y):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    si, sa = img[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
    frame[y0:y1, x0:x1] = (si * sa + roi * (1 - sa)).astype(np.uint8)


def load_rgba(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    return img[..., :3].astype(np.float32), img[..., 3:].astype(np.float32) / 255.0


slides = {}
for name, _ in SEGS:
    bg = cv2.imread(os.path.join(SLIDES, f"{name}_bg.png"))
    fg, fa = load_rgba(os.path.join(SLIDES, f"{name}_fg.png"))
    slides[name] = (bg, fg, fa, anim.load(SLIDES, name))
disc, disc_a = load_rgba(os.path.join(SLIDES, "disclosure_fg.png"))
cards = [load_rgba(os.path.join(HERE, "cards_v", c[0])) for c in CARDS]
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
    if name == "end" and t >= DISCLOSURE_IN:
        blend(frame, disc, disc_a * ease((t - DISCLOSURE_IN) / 0.6), 0, 0)
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
     "-i", "-", "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
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
    for (name, t_in, x, y, t_out), (img, a) in zip(CARDS, cards):
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
