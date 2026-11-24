"""Animated slide elements shared by composite.py and composite_vertical.py.

- Counters: numbers written by make_slides*.py to <slide>_anim.json, drawn per frame counting up fast
  from 0 to their final text (keeps prefix/suffix, commas, e.g. ₦375bn, 1,000,000+, 156,446, 1m+).
- Layers: text PNGs that animate in at a named time ("slide" from the left, or "rise" with a slight pop).
"""
import json
import os
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw

import make_slides as ms

COUNT_DUR = 1.1        # seconds to reach the final value
LAYER_IN = 0.55
_fonts, _boxes = {}, {}


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def load(slide_dir, name):
    path = os.path.join(slide_dir, f"{name}_anim.json")
    if not os.path.exists(path):
        return {"counters": [], "layers": []}
    spec = json.load(open(path))
    for lay in spec["layers"]:
        img = cv2.imread(os.path.join(slide_dir, lay["png"]), cv2.IMREAD_UNCHANGED)
        ys, xs = np.where(img[..., 3] > 0)
        y0, y1, x0, x1 = max(ys.min() - 20, 0), ys.max() + 20, max(xs.min() - 20, 0), xs.max() + 20
        lay["img"] = img[y0:y1, x0:x1, :3].astype(np.float32)
        lay["a"] = img[y0:y1, x0:x1, 3:].astype(np.float32) / 255.0
        lay["xy"] = (x0, y0)
    return spec


def count_text(final, p):
    m = re.match(r"^(\D*?)([\d,]*\.?\d+)(.*)$", final)
    if not m or p >= 1:
        return final
    pre, num, suf = m.groups()
    target = float(num.replace(",", ""))
    v = target * ease_out(p)
    if "," in num:
        body = f"{int(round(v)):,}"
    elif target < 10:
        if round(v, 1) >= target:
            return final
        body = f"{v:.1f}"
    else:
        body = f"{int(round(v))}"
    return pre + body + suf


def _font(size, weight):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ms.font(size, weight)
    return _fonts[key]


def draw_counter(frame, c, p_count, alpha, dy, blend):
    """Render one counter at count progress p_count with opacity alpha, shifted down by dy."""
    if alpha <= 0:
        return
    text = count_text(c["text"], p_count)
    f = _font(c["size"], c["weight"])
    key = (c["text"], c["size"], c["weight"])
    if key not in _boxes:  # canvas sized for the final (widest) text
        d = ImageDraw.Draw(Image.new("L", (1, 1)))
        w = int(d.textlength("N" + c["text"][1:] if c["text"].startswith("₦") else c["text"], font=f))
        _boxes[key] = (int(w * 1.15) + 2 * c["size"], int(c["size"] * 1.6))
    cw, ch = _boxes[key]
    img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    pad = c["size"] // 2
    ms.naira_text(ImageDraw.Draw(img), (pad, 0), text, f, tuple(c["color"]))
    arr = np.asarray(img).astype(np.float32)
    blend(frame, arr[..., 2::-1], arr[..., 3:] / 255.0 * alpha, int(round(c["x"] - pad)), int(round(c["y"] + dy)))


def draw_layer(frame, lay, t, t_in, blend):
    if t < t_in:
        return
    p = ease((t - t_in) / LAYER_IN)
    x, y = lay["xy"]
    if lay["anim"] == "slide":
        blend(frame, lay["img"], lay["a"] * p, x - int(round(70 * (1 - p))), y)
    else:  # "rise": up from below with a slight scale pop
        s = 0.92 + 0.08 * ease_out((t - t_in) / LAYER_IN)
        img, a = lay["img"], lay["a"]
        if s < 0.999:
            h, w = img.shape[:2]
            nw, nh = int(w * s), int(h * s)
            img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
            a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA)[..., None]
            x, y = x + (w - nw) // 2, y + (h - nh) // 2
        blend(frame, img, a * p, x, y + int(round(28 * (1 - p))))
