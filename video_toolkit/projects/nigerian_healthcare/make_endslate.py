"""10 s end slate: end card background, two leaders' photos animate in, names type out live.

Usage: python make_endslate.py <endcard_bg.png> <audio.wav> <out.mp4>
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG, AUDIO, OUT = sys.argv[1:4]
IMG = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "photos")
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
FPS, DUR = 25, 10.0
W, H = 1920, 1080
COL_W, PHOTO = 300, 290
CPS = 20            # typing speed, characters per second
WHITE, GREEN = (255, 255, 255), (150, 230, 170)

PEOPLE = [
    # photo, square crop, column x, name lines, title, photo-in time, typing start
    (f"{IMG}/tompolo.webp", (295, 60, 725, 490), 96,
     ["High Chief Government", "Oweizide Ekpemupolo", "(Tompolo)"], "Grand Patron", 0.8, 1.5),
    (f"{IMG}/asuku.jpg", (5, 0, 305, 300), 1524,
     ["Comrade Sunday", "Adekanbi Asuku"], "National Coordinator", 2.4, 3.1),
]
PHOTO_Y, PHOTO_IN, RISE = 110, 0.7, 40


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def photo_card(path, crop):
    """Square photo, white border, rounded corners, soft shadow -> RGBA with margin for the shadow."""
    p = Image.open(path).convert("RGB").crop(crop).resize((PHOTO - 12, PHOTO - 12), Image.LANCZOS)
    card = Image.new("RGBA", (PHOTO, PHOTO), (255, 255, 255, 255))
    card.paste(p, (6, 6))
    mask = Image.new("L", (PHOTO, PHOTO), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PHOTO - 1, PHOTO - 1), 22, fill=255)
    card.putalpha(mask)
    M = 24
    out = Image.new("RGBA", (PHOTO + 2 * M, PHOTO + 2 * M), (0, 0, 0, 0))
    shadow = Image.new("L", out.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle((M, M + 8, M + PHOTO, M + PHOTO + 8), 22, fill=140)
    out.putalpha(shadow.filter(ImageFilter.GaussianBlur(10)))
    out = Image.composite(Image.new("RGBA", out.size, (0, 0, 0, 255)), Image.new("RGBA", out.size, (0, 0, 0, 0)), out.getchannel("A"))
    out.alpha_composite(card, (M, M))
    return out, M


def fit_font(lines, weight, start):
    size = start
    while size > 16:
        f = ImageFont.truetype(AVENIR, size, index=weight)
        if max(f.getlength(l) for l in lines) <= COL_W:
            return f
        size -= 1
    return ImageFont.truetype(AVENIR, size, index=weight)


bg = Image.open(BG).convert("RGBA").resize((W, H))
people = []
for path, crop, x, names, title, t_in, t_type in PEOPLE:
    card, margin = photo_card(path, crop)
    name_font = fit_font(names, 2, 31)                       # Demi Bold
    title_font = fit_font([title], 7, 28)                    # Regular
    people.append((card, margin, x, names, title, t_in, t_type, name_font, title_font))

enc = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-i", AUDIO, "-map", "0:v", "-map", "1:a",
     "-c:v", "libx264", "-preset", "slow", "-b:v", "16M", "-maxrate", "25M", "-bufsize", "40M",
     "-profile:v", "high", "-level", "4.2", "-g", "25", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-t", str(DUR), OUT],
    stdin=subprocess.PIPE)

for n in range(int(DUR * FPS)):
    t = n / FPS
    frame = bg.copy()
    d = ImageDraw.Draw(frame)
    for card, margin, x, names, title, t_in, t_type, nf, tf in people:
        # photo: fade + rise + slight scale-up
        p = ease((t - t_in) / PHOTO_IN)
        if p > 0:
            s = 0.92 + 0.08 * p
            c = card.resize((round(card.width * s), round(card.height * s)), Image.LANCZOS)
            c.putalpha(c.getchannel("A").point(lambda a: int(a * p)))
            cx = x + COL_W // 2 - c.width // 2
            cy = PHOTO_Y - margin + int(RISE * (1 - p)) + (card.height - c.height) // 2
            frame.alpha_composite(c, (cx, cy))
        # typewriter: names, a short pause, then title
        typed = max(0, int((t - t_type) * CPS)) if t >= t_type else -1
        if typed < 0:
            continue
        y = PHOTO_Y + PHOTO + 26
        remaining = typed
        cursor_at = None
        lines = [(l, nf, WHITE, 40) for l in names] + [("", tf, GREEN, 8), (title, tf, GREEN, 34)]
        for text, font, colour, lh in lines:
            shown = text[:max(0, remaining)]
            remaining -= len(text) + (4 if text == "" else 0)   # empty line = brief pause
            if shown:
                d.text((x + COL_W / 2, y), shown, font=font, fill=colour, anchor="mt")
            if text and 0 <= len(shown) < len(text) and cursor_at is None and len(shown) > 0:
                cursor_at = (x + COL_W / 2 + font.getlength(shown) / 2 + 3, y, font.size, colour)
            y += lh
            if remaining < 0 and cursor_at is None and text:
                cursor_at = (x + COL_W / 2 + font.getlength(shown) / 2 + 3, y - lh, font.size, colour)
            if remaining < 0:
                break
        total = sum(len(l) for l in names) + 4 + len(title)
        done_at = t_type + total / CPS
        if cursor_at is None and t < done_at + 0.8:          # keep the cursor briefly at the end
            last_font = tf
            cursor_at = (x + COL_W / 2 + last_font.getlength(title) / 2 + 3, y - 34, tf.size, GREEN)
        if cursor_at and t < done_at + 0.8 and int(t * 4) % 2 == 0:
            cx, cy, size, colour = cursor_at
            d.rectangle((cx, cy + 2, cx + 3, cy + size + 2), fill=colour)
    enc.stdin.write(frame.convert("RGB").tobytes())

enc.stdin.close()
enc.wait()
print("frames", int(DUR * FPS), "exit", enc.returncode)
