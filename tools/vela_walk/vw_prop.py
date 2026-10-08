"""Second-pass inits: carry one key painting to every frame of a sequence along optical flow measured on the 3D colour
guides (chained frame to frame, so the warp is never asked to jump more than one step), and fall back to the deflickered
first-pass frame wherever the warp is unreliable (occlusion, limbs crossing). The result goes back through vw_paint.py at
low denoise with the same seed, so every frame starts from the same face, hair and dress.
Usage: vw_prop.py GUIDEDIR CUTDIR OUTDIR --set walk --angles 0 [--key 4]"""
import os, argparse
import numpy as np, cv2
BG = np.array([74, 74, 80], np.float32)
def rgba(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED); return cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32)
def warp(img, f):
    h, w = f.shape[:2]; gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + f[..., 0], gy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
def main(gd, cd, od, loop, key):
    os.makedirs(od, exist_ok=True)
    n = len([f for f in os.listdir(cd) if f.startswith('cut_')])
    G = [rgba(os.path.join(gd, 'color_%02d.png' % i)) for i in range(n)]
    Gc = [(g[..., :3] * g[..., 3:4] / 255).astype(np.uint8) for g in G]
    Gy = [cv2.cvtColor(g, cv2.COLOR_RGB2GRAY) for g in Gc]
    C = [rgba(os.path.join(cd, 'cut_%02d.png' % i)) for i in range(n)]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    if key < 0:  # auto: the most typical first-pass frame (closest to the per-pixel median of the sequence)
        med = np.median(np.stack([c[..., :3] for c in C]), axis=0)
        key = int(np.argmin([np.abs(c[..., :3] - med).mean() for c in C]))
    # premultiplied key painting (+ confidence channel) carried outward from the key in both directions
    def carry(order):
        cur = np.dstack([C[key][..., :3] * C[key][..., 3:4] / 255, C[key][..., 3:4] / 255, np.ones(C[key].shape[:2] + (1,), np.float32)])
        out = {key: cur}
        prev = key
        for i in order:
            f = dis.calc(Gy[i], Gy[prev], None)
            w = warp(cur, f)
            err = np.abs(warp(Gc[prev].astype(np.float32), f) - Gc[i].astype(np.float32)).sum(2)
            ok = (err < 24).astype(np.float32) * (G[i][..., 3] > 127)
            ok = cv2.GaussianBlur(cv2.erode(ok, np.ones((3, 3), np.uint8)), (7, 7), 2)
            w[..., 4] *= ok
            out[i] = w; cur = w; prev = i
        return out
    if loop:
        half = n // 2
        fw = carry([(key + d) % n for d in range(1, half + 1)])
        bw = carry([(key - d) % n for d in range(1, n - half)])
        car = {**bw, **fw}
    else:
        car = {**carry(list(range(key - 1, -1, -1))), **carry(list(range(key + 1, n)))}
    for i in range(n):
        w = car[i]; conf = np.clip(w[..., 4:5], 0, 1)
        a = np.maximum(w[..., 3:4], 1e-3); keyrgb = w[..., :3] / a
        base = C[i][..., :3]
        rgb = keyrgb * conf + base * (1 - conf)
        alpha = G[i][..., 3:4] / 255
        img = rgb * alpha + BG * (1 - alpha)
        cv2.imwrite(os.path.join(od, 'init_%02d.png' % i), cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    print('prop', od, n, 'key', key, 'mean conf', [round(float(car[i][..., 4].mean() / max(G[i][..., 3].mean() / 255, 1e-3)), 2) for i in range(n)])
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('guides'); ap.add_argument('cut'); ap.add_argument('out')
    ap.add_argument('--set', default='walk'); ap.add_argument('--angles', default='0'); ap.add_argument('--key', default='-1')
    a = ap.parse_args()
    keys = [int(k) for k in a.key.split(',')]
    for j, az in enumerate([int(x) for x in a.angles.split(',')]):
        sub = os.path.join(a.set, 'a%03d' % az)
        main(os.path.join(a.guides, sub), os.path.join(a.cut, sub), os.path.join(a.out, sub), a.set in ('walk', 'idle'), keys[min(j, len(keys) - 1)])
