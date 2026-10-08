"""Cut out and deflicker painted Vela frames.
Matte: the 3D render's alpha, refined at the edge band by distance from the grey paint background.
Deflicker: neighbours are warped onto each frame with optical flow measured on the clean 3D colour guides (not on the
paintings), occlusions rejected by guide error, then a per-pixel temporal median; finally a per-sequence colour lock.
Usage: vw_post.py GUIDEDIR PAINTDIR OUTDIR --set walk --angles 0,45 [--loop 1] [--radius 1] [--src paint]"""
import os, argparse
import numpy as np, cv2
BG = np.array([74, 74, 80], np.float32)

def load_rgba(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3: im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    return cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)

def matte(guide_a, paint):
    a = guide_a.astype(np.float32) / 255
    hard = (a > 0.5).astype(np.uint8)
    dil = cv2.dilate(hard, np.ones((5, 5), np.uint8)); ero = cv2.erode(hard, np.ones((5, 5), np.uint8))
    band = (dil > 0) & (ero == 0)
    d = np.linalg.norm(paint.astype(np.float32) - BG, axis=2)
    fg = np.clip((d - 10) / 28, 0, 1)  # near the grey background colour -> background
    m = np.where(ero > 0, 1.0, np.where(band, np.maximum(fg * (dil > 0), 0) * np.clip(a * 1.5 + 0.3, 0, 1), 0))
    m = cv2.GaussianBlur(m.astype(np.float32), (3, 3), 0.8)
    return np.clip(m, 0, 1)

def flow(gi, gj, dis):
    a = cv2.cvtColor(gi, cv2.COLOR_RGB2GRAY); b = cv2.cvtColor(gj, cv2.COLOR_RGB2GRAY)
    return dis.calc(a, b, None)

def warp(img, f):
    h, w = f.shape[:2]; gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + f[..., 0], gy + f[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def process(gdir, pdir, odir, loop, radius, src):
    os.makedirs(odir, exist_ok=True)
    n = len([f for f in os.listdir(pdir) if f.startswith(src + '_') and f.endswith('.png') and f[len(src) + 1:-4].isdigit()])
    G = [load_rgba(os.path.join(gdir, 'color_%02d.png' % i)) for i in range(n)]
    Gc = [(g[..., :3].astype(np.float32) * (g[..., 3:4] / 255.0)).astype(np.uint8) for g in G]
    P = [cv2.cvtColor(cv2.imread(os.path.join(pdir, '%s_%02d.png' % (src, i))), cv2.COLOR_BGR2RGB) for i in range(n)]
    M = [matte(G[i][..., 3], P[i]) for i in range(n)]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    out = []
    for i in range(n):
        stack = [P[i].astype(np.float32)]; valid = [np.ones(P[i].shape[:2], bool)]
        for d in range(-radius, radius + 1):
            if d == 0: continue
            j = i + d
            if loop: j %= n
            elif j < 0 or j >= n: continue
            f = flow(Gc[i], Gc[j], dis)
            gw = warp(Gc[j], f).astype(np.float32); err = np.abs(gw - Gc[i].astype(np.float32)).sum(2)
            ok = (err < 30) & (warp(M[j], f) > 0.5) & (M[i] > 0.5)
            stack.append(warp(P[j], f).astype(np.float32)); valid.append(ok)
        S = np.stack(stack); V = np.stack(valid)
        # per-pixel median over the valid aligned samples (current frame always counts)
        Sm = np.where(V[..., None], S, np.nan)
        med = np.nanmedian(Sm, axis=0)
        cur = S[0]
        res = np.where(np.isnan(med), cur, 0.35 * cur + 0.65 * med)
        out.append(res)
    # colour lock: every frame's mean colour inside the matte follows the sequence mean
    means = [np.array([(o[..., c] * M[i]).sum() / max(M[i].sum(), 1) for c in range(3)]) for i, o in enumerate(out)]
    tgt = np.mean(means, axis=0)
    for i, o in enumerate(out):
        g = np.clip(tgt / np.maximum(means[i], 1), 0.92, 1.08)
        rgb = np.clip(o * g, 0, 255).astype(np.uint8)
        a = (M[i] * 255).astype(np.uint8)
        cv2.imwrite(os.path.join(odir, 'cut_%02d.png' % i), cv2.cvtColor(np.dstack([rgb, a]), cv2.COLOR_RGBA2BGRA))
    print('post', odir, n, 'frames')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('guides'); ap.add_argument('paint'); ap.add_argument('out')
    ap.add_argument('--set', default='walk'); ap.add_argument('--angles', default='0'); ap.add_argument('--loop', type=int, default=-1)
    ap.add_argument('--radius', type=int, default=1); ap.add_argument('--src', default='paint')
    a = ap.parse_args()
    loop = a.loop if a.loop >= 0 else (1 if a.set in ('walk', 'idle') else 0)
    for az in [int(x) for x in a.angles.split(',')]:
        sub = os.path.join(a.set, 'a%03d' % az)
        process(os.path.join(a.guides, sub), os.path.join(a.paint, sub), os.path.join(a.out, sub), loop, a.radius, a.src)
