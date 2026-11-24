"""Vertical 9:16 (1080x1920) phone version.

Slide on top over a blurred fill, photo cards in the middle band, talking presenter below.
Usage: python composite_vertical.py <main.mp4> <avatar_talking.mp4> <alpha.png> <audio> <out.mp4>
"""
import os
import subprocess
import sys

import cv2
import numpy as np

MAIN, AV, ALPHA, AUDIO, OUT = sys.argv[1:6]
CARDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards_v")
W, H = 1080, 1920
# Slide layouts: (from time s, [panels]); each panel = (source crop x,y,w,h, dest x,y,width).
# Wide photo slides are split: text half on top, photo half below. Layout changes crossfade.
def split(text_w, photo_x, width=790, x=50, top=30, gap=15):
    """Text half (0..text_w) on top, photo half (photo_x..1024, header to above footer) below."""
    text_h = round(576 * width / text_w)
    return [((0, 0, text_w, 576), (x, top, width)),
            ((photo_x, 0, 1024 - photo_x, 500), (x, top + text_h + gap, width))]


LAYOUTS = [
    (0.0, [((272, 0, 480, 576), (0, 200, 1080))]),                    # title: centre column
    (6.9, split(500, 495)),                                            # Bala
    (16.1, split(468, 462)),                                           # Ejiro
    (24.4, split(500, 500)),                                           # Charity
    (33.1, [((270, 0, 484, 576), (110, 40, 860))]),                    # Choose: centre column
    (41.4, [((100, 60, 824, 490), (0, 230, 1080))]),                   # end card
]
FADE = 0.6

# Presenter: fixed small inset, bottom-right corner
INSET = (810, 1660, 260)

# (png, appear s, x, y, gone s)
CARDS = [
    ("tinubu.png", 33.8, 100, 1110, 41.3),
    ("shettima.png", 35.0, 560, 1110, 41.3),
    ("tompolo.png", 42.0, 70, 1000, 99),
    ("asuku.png", 43.0, 590, 1000, 99),
]
CARD_IN, CARD_OUT, CARD_RISE = 0.7, 0.4, 60


def ease(u):
    return u * u * (3 - 2 * u)


def layout_weights(t):
    """[(layout index, weight)] — two entries while crossfading."""
    idx = 0
    for i, l in enumerate(LAYOUTS):
        if t >= l[0]:
            idx = i
    if idx > 0 and t < LAYOUTS[idx][0] + FADE:
        u = ease((t - LAYOUTS[idx][0]) / FADE)
        return [(idx - 1, 1 - u), (idx, u)]
    return [(idx, 1.0)]


def draw_layout(frame, src, panels, weight):
    for (cx, cy, cw, ch), (dx, dy, dw) in panels:
        dh = int(round(dw * ch / cw))
        view = cv2.resize(src[cy:cy + ch, cx:cx + cw], (dw, dh), interpolation=cv2.INTER_CUBIC)
        blend(frame, view.astype(np.float32), np.full((dh, dw, 1), weight, np.float32), dx, dy)


def blend(frame, img, a, x, y):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    si, sa = img[y0 - y:y1 - y, x0 - x:x1 - x], a[y0 - y:y1 - y, x0 - x:x1 - x]
    frame[y0:y1, x0:x1] = (si * sa + roi * (1 - sa)).astype(np.uint8)


def load_card(name):
    img = cv2.imread(os.path.join(CARDS_DIR, name), cv2.IMREAD_UNCHANGED)
    return img[..., :3].astype(np.float32), img[..., 3:].astype(np.float32) / 255.0


main = cv2.VideoCapture(MAIN)
fps = main.get(cv2.CAP_PROP_FPS)
sw, sh = int(main.get(3)), int(main.get(4))
av = cv2.VideoCapture(AV)
av_fps = av.get(cv2.CAP_PROP_FPS)
alpha_full = cv2.imread(ALPHA, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
cards = [load_card(c[0]) for c in CARDS]
# central strip of the slide with the same 9:16 aspect, used for the blurred fill
strip_w = int(sh * W / H)
strip_x = (sw - strip_w) // 2

enc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
     "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", AUDIO,
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
     "-shortest", OUT],
    stdin=subprocess.PIPE)

n, av_idx, av_frame = 0, -1, None
while True:
    ok, src = main.read()
    if not ok:
        break
    t = n / fps
    # blurred, darkened background fill
    bg = cv2.resize(src[:, strip_x:strip_x + strip_w], (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(bg, (0, 0), 6)
    frame = (cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR) * 0.45).astype(np.uint8)
    # slide panels (crossfading between layouts at slide changes)
    weights = layout_weights(t)
    if len(weights) == 1:
        draw_layout(frame, src, LAYOUTS[weights[0][0]][1], 1.0)
    elif len(LAYOUTS[weights[0][0]][1]) == len(LAYOUTS[weights[1][0]][1]):
        # same panel structure: morph crop and placement instead of crossfading (no ghosting)
        u = weights[1][1]
        morphed = []
        for (ca, da), (cb, db) in zip(LAYOUTS[weights[0][0]][1], LAYOUTS[weights[1][0]][1]):
            morphed.append((tuple(int(round(a + (b - a) * u)) for a, b in zip(ca, cb)),
                            tuple(int(round(a + (b - a) * u)) for a, b in zip(da, db))))
        draw_layout(frame, src, morphed, 1.0)
    else:
        a_canvas, b_canvas = frame.copy(), frame.copy()
        draw_layout(a_canvas, src, LAYOUTS[weights[0][0]][1], 1.0)
        draw_layout(b_canvas, src, LAYOUTS[weights[1][0]][1], 1.0)
        u = weights[1][1]
        frame = (a_canvas * (1 - u) + b_canvas * u).astype(np.uint8)
    # cards
    for (name, t_in, x, y, t_out), (img, a) in zip(CARDS, cards):
        if t_in <= t <= t_out:
            p = ease(min((t - t_in) / CARD_IN, 1.0))
            q = ease(min(max((t_out - t) / CARD_OUT, 0.0), 1.0))
            blend(frame, img, a * (p * q), x, y + int(round(CARD_RISE * (1 - p))))
    # presenter
    want = int(t * av_fps)
    while av_idx < want:
        ok2, f2 = av.read()
        if not ok2:
            break
        av_frame, av_idx = f2, av_idx + 1
    if av_frame is not None:
        x, y, size = INSET
        a_img = cv2.resize(av_frame, (size, size), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        a = cv2.resize(alpha_full, (size, size), interpolation=cv2.INTER_LINEAR)[..., None]
        blend(frame, a_img, a, x, y)
    enc.stdin.write(frame.tobytes())
    n += 1

enc.stdin.close()
enc.wait()
print("frames", n, "exit", enc.returncode)
