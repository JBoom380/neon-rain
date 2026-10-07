"""Recolor the grey skin and hair of the stole cut-out with the gem photo's warm skin and golden hair (percentile colour transfer)."""
import numpy as np
from PIL import Image

ART = r"C:\Users\John\Documents\GitHub\projects\neon-rain-fps\art"
gem = Image.open(ART + r"\cover_cut_gem.png").convert("RGBA"); gem = gem.crop(gem.getbbox())
st = Image.open(ART + r"\cover_cut_stole.png").convert("RGBA"); st = st.crop(st.getbbox())
G = np.asarray(gem).astype(np.float32)
S = np.asarray(st).astype(np.float32).copy()


def lum(a): return a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114


def patch(a, x0, y0, x1, y1, lo=60):
    p = a[y0:y1, x0:x1].reshape(-1, 4); p = p[(p[:, 3] > 200) & (lum(p) > lo)]
    rgb = p[:, :3]; return rgb[np.argsort(lum(rgb))]


skin_src = np.concatenate([patch(G, 300, 120, 480, 400), patch(G, 300, 420, 520, 620), patch(G, 130, 500, 240, 650)])
hair_src = np.concatenate([patch(G, 160, 150, 280, 420), patch(G, 470, 60, 590, 380), patch(G, 260, 10, 520, 110)])

H, W = S.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]
L = lum(S[..., :3]); a = S[..., 3] > 128
r, g, b = S[..., 0], S[..., 1], S[..., 2]
red = (r > g * 1.6) & (r > 90)
face = (((xx - 322) / 72.0) ** 2 + ((yy - 120) / 92.0) ** 2) < 1
neck = (xx > 235) & (xx < 360) & (yy >= 180) & (yy < 395)
hair = (yy < 215) & ~face & (xx > 195) & (xx < 440)
skin_m = (face | neck) & a & ~red & (L > 70)
hair_m = hair & a & ~red & (L > 90)


import cv2
lab = cv2.cvtColor(S[..., :3].astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)


def transfer(mask, src):
    srcl = cv2.cvtColor(src.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    m = mask.astype(np.float32)
    soft = cv2.GaussianBlur(m, (0, 0), 6)
    t = lab[mask]
    mu_t, sd_t = t.mean(0), t.std(0) + 1e-3
    mu_s, sd_s = srcl.mean(0), srcl.std(0)
    new = lab.copy()
    # keep the target's lightness detail; take chroma (a, b) from the source, lightness mean shifted gently
    new[..., 0] = lab[..., 0] + (mu_s[0] - mu_t[0]) * 0.5
    new[..., 1] = (lab[..., 1] - mu_t[1]) * min(1.5, sd_s[1] / sd_t[1]) + mu_s[1]
    new[..., 2] = (lab[..., 2] - mu_t[2]) * min(1.5, sd_s[2] / sd_t[2]) + mu_s[2]
    lab[:] = lab * (1 - soft[..., None]) + new * soft[..., None]


transfer(skin_m, skin_src); transfer(hair_m, hair_src)
S[..., :3] = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
# soften the mask edges by blending a blurred copy back over the region borders
Image.fromarray(S.astype(np.uint8)).save(ART + r"\cover_cut_stole_warm.png")
print("skin px", skin_m.sum(), "hair px", hair_m.sum())
