"""Rebuild the end card so its two closing lines can be animated and moved.

Usage: python make_endcard.py <end_card_frame.png> <slides_dir> <slides_v_dir>
From one clean frame of the healthcare end card (1920x1080) it writes:
  slides/end_bg.png            background plate: logo + disclosure, original lines painted out
  slides/end_l1.png, end_l2.png  the two original lines as transparent layers, DOWN px lower
  slides_v/end_bg.png, end_l1.png, end_l2.png  the same for the 1080x1920 phone layout
  end_fg.png (empty) and end_anim.json in both, so the compositors treat it like any other slide
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

FRAME, SL, SLV = sys.argv[1:4]
DOWN = 40                                   # move both lines down this much (TV px)
LINES = [(438, 520, 500, 1420),             # original "This message is approved by the" (y0, y1, x0, x1)
         (520, 622, 370, 1555)]             # "PBAT Door to Door Movement" (with its glow)
# line 1 is re-set in Lexend (closest match to the original lettering); line 2 keeps the original pixels
LINE1_TEXT = "This message is brought to you by the"
LINE1_FONT, LINE1_WEIGHT, LINE1_SIZE = "assets/fonts/Lexend.ttf", 420, 53
LINE1_TOP, LINE1_CX, LINE1_RGB = 449, 957.5, (234, 248, 228)   # cap top and centre of the original line
# phone layout: crop of the TV card and where it goes (matches composite_vertical.py)
V_CROP, V_Y, VW, VH = (260, 120, 1400, 620), 230, 1080, 1920

src = cv2.imread(FRAME).astype(np.float32)
H, W = src.shape[:2]

# 1) plate: inpaint the text block at quarter size (the background is a smooth glow), blend in softly
mask = np.zeros((H, W), np.uint8)
for y0, y1, x0, x1 in LINES:
    mask[y0 - 6:y1 + 6, x0 - 10:x1 + 10] = 255
small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA).astype(np.uint8)
msmall = cv2.dilate(cv2.resize(mask, (W // 4, H // 4), interpolation=cv2.INTER_NEAREST), np.ones((5, 5), np.uint8))
filled = cv2.inpaint(small, msmall, 12, cv2.INPAINT_TELEA)
filled = cv2.GaussianBlur(cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32), (0, 0), 14)
soft = cv2.GaussianBlur(cv2.dilate(mask, np.ones((25, 25), np.uint8)).astype(np.float32) / 255, (0, 0), 10)[..., None]
plate = src * (1 - soft) + filled * soft
cv2.imwrite(os.path.join(SL, "end_bg.png"), plate.astype(np.uint8))

# 2) each line as RGBA: alpha from how far the pixel is from the plate, colour un-premultiplied
for i, (y0, y1, x0, x1) in enumerate(LINES, 1):
    strip, base = src[y0:y1, x0:x1], plate[y0:y1, x0:x1]
    diff = np.abs(strip - base).max(2)
    a = np.clip(diff / np.percentile(diff, 99.5), 0, 1)
    a[a < 0.04] = 0
    rgb = np.clip((strip - base * (1 - a[..., None])) / np.maximum(a[..., None], 0.05), 0, 255)
    layer = np.zeros((H, W, 4), np.float32)
    layer[y0 + DOWN:y1 + DOWN, x0:x1, :3] = rgb
    layer[y0 + DOWN:y1 + DOWN, x0:x1, 3] = a * 255
    cv2.imwrite(os.path.join(SL, f"end_l{i}.png"), layer.astype(np.uint8))

if LINE1_TEXT:
    from PIL import ImageDraw, ImageFilter, ImageFont
    fo = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), LINE1_FONT), LINE1_SIZE)
    fo.set_variation_by_axes([LINE1_WEIGHT])
    txt = Image.new("L", (W, H))
    d = ImageDraw.Draw(txt)
    b = d.textbbox((0, 0), LINE1_TEXT, font=fo)
    d.text((LINE1_CX - (b[2] - b[0]) / 2 - b[0], LINE1_TOP + DOWN - b[1]), LINE1_TEXT, font=fo, fill=255)
    a_txt = np.asarray(txt.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
    shadow = np.roll(np.asarray(txt.filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255, (2, 1), (0, 1)) * 0.45
    a = a_txt + shadow * (1 - a_txt)
    rgb = np.array(LINE1_RGB[::-1], np.float32) * (a_txt / np.maximum(a, 1e-3))[..., None]
    layer = np.dstack([rgb, a * 255])
    cv2.imwrite(os.path.join(SL, "end_l1.png"), np.clip(layer, 0, 255).astype(np.uint8))

# 3) phone versions: panel crop over a plain gradient sampled from the panel's own edges
x, y, w, h = V_CROP
ph = round(h * VW / w)
top = plate[y:y + 6, x:x + w].reshape(-1, 3).mean(0)
bot = plate[y + h - 6:y + h, x:x + w].reshape(-1, 3).mean(0)
v = np.clip((np.arange(VH, dtype=np.float32) - V_Y) / ph, 0, 1)[:, None]
col = (top * (1 - v) + bot * v) * (1 - 0.35 * np.clip((np.arange(VH)[:, None] - 1000) / 920, 0, 1))
hx = 1 - 0.25 * ((np.arange(VW) - VW / 2) / (VW / 2)) ** 2
vbg = col[:, None, :] * hx[None, :, None]
panel = cv2.resize(plate[y:y + h, x:x + w], (VW, ph), interpolation=cv2.INTER_AREA)
m = np.ones((ph, VW, 1), np.float32)
r = 110
ramp = np.linspace(0, 1, r)[:, None, None]
m[:r] *= ramp
m[-r:] *= ramp[::-1]
vbg[V_Y:V_Y + ph] = panel * m + vbg[V_Y:V_Y + ph] * (1 - m)
cv2.imwrite(os.path.join(SLV, "end_bg.png"), np.clip(vbg, 0, 255).astype(np.uint8))
for i in (1, 2):
    layer = cv2.imread(os.path.join(SL, f"end_l{i}.png"), cv2.IMREAD_UNCHANGED)
    vl = np.zeros((VH, VW, 4), np.uint8)
    vl[V_Y:V_Y + ph] = cv2.resize(layer[y:y + h, x:x + w], (VW, ph), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(SLV, f"end_l{i}.png"), vl)
for d, size in ((SL, (W, H)), (SLV, (VW, VH))):
    Image.new("RGBA", size, (0, 0, 0, 0)).save(os.path.join(d, "end_fg.png"))
    with open(os.path.join(d, "end_anim.json"), "w") as fh:
        json.dump({"counters": [], "layers": [{"png": "end_l1.png", "key": "approved1", "anim": "rise"},
                                              {"png": "end_l2.png", "key": "approved2", "anim": "rise"}]}, fh)
print("end card plate and line layers written")
