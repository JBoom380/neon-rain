"""Composite Vela cut-outs onto generated backgrounds with a heavy noir grade. Writes art/covers_noir/*.jpg and a sheet."""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance

ART = r"C:\Users\John\Documents\GitHub\projects\neon-rain-fps\art"
BG = r"C:\Users\John\Documents\ComfyUI_Output\neonrain_bg"
OUT = os.path.join(ART, "covers_noir"); os.makedirs(OUT, exist_ok=True)
W, H = 1344, 768


def grade(im, warm=True, blinds=True, key=(0.66, 0.33)):
    a = np.asarray(im).astype(np.float32) / 255
    lum = a @ np.array([.299, .587, .114])
    # desaturate everything except reds and ambers
    hsv = np.asarray(im.convert("HSV")).astype(np.float32)
    h = hsv[..., 0] / 255 * 360
    keep = ((h < 25) | (h > 340)) & (hsv[..., 1] > 90)
    amber = (h >= 25) & (h < 50) & (hsv[..., 1] > 60)
    sat = np.where(keep, 1.0, np.where(amber, 0.55, 0.15))[..., None]
    a = lum[..., None] + (a - lum[..., None]) * sat
    # crush: deep blacks, low-key
    a = np.clip((a - 0.04) / 0.96, 0, 1) ** 1.3
    yy, xx = np.mgrid[0:H, 0:W]
    # one hard key light pool around the face
    kx, ky = key[0] * W, key[1] * H
    d = np.sqrt(((xx - kx) / (W * .30)) ** 2 + ((yy - ky) / (H * .55)) ** 2)
    light = np.clip(1.35 - d, 0.32, 1.0)
    if blinds:  # venetian blind stripes slanting across
        s = ((yy * 0.95 + xx * 0.3) / 44.0) % 1.0
        band = 0.5 + 0.5 * np.cos(s * 2 * np.pi)
        light = light * (0.62 + 0.38 * np.clip(band * 1.6 - 0.3, 0, 1))
    a = a * light[..., None]
    if warm:
        a = a * np.array([1.08, 0.97, 0.82])
    # vignette + grain
    v = np.sqrt(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .62)) ** 2)
    a = a * np.clip(1.15 - v ** 2.2, 0.05, 1)[..., None]
    a = a + np.random.default_rng(3).normal(0, 0.025, a.shape[:2])[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def place(cut, bg, x_frac, height_frac, top_frac):
    c = Image.open(cut).convert("RGBA")
    bbox = c.getbbox(); c = c.crop(bbox)
    hh = int(H * height_frac); ww = int(c.width * hh / c.height)
    c = c.resize((ww, hh), Image.LANCZOS)
    b = Image.open(bg).convert("RGB").resize((W, H), Image.LANCZOS)
    b = ImageEnhance.Brightness(b.filter(ImageFilter.GaussianBlur(1.6))).enhance(0.9)
    x = int(W * x_frac - ww / 2); y = int(H * top_frac)
    # soft shadow behind her
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); m = c.split()[3].point(lambda p: int(p * 0.7))
    sh.paste((0, 0, 0, 255), (x + 18, y + 10), m)
    b.paste(sh.filter(ImageFilter.GaussianBlur(14)), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    b.paste(c, (x, y), c)
    return b


JOBS = [
    ("stole_office_warm", "cover_cut_stole_warm.png", "bg_office", .62, 1.08, .04),
    ("gem_office", "cover_cut_gem.png", "bg_office", .68, 1.3, .04),
    ("gem_bar", "cover_cut_gem.png", "bg_bar", .64, 1.3, .04),
    ("gem_lounge", "cover_cut_gem.png", "bg_lounge", .66, 1.3, .04),
    ("gem_tile", "cover_cut_gem.png", "bg_tile", .64, 1.3, .04),
    ("stole_office", "cover_cut_stole.png", "bg_office", .62, 1.08, .04),
    ("stole_bar", "cover_cut_stole.png", "bg_bar", .62, 1.08, .04),
]
tiles = []
for name, cut, bg, xf, hf, tf in JOBS:
    bgf = [f for f in os.listdir(BG) if f.startswith(bg)][-1]
    im = place(os.path.join(ART, cut), os.path.join(BG, bgf), xf, hf, tf)
    im = grade(im, key=(xf, 0.30))
    p = os.path.join(OUT, name + ".jpg"); im.save(p, quality=90); tiles.append((name, im))
f = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 30); tw, th = 672, 384
S = Image.new("RGB", (2 * tw + 60, 3 * (th + 50) + 20), (8, 8, 10)); d = ImageDraw.Draw(S)
for i, (n, im) in enumerate(tiles):
    x = 20 + (i % 2) * (tw + 20); y = 10 + (i // 2) * (th + 50)
    S.paste(im.resize((tw, th)), (x, y)); d.text((x, y + th + 8), f"{i + 1}  {n}", fill=(232, 200, 144), font=f)
S.save(os.path.join(OUT, "sheet.png")); print("ok")
