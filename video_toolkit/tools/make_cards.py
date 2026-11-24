"""Build framed portrait cards (RGBA PNG) with a name caption and optional role line.

Usage: python make_cards.py <photo> <name> <crop x0,y0,x1,y1> <out.png> [role] [width] [photo_h]
"""
import sys

from PIL import Image, ImageDraw, ImageFont

PHOTO, NAME, CROP, OUT = sys.argv[1:5]
ROLE = sys.argv[5] if len(sys.argv) > 5 else ""
CW = int(sys.argv[6]) if len(sys.argv) > 6 else 236
PH = int(sys.argv[7]) if len(sys.argv) > 7 else 262
K = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0  # font/padding scale
BORDER, RAD = round(3 * K), round(16 * K)
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"


def fit(draw, text, path, start, max_w):
    size = start
    font = ImageFont.truetype(path, size)
    while draw.textlength(text, font=font) > max_w and size > 8:
        size -= 1
        font = ImageFont.truetype(path, size)
    return font


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


scratch = ImageDraw.Draw(Image.new("RGB", (1, 1)))
max_w = CW - round(20 * K)
name_font = fit(scratch, NAME, BOLD, round(19 * K), max_w) if not ROLE else ImageFont.truetype(BOLD, round(14 * K))
# "|" in NAME forces a line break, e.g. "High Chief ...|(Tompolo)"
name_lines = [l for part in NAME.split("|") for l in wrap(scratch, part, name_font, max_w)] if ROLE else [NAME]
role_font = ImageFont.truetype(REG, round(12 * K))
role_lines = wrap(scratch, ROLE, role_font, max_w) if ROLE else []
line_h, name_h = round(15 * K), round(17 * K)
CAP = round(44 * K) if not ROLE else round(10 * K) + name_h * len(name_lines) + round(4 * K) + line_h * len(role_lines) + round(8 * K)

x0, y0, x1, y1 = map(int, CROP.split(","))
photo = Image.open(PHOTO).convert("RGB").crop((x0, y0, x1, y1))
photo = photo.resize((CW - 2 * BORDER, PH - BORDER), Image.LANCZOS)

H = PH + CAP + BORDER
mask = Image.new("L", (CW, H), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, CW - 1, H - 1), RAD, fill=255)
body = Image.new("RGBA", (CW, H), (255, 255, 255, 255))
body.paste(photo, (BORDER, BORDER))
d = ImageDraw.Draw(body)
d.rectangle((BORDER, PH, CW - BORDER - 1, H - BORDER - 1), fill=(11, 74, 38, 255))
d.rectangle((BORDER, PH, CW - BORDER - 1, PH + round(3 * K)), fill=(46, 173, 92, 255))
if not ROLE:
    d.text((CW / 2, PH + round(4 * K) + (CAP - round(4 * K)) / 2), NAME, font=name_font, fill="white", anchor="mm")
else:
    y = PH + round(10 * K)
    for line in name_lines:
        d.text((CW / 2, y), line, font=name_font, fill="white", anchor="mt")
        y += name_h
    y += round(4 * K)
    for line in role_lines:
        d.text((CW / 2, y), line, font=role_font, fill=(150, 230, 170), anchor="mt")
        y += line_h

card = Image.new("RGBA", (CW, H), (0, 0, 0, 0))
card.paste(body, (0, 0), mask)
card.save(OUT)
print(OUT, card.size)
