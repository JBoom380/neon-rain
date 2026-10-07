"""Small authored textures for the environment pass (system Python + PIL): the office door's frosted glass lettering
(painted on the hall side, so it reads mirrored from inside the office). Output: art/env_src/tex/."""
import pathlib, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEX = ROOT / "art" / "env_src" / "tex"; TEX.mkdir(parents=True, exist_ok=True)
FONT = "C:/Windows/Fonts/georgia.ttf"; FONTB = "C:/Windows/Fonts/georgiab.ttf"


def door_glass():
    w, h = 512, 640
    rnd = random.Random(7)
    im = Image.new("RGB", (w, h), (138, 118, 84))
    px = im.load()
    for y in range(h):  # pebbled frosted glass
        for x in range(w):
            v = rnd.randint(-14, 14)
            r, g, b = px[x, y]; px[x, y] = (r + v, g + v, b + v - 4)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONTB, 62); f2 = ImageFont.truetype(FONT, 30)
    for text, font, y in (("S. HARROW", f1, 250), ("PRIVATE INVESTIGATIONS", f2, 318)):
        tw = d.textlength(text, font=font)
        d.text(((w - tw) / 2 + 2, y + 2), text, font=font, fill=(150, 120, 60))
        d.text(((w - tw) / 2, y), text, font=font, fill=(18, 14, 10))
    d.line((90, 372, w - 90, 372), fill=(18, 14, 10), width=2)
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(TEX / "door_glass.png")


if __name__ == "__main__":
    door_glass()
    print("ok")
