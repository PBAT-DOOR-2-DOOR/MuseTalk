"""Draw the 1920x1080 slides for the education video in the style of the healthcare campaign.

Usage: python make_slides.py <out_dir>
Each slide is written as <name>_bg.png (background, logos, photo) and <name>_fg.png (RGBA text layer,
animated in by composite.py). Wording and figures are in SLIDES / TILES below.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if __name__ == "__main__" else "."
HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.join(HERE, *p)  # noqa: E731
W, H = 1920, 1080
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
BOLD, DEMI, MED, REG, HEAVY = 0, 2, 5, 7, 8
CREAM = (241, 237, 229)
INK = (24, 24, 24)
GREEN = (14, 92, 50)        # big numbers on cream slides
MINT = (98, 214, 140)       # highlight box / accents on dark slides
SOFTGREEN = (88, 178, 112)  # "Beyond the Ballot" line
RED = (191, 79, 78)

# Cream "story" slides: name line, big number, caption, small source line, photo
SLIDES = [
    ("ngozi", "For Ngozi in Enugu,", "₦375bn", "in interest-free student loans",
     "1.67 million loans disbursed by NELFUND", "photos/student.png"),
    ("aisha", "For little Aisha in Kano,", "1,000,000+", "out-of-school children back in class",
     "returned to learning nationwide", "photos/schoolgirl.png"),
    ("tunde", "For Tunde in Ibadan,", "156,446", "youths in free technical training",
     "with monthly stipends and start-up support", "photos/technician.png"),
]
TILES = [("01", "₦375bn", "student loans", "disbursed"),
         ("02", "1m+", "out-of-school children", "back in class"),
         ("03", "156,446", "youths in free", "technical training")]


def font(size, weight=BOLD):
    return ImageFont.truetype(AVENIR, size, index=weight)


def naira_text(d, xy, text, f, fill, anchor="la"):
    """Avenir has no ₦ glyph: draw an N and add the two bars."""
    x, y = xy
    if not text.startswith("₦"):
        d.text(xy, text, font=f, fill=fill, anchor=anchor)
        return d.textlength(text, font=f)
    d.text((x, y), "N" + text[1:], font=f, fill=fill, anchor=anchor)
    l, t, r, b = d.textbbox((x, y), "N", font=f, anchor=anchor)
    th = max(2, round((b - t) * 0.075))
    for fy in (0.40, 0.60):
        yy = t + (b - t) * fy
        d.rectangle([l - th * 0.5, yy - th / 2, r + th * 0.5, yy + th / 2], fill=fill)
    return d.textlength("N" + text[1:], font=f)


COUNTERS, LAYERS = [], []   # animated elements of the slide being drawn (see save_anim)


def counter(xy, text, size, weight, color):
    """A number that counts up to `text` in the video (drawn per frame by anim.py, not baked into _fg)."""
    COUNTERS.append({"x": xy[0], "y": xy[1], "text": text, "size": size, "weight": weight, "color": list(color)})


def text_layer(out, png, xy, text, f, fill, key, anim, size=(1920, 1080)):
    """Text on its own transparent layer, animated in at the time named `key` in the compositor."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill)
    img.save(os.path.join(out, png))
    LAYERS.append({"png": png, "key": key, "anim": anim})


def save_anim(out, name):
    with open(os.path.join(out, f"{name}_anim.json"), "w") as fh:
        json.dump({"counters": COUNTERS, "layers": LAYERS}, fh, indent=1)
    COUNTERS.clear()
    LAYERS.clear()


def paste_logo(img, path, x, y, feather=6):
    logo = Image.open(A(path)).convert("RGB")
    m = Image.new("L", logo.size, 0)
    ImageDraw.Draw(m).rectangle([feather, feather, logo.width - feather, logo.height - feather], fill=255)
    img.paste(logo, (x, y), m.filter(ImageFilter.GaussianBlur(feather / 2)))


def cream_slide(name, who, big, caption, small, photo):
    bg = Image.new("RGB", (W, H), CREAM)
    # photo on the right, its background shifted to the slide's cream and faded in from the left
    ph = Image.open(A(photo)).convert("RGB")
    ph = ph.resize((round(ph.width * 820 / ph.height), 820), Image.LANCZOS)
    arr = np.asarray(ph).astype(np.float32)
    corner = arr[10:120, 10:200].reshape(-1, 3).mean(0)
    arr = np.clip(arr + (np.array(CREAM) - corner), 0, 255).astype(np.uint8)
    ph = Image.fromarray(arr)
    ramp = np.clip((np.arange(ph.width) - 120) / 380.0, 0, 1)
    mask = Image.fromarray((np.tile(ramp, (ph.height, 1)) * 255).astype(np.uint8))
    bg.paste(ph, (W - ph.width, 938 - ph.height), mask)
    d = ImageDraw.Draw(bg)
    d.rectangle([90, 938, 1830, 940], fill=(222, 218, 212))   # footer rule
    d.rectangle([232, 82, 1630, 84], fill=RED)                 # header rule
    paste_logo(bg, "assets/apc_light.png", 80, 18)
    paste_logo(bg, "assets/pbat_light.png", 1640, 15)
    paste_logo(bg, "assets/vote_light.png", 80, 965)

    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.text((90, 330), who, font=font(62, BOLD), fill=INK)
    size = 200
    while d.textlength(big, font=font(size, HEAVY)) > 760:
        size -= 4
    counter((96, 400 + (200 - size) * 0.6), big, size, HEAVY, GREEN)
    d.text((92, 640), caption, font=font(52, BOLD), fill=INK)
    d.rectangle([92, 726, 160, 731], fill=GREEN)
    d.text((92, 748), small, font=font(34, MED), fill=(90, 90, 90))
    bg.save(os.path.join(OUT, f"{name}_bg.png"))
    fg.save(os.path.join(OUT, f"{name}_fg.png"))
    save_anim(OUT, name)


def dark_bg():
    """Dark green poster column with soft blurred sides, like the reference title/closing slides."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.array([6, 24, 14], np.float32)
    glow = np.exp(-(((xx - 960) / 700) ** 2 + ((yy - 40) / 520) ** 2))[..., None]
    col = (np.abs(xx - 960) < 430).astype(np.float32)[..., None]
    img = base + glow * np.array([4, 34, 16]) + col * np.array([0, 8, 3]) * (1 - yy[..., None] / H)
    img = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))
    # darker, blurred side wings
    side = np.ones((H, W, 1), np.float32)
    side[:, :530] = 0.72
    side[:, 1390:] = 0.72
    sm = Image.fromarray((side[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40))
    arr = np.asarray(img).astype(np.float32) * (np.asarray(sm)[..., None] / 255.0)
    return Image.fromarray(arr.astype(np.uint8))


def header_footer(img):
    d = ImageDraw.Draw(img)
    paste_logo(img, "assets/apc_dark.png", 566, 30, 4)
    paste_logo(img, "assets/pbat_dark.png", 1191, 30, 4)
    f = font(17, DEMI)
    label = "E D U C A T I O N   P O L I C I E S"
    tw = d.textlength(label, font=f)
    d.rounded_rectangle([960 - tw / 2 - 26, 70, 960 + tw / 2 + 26, 106], 18, outline=(170, 190, 175), width=2)
    d.text((960, 88), label, font=f, fill=(225, 235, 228), anchor="mm")
    d.rectangle([566, 948, 1354, 949], fill=(40, 70, 52))
    paste_logo(img, "assets/vote_dark.png", 560, 958, 4)


def tiles(d, y):
    x = 566
    for num, big, l1, l2 in TILES:
        d.rounded_rectangle([x, y, x + 252, y + 146], 14, fill=(14, 40, 24), outline=(52, 92, 66), width=2)
        d.text((x + 18, y + 16), num, font=font(16, DEMI), fill=(150, 175, 160))
        d.rectangle([x + 50, y + 25, x + 234, y + 26], fill=(70, 105, 82))
        counter((x + 18, y + 44), big, 46, BOLD, (255, 255, 255))
        d.text((x + 18, y + 100), l1, font=font(19, MED), fill=(205, 222, 210))
        d.text((x + 18, y + 122), l2, font=font(19, MED), fill=(205, 222, 210))
        x += 268


def title_slide():
    bg = dark_bg()
    header_footer(bg)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.rectangle([566, 196, 604, 198], fill=(200, 215, 205))
    d.text((620, 197), "B E Y O N D   T H E   H E A D L I N E S", font=font(18, DEMI), fill=(200, 215, 205), anchor="lm")
    d.text((562, 222), "NIGERIAN", font=font(104, HEAVY), fill=(255, 255, 255))
    fb = font(104, HEAVY)
    w = d.textlength("EDUCATION", font=fb)
    d.rounded_rectangle([556, 344, 556 + w + 34, 462], 12, fill=MINT)
    d.text((573, 336), "EDUCATION", font=fb, fill=(10, 50, 28))
    d.text((562, 456), "BY THE", font=fb, fill=(9, 38, 22), stroke_width=3, stroke_fill=(255, 255, 255))
    wb = d.textlength("BY THE ", font=fb)
    d.text((562 + wb, 456), "NUMBERS:", font=fb, fill=(255, 255, 255))
    # rising chart line
    pts = [(1080, 300), (1125, 270), (1165, 284), (1215, 230), (1262, 246), (1322, 160)]
    d.line(pts, fill=MINT, width=4, joint="curve")
    for p in pts[1:-1]:
        d.ellipse([p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7], outline=MINT, width=3)
    d.ellipse([1310, 148, 1334, 172], outline=MINT, width=4)
    d.text((566, 600), "What the figures mean for Nigerian", font=font(30, MED), fill=(235, 242, 237))
    d.text((566, 638), "families, every day.", font=font(30, MED), fill=(235, 242, 237))
    d.rectangle([566, 700, 986, 704], fill=(40, 120, 70))
    d.rectangle([706, 700, 846, 704], fill=(240, 250, 244))
    tiles(d, 730)
    cta, fc = "Choose a brighter future. Beyond the Ballot, PBAT Cares.", font(19, DEMI)
    d.rounded_rectangle([566, 890, 566 + d.textlength(cta, font=fc) + 48, 936], 10, fill=(255, 255, 255))
    d.text((590, 913), cta, font=fc, fill=(14, 92, 50), anchor="lm")
    bg.save(os.path.join(OUT, "title_bg.png"))
    fg.save(os.path.join(OUT, "title_fg.png"))
    save_anim(OUT, "title")


def choose_slide():
    bg = dark_bg()
    header_footer(bg)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    d.text((562, 200), "Choose a", font=font(92, HEAVY), fill=(255, 255, 255))
    d.text((562, 304), "brighter future.", font=font(92, HEAVY), fill=(255, 255, 255))
    text_layer(OUT, "choose_beyond1.png", (566, 450), "Beyond the Ballot,", font(58, HEAVY), SOFTGREEN, "beyond1", "slide")
    text_layer(OUT, "choose_beyond2.png", (566, 520), "PBAT Cares.", font(58, HEAVY), SOFTGREEN, "beyond2", "slide")
    tiles(d, 690)
    bg.save(os.path.join(OUT, "choose_bg.png"))
    fg.save(os.path.join(OUT, "choose_fg.png"))
    save_anim(OUT, "choose")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    title_slide()
    for s in SLIDES:
        cream_slide(*s)
    choose_slide()
    print("slides written to", OUT)
