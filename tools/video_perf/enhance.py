"""Upscale an LTX take x2 (RealESRGAN x2plus, BSD-3) and restore the face (GFPGAN v1.4, Apache-2.0) per frame.
Run with ComfyUI's embedded python (spandrel + torch + cv2):
  E:/ComfyUI_windows_portable/python_embeded/python.exe enhance.py SRC.mp4 OUT.mkv --eyes x1,y1,x2,y2 --mouth x,y --ref N [--w 0.5]
Eye and mouth points are source pixels on frame --ref. The face is tracked per frame by template match, aligned to the
FFHQ 512 template, restored, blended back (weight --w) through a feathered mask. Writes a lossless FFV1 file and
face_check.json (per-frame correlation of the restored face with the upscaled face: identity drift check)."""
import argparse, json, os, subprocess
import numpy as np, cv2, torch
from spandrel import ModelLoader

M = 'E:/ComfyUI_windows_portable/ComfyUI/models/'
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--eyes', required=True); ap.add_argument('--mouth', required=True); ap.add_argument('--ref', type=int, default=0)
ap.add_argument('--w', type=float, default=0.5); ap.add_argument('--tile', type=int, default=256)
a = ap.parse_args()
w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', a.src], capture_output=True, text=True).stdout.strip().split(','))
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
dev = 'cuda'
up = ModelLoader().load_from_file(M + 'upscale_models/RealESRGAN_x2plus.pth').to(dev).eval().half()
fx = ModelLoader().load_from_file(M + 'facerestore_models/GFPGANv1.4.pth').to(dev).eval()


@torch.no_grad()
def upscale(img):
    t = torch.from_numpy(img).permute(2, 0, 1)[None].float().div(255)
    H, W = img.shape[:2]; T, P = a.tile, 16; out = torch.zeros(1, 3, H * 2, W * 2)
    for y in range(0, H, T):
        for x in range(0, W, T):
            y0, x0, y1, x1 = max(0, y - P), max(0, x - P), min(H, y + T + P), min(W, x + T + P)
            o = up.model(t[:, :, y0:y1, x0:x1].to(dev).half()).float().cpu()
            oy, ox = (y - y0) * 2, (x - x0) * 2; hh, ww = (min(H, y + T) - y) * 2, (min(W, x + T) - x) * 2
            out[:, :, y * 2:y * 2 + hh, x * 2:x * 2 + ww] = o[:, :, oy:oy + hh, ox:ox + ww]
    return (out[0].permute(1, 2, 0).clamp(0, 1).numpy() * 255).round().astype(np.uint8)


@torch.no_grad()
def restore(face):
    t = torch.from_numpy(face).permute(2, 0, 1)[None].float().div(255).to(dev)
    t = (t - 0.5) / 0.5
    o = fx.model(t)
    o = o[0] if isinstance(o, (tuple, list)) else o
    o = (o * 0.5 + 0.5).clamp(0, 1)
    return (o[0].permute(1, 2, 0).cpu().numpy() * 255).round().astype(np.uint8)


ex1, ey1, ex2, ey2 = map(float, a.eyes.split(',')); mx, my = map(float, a.mouth.split(','))
P0 = np.float32([[ex1, ey1], [ex2, ey2], [mx, my]])
FF = np.float32([[192.98, 239.95], [318.90, 240.19], [257.17, 371.28]])
cx, cy = P0[:, 0].mean(), P0[:, 1].mean(); r = int(abs(ex2 - ex1) * 1.6)
g = lambda im: cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
tpl = g(fr[a.ref])[int(cy - r):int(cy + r), int(cx - r):int(cx + r)]
mask = np.zeros((512, 512), np.float32); cv2.ellipse(mask, (256, 290), (170, 215), 0, 0, 360, 1, -1); mask = cv2.GaussianBlur(mask, (0, 0), 22)
tmp = os.path.splitext(a.out)[0] + '_frames'; os.makedirs(tmp, exist_ok=True)
check = []
for k, f in enumerate(fr):
    # track: translation of the face box from the reference frame
    sr = 12; y0, x0 = int(cy - r - sr), int(cx - r - sr)
    res = cv2.matchTemplate(g(f)[y0:y0 + 2 * r + 2 * sr, x0:x0 + 2 * r + 2 * sr], tpl, cv2.TM_CCOEFF_NORMED)
    _, _, _, loc = cv2.minMaxLoc(res); d = np.float32([loc[0] - sr, loc[1] - sr])
    U = upscale(f); pts = (P0 + d) * 2
    A, _ = cv2.estimateAffinePartial2D(pts, FF)
    crop = cv2.warpAffine(U, A, (512, 512), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    rest = restore(crop)
    mixed = (crop.astype(np.float32) * (1 - a.w) + rest.astype(np.float32) * a.w)
    Ai = cv2.invertAffineTransform(A)
    back = cv2.warpAffine(mixed, Ai, (U.shape[1], U.shape[0]), flags=cv2.INTER_LANCZOS4)
    mk = cv2.warpAffine(mask, Ai, (U.shape[1], U.shape[0]))[..., None]
    O = (U * (1 - mk) + back * mk).clip(0, 255).astype(np.uint8)
    s1 = cv2.resize(g(crop), (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32); s2 = cv2.resize(g(rest), (64, 64), interpolation=cv2.INTER_AREA).astype(np.float32)
    check.append(round(float(np.corrcoef(s1.ravel(), s2.ravel())[0, 1]), 4))
    cv2.imwrite(f'{tmp}/{k:04d}.png', cv2.cvtColor(O, cv2.COLOR_RGB2BGR))
    if k in (0, len(fr) // 2): cv2.imwrite(f'{tmp}_face{k}.png', cv2.cvtColor(np.concatenate([crop, rest], 1), cv2.COLOR_RGB2BGR))
    print(k, d.tolist(), check[-1], flush=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', f'{tmp}/%04d.png', '-c:v', 'ffv1', '-pix_fmt', 'rgb24', a.out], check=True)
json.dump({'src': a.src, 'face_corr': check, 'min': min(check), 'mean': sum(check) / len(check)}, open(os.path.splitext(a.out)[0] + '_face_check.json', 'w'))
print('min corr', min(check), 'mean', sum(check) / len(check))
