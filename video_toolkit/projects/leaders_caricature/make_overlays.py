"""Transparent 1280x720 overlays: title, per-speaker name tag + caption, parody badge, end card."""
from PIL import Image, ImageDraw, ImageFont
import os
W, H = 1280, 720
D = os.path.join(os.path.dirname(__file__), "overlays")
FONT = os.path.join(os.path.dirname(__file__), "../tinubu_education/assets/fonts/Lexend.ttf")
GREEN = (0, 135, 81, 235)
def font(sz, wt=700):
    f = ImageFont.truetype(FONT, sz)
    try: f.set_variation_by_axes([wt])
    except Exception: pass
    return f
def centered(d, y, text, f, fill=(255,255,255,255)):
    w = d.textlength(text, font=f); d.text(((W-w)/2, y), text, font=f, fill=fill, stroke_width=3, stroke_fill=(0,0,0,200))
def badge(d):
    f = font(20, 600); t = "PARODY · SYNTHETIC VOICES"; w = d.textlength(t, font=f)
    d.rounded_rectangle((W-w-44, 20, W-20, 58), 10, fill=(0,0,0,150)); d.text((W-w-32, 27), t, font=f, fill=(255,255,255,235))
im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
d.rounded_rectangle((300, 70, 980, 210), 22, fill=GREEN)
centered(d, 88, "CARTOON ROLL CALL", font(56, 800)); centered(d, 158, "Nigerian leaders, caricatured", font(28, 500))
badge(d); im.save(f"{D}/title.png")
lines = {
 "tinubu": ("Bola Tinubu", "“Good evening, Nigeria! I am the cartoon Tinubu. Emi lokan!”"),
 "obi": ("Peter Obi", "“Good evening. I am cartoon Peter Obi, and yes, I brought my receipts.”"),
 "atiku": ("Atiku Abubakar", "“Hello everyone! Cartoon Atiku here. And yes, I am still running.”"),
 "obasanjo": ("Olusegun Obasanjo", "“Ah, my children! Cartoon Obasanjo has seen it all. Behave yourselves!”"),
}
for k, (name, cap) in lines.items():
    im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
    f = font(34, 700); w = d.textlength(name, font=f)
    d.rounded_rectangle((40, 520, 40+w+48, 576), 12, fill=GREEN); d.text((64, 527), name, font=f, fill="white")
    fc = font(30, 500); w = d.textlength(cap, font=fc)
    if w > W-80: fc = font(int(30*(W-80)/w), 500); w = d.textlength(cap, font=fc)
    d.rounded_rectangle(((W-w)/2-20, 600, (W+w)/2+20, 660), 12, fill=(0,0,0,160))
    d.text(((W-w)/2, 612), cap, font=fc, fill="white")
    badge(d); im.save(f"{D}/{k}.png")
im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
d.rounded_rectangle((200, 230, 1080, 450), 22, fill=(0,0,0,175))
centered(d, 260, "That's all, folks!", font(56, 800))
centered(d, 345, "Parody caricatures made in Blender.", font(28, 500))
centered(d, 388, "Voices are synthetic. These are not real statements.", font(28, 500))
im.save(f"{D}/end.png")
print("ok")
