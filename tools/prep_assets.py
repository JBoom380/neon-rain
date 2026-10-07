"""Shrink the painted sprites in art/sprites/ into phone-sized game assets in assets/sprites/.
Angles + idle frames: 384x768 WebP (alpha). Close-ups: 480x640 JPEG. Run: python tools/prep_assets.py"""
import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "art" / "sprites", ROOT / "assets" / "sprites"
OUT.mkdir(parents=True, exist_ok=True)
ANGLES = ["front", "front34L", "front34R", "sideL", "sideR", "back34L", "back34R", "back"]
total = 0
for who in ("vela", "dolores"):
    for a in ANGLES:
        im = Image.open(SRC / who / f"{who}_{a}.png").convert("RGBA").resize((384, 768), Image.LANCZOS)
        p = OUT / f"{who}_{a}.webp"; im.save(p, "WEBP", quality=88, method=6); total += p.stat().st_size
    for i in range(12):
        im = Image.open(SRC / who / "idle" / f"{who}_idle_{i:02d}.png").convert("RGBA").resize((384, 768), Image.LANCZOS)
        p = OUT / f"{who}_idle_{i:02d}.webp"; im.save(p, "WEBP", quality=85, method=6); total += p.stat().st_size
    for e in ("warm", "guarded", "cold"):
        im = Image.open(SRC / who / f"{who}_close_{e}.png").convert("RGB").resize((480, 640), Image.LANCZOS)
        p = OUT / f"{who}_close_{e}.jpg"; im.save(p, "JPEG", quality=86, optimize=True); total += p.stat().st_size
print(f"wrote {len(list(OUT.iterdir()))} files, {total / 1e6:.2f} MB")
