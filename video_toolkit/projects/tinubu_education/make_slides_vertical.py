"""Draw the 1080x1920 (iPhone, 9:16) slides. Same wording and figures as make_slides.py.

Usage: python make_slides_vertical.py <out_dir>
Writes <name>_bg.png / <name>_fg.png pairs like the widescreen version.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
import make_slides as ms
from make_slides import A, BOLD, CREAM, DEMI, GREEN, HEAVY, INK, MED, MINT, RED, REG, SOFTGREEN, font, naira_text

OUT = sys.argv[1]
W, H = 1080, 1920
PHOTO_X0 = {"ngozi": 520, "aisha": 470, "tunde": 520}  # left edge of the photo crop (1280x720 source)


def paste_logo(img, path, x, y, feather=6):
    ms.paste_logo(img, path, x, y, feather)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def cream_slide(name, who, big, caption, small, photo):
    bg = Image.new("RGB", (W, H), CREAM)
    ph = Image.open(A(photo)).convert("RGB")
    x0 = PHOTO_X0[name]
    ph = ph.crop((x0, 0, ph.width, ph.height))
    ph = ph.resize((W, round(ph.height * W / ph.width)), Image.LANCZOS)
    arr = np.asarray(ph).astype(np.float32)
    corner = arr[10:80, 10:120].reshape(-1, 3).mean(0)
    ph = Image.fromarray(np.clip(arr + (np.array(CREAM) - corner), 0, 255).astype(np.uint8))
    ramp = np.clip(np.arange(ph.height) / 140.0, 0, 1)[:, None]
    hramp = np.clip(np.arange(ph.width) / 160.0, 0, 1)[None, :]
    mask = Image.fromarray((ramp * hramp * 255).astype(np.uint8))
    bg.paste(ph, (0, 1712 - ph.height), mask)
    d = ImageDraw.Draw(bg)
    d.rectangle([40, 1712, 1040, 1714], fill=(222, 218, 212))
    d.rectangle([200, 114, 822, 116], fill=RED)
    paste_logo(bg, "assets/apc_light.png", 40, 48)
    paste_logo(bg, "assets/pbat_light.png", 835, 46)
    paste_logo(bg, "assets/vote_light.png", 30, 1745)

    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.text((60, 215), who, font=font(64, BOLD), fill=INK)
    size = 220
    while d.textlength(big, font=font(size, HEAVY)) > 950:
        size -= 4
    ms.counter((58, 285 + (220 - size) * 0.5), big, size, HEAVY, GREEN)
    y = 535
    for line in wrap(d, caption, font(52, BOLD), 960):
        d.text((62, y), line, font=font(52, BOLD), fill=INK)
        y += 64
    d.rectangle([62, y + 14, 140, y + 20], fill=GREEN)
    d.text((62, y + 34), small, font=font(36, MED), fill=(90, 90, 90))
    bg.save(os.path.join(OUT, f"{name}_bg.png"))
    fg.save(os.path.join(OUT, f"{name}_fg.png"))
    ms.save_anim(OUT, name)


def dark_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array([6, 24, 14], np.float32)
    glow = np.exp(-(((xx - 540) / 650) ** 2 + ((yy - 60) / 760) ** 2))[..., None]
    vign = 1 - 0.35 * (np.abs(xx - 540) / 540) ** 2
    img = (base + glow * np.array([5, 40, 19])) * vign[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))


def header_footer(img):
    d = ImageDraw.Draw(img)
    paste_logo(img, "assets/apc_dark.png", 50, 56, 4)
    paste_logo(img, "assets/pbat_dark.png", 1080 - 50 - 165, 56, 4)
    f = font(20, DEMI)
    label = "E D U C A T I O N   P O L I C I E S"
    tw = d.textlength(label, font=f)
    d.rounded_rectangle([540 - tw / 2 - 26, 96, 540 + tw / 2 + 26, 138], 21, outline=(170, 190, 175), width=2)
    d.text((540, 117), label, font=f, fill=(225, 235, 228), anchor="mm")
    d.rectangle([50, 1792, 1030, 1793], fill=(40, 70, 52))
    paste_logo(img, "assets/vote_dark.png", 40, 1806, 4)


def tiles(d, y, h=200):
    x = 50
    for num, big, l1, l2 in ms.TILES:
        d.rounded_rectangle([x, y, x + 314, y + h], 16, fill=(14, 40, 24), outline=(52, 92, 66), width=2)
        d.text((x + 22, y + 18), num, font=font(20, DEMI), fill=(150, 175, 160))
        d.rectangle([x + 62, y + 30, x + 292, y + 31], fill=(70, 105, 82))
        ms.counter((x + 22, y + 52), big, 58, BOLD, (255, 255, 255))
        d.text((x + 22, y + h - 76), l1, font=font(25, MED), fill=(205, 222, 210))
        d.text((x + 22, y + h - 44), l2, font=font(25, MED), fill=(205, 222, 210))
        x += 333


def title_slide():
    bg = dark_bg()
    header_footer(bg)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.rectangle([60, 262, 106, 265], fill=(200, 215, 205))
    d.text((124, 264), "B E Y O N D   T H E   H E A D L I N E S", font=font(24, DEMI), fill=(200, 215, 205), anchor="lm")
    fb = font(150, HEAVY)
    d.text((54, 290), "NIGERIAN", font=fb, fill=(255, 255, 255))
    w = d.textlength("EDUCATION", font=fb)
    d.rounded_rectangle([46, 470, 46 + w + 40, 636], 14, fill=MINT)
    d.text((66, 459), "EDUCATION", font=fb, fill=(10, 50, 28))
    d.text((54, 640), "BY THE", font=fb, fill=(9, 38, 22), stroke_width=4, stroke_fill=(255, 255, 255))
    d.text((54, 810), "NUMBERS:", font=fb, fill=(255, 255, 255))
    pts = [(660, 800), (725, 765), (785, 782), (850, 720), (915, 738), (1010, 668)]
    d.line(pts, fill=MINT, width=5, joint="curve")
    for p in pts[1:-1]:
        d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], outline=MINT, width=4)
    d.ellipse([994, 652, 1026, 684], outline=MINT, width=5)
    d.text((60, 1010), "What the figures mean for Nigerian", font=font(40, MED), fill=(235, 242, 237))
    d.text((60, 1062), "families, every day.", font=font(40, MED), fill=(235, 242, 237))
    d.rectangle([60, 1138, 600, 1143], fill=(40, 120, 70))
    d.rectangle([240, 1138, 420, 1143], fill=(240, 250, 244))
    tiles(d, 1180)
    cta, fc = "Choose a brighter future. Beyond the Ballot, PBAT Cares.", font(26, DEMI)
    d.rounded_rectangle([50, 1410, 50 + d.textlength(cta, font=fc) + 56, 1468], 12, fill=(255, 255, 255))
    d.text((78, 1439), cta, font=fc, fill=(14, 92, 50), anchor="lm")
    bg.save(os.path.join(OUT, "title_bg.png"))
    fg.save(os.path.join(OUT, "title_fg.png"))
    ms.save_anim(OUT, "title")


def choose_slide():
    bg = dark_bg()
    header_footer(bg)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.text((56, 210), "Choose a", font=font(118, HEAVY), fill=(255, 255, 255))
    d.text((56, 345), "brighter future.", font=font(118, HEAVY), fill=(255, 255, 255))
    ms.text_layer(OUT, "choose_beyond1.png", (60, 520), "Beyond the Ballot,", font(74, HEAVY), SOFTGREEN, "beyond1", "slide", (W, H))
    ms.text_layer(OUT, "choose_beyond2.png", (60, 610), "PBAT Cares.", font(74, HEAVY), SOFTGREEN, "beyond2", "slide", (W, H))
    tiles(d, 1290)
    bg.save(os.path.join(OUT, "choose_bg.png"))
    fg.save(os.path.join(OUT, "choose_fg.png"))
    ms.save_anim(OUT, "choose")


def disclosure():
    """End-card AI disclosure, re-set for the phone width (the TV line is too wide to crop)."""
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    f = font(27, REG)
    text = ("AI disclosure: This video contains AI-generated content, including the voiceover, music and "
            "imagery. Some people shown are illustrative; named individuals are real.")
    y = 1782
    for line in wrap(d, text, f, 940):
        d.text((540, y), line, font=f, fill=(198, 236, 214), anchor="ma")
        y += 36
    fg.save(os.path.join(OUT, "disclosure_fg.png"))


os.makedirs(OUT, exist_ok=True)
disclosure()
title_slide()
for s in ms.SLIDES:
    cream_slide(*s)
choose_slide()
print("vertical slides written to", OUT)
