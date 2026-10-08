"""NEON RAIN video-performance post: matte, loop, export.

python process.py SRC.mp4 NAME [--opaque] [--min-len 60] [--xfade 12] [--key 12] [--height 720] [--skip 3]

Steps
1. Loop points: search frame pairs (i, j) whose neighbourhoods match best (RGB, low-res, +-2 frames, velocity included).
2. Matte (cut-outs only): rembg BiRefNet (birefnet-general) on key frames every --key frames inside the loop range,
   propagated to the frames between by DIS optical flow from both neighbouring keys, edge-snapped with a guided filter,
   then smoothed in time with a colour-weighted (motion-aware) +-2 frame filter. Colour is decontaminated against a
   background plate so hair edges carry no grey fringe.
3. Seamless loop: the last --xfade frames morph into the frames before i with a flow-warped two-way blend.
4. Export to assets/video/: NAME.webm (VP9 + alpha), NAME_stack.mp4 (H.264, colour on top, alpha below, for WebKit/iOS),
   NAME.jpg poster. Opaque clips: NAME.webm (VP9) + NAME.mp4 (H.264).
"""
import argparse, os, subprocess, sys, json
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'video')
CACHE = os.path.join(HERE, '_cache')


def read_frames(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path], capture_output=True, text=True)
    w, h = map(int, p.stdout.strip().split(','))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).copy()


def small(fr, s=6):
    return np.stack([cv2.resize(f, (f.shape[1] // s, f.shape[0] // s), interpolation=cv2.INTER_AREA) for f in fr]).astype(np.float32) / 255.0


def find_loop(fr, min_len, xf, skip, weight=None):
    s = small(fr)
    n = len(s)
    if weight is not None:
        wt = cv2.resize(weight, (s.shape[2], s.shape[1]), interpolation=cv2.INTER_AREA)
        s = s * np.sqrt(wt / max(wt.mean(), 1e-6))[None, :, :, None]
    flat = s.reshape(n, -1)
    D = np.sqrt(((flat[:, None, :] - flat[None, :, :]) ** 2).mean(-1))
    best = None
    for i in range(max(xf, skip), n):
        for j in range(i + min_len, n + 1):
            # the frame after j-1 is i; it must look like j (which would have followed j-1)
            ks = [k for k in (-2, -1, 0, 1, 2) if 0 <= i + k < n and 0 <= j + k < n]
            if len(ks) < 3:
                if j == n:  # j is past the end: compare i-1 with j-1 and i-2 with j-2
                    ks2 = [k for k in (-3, -2, -1) if i + k >= 0]
                    c = np.mean([D[i + k, j + k] for k in ks2])
                else:
                    continue
            else:
                c = np.mean([D[i + k, j + k] for k in ks])
            c += 0.002 * abs((j - i) - 84) / 84  # mild preference for ~3.5 s
            if best is None or c < best[0]:
                best = (c, i, j)
    return best


def flow(a, b, dis):
    ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
    return dis.calc(ga, gb, None)


def warp(img, fl):
    h, w = fl.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(img, gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def box(x, r):
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), normalize=True, borderType=cv2.BORDER_REFLECT)


def guided(I, p, r=5, eps=2e-4):
    mI, mp = box(I, r), box(p, r)
    cov = box(I * p, r) - mI * mp
    var = box(I * I, r) - mI * mI
    a = cov / (var + eps)
    b = mp - a * mI
    return box(a, r) * I + box(b, r)


def birefnet_masks(fr, idxs, name):
    os.makedirs(CACHE, exist_ok=True)
    need = [i for i in idxs if not os.path.exists(os.path.join(CACHE, f'{name}_m{i:03d}.png'))]
    if need:
        from rembg import new_session, remove
        from PIL import Image
        sess = new_session('birefnet-general')
        for i in need:
            m = remove(Image.fromarray(fr[i]), session=sess, only_mask=True)
            m.save(os.path.join(CACHE, f'{name}_m{i:03d}.png'))
            print('  key mask', i, flush=True)
    return {i: cv2.imread(os.path.join(CACHE, f'{name}_m{i:03d}.png'), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0 for i in idxs}


def matte(fr, lo, hi, key, name):
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    keys = list(range(lo, hi, key))
    if keys[-1] != hi - 1:
        keys.append(hi - 1)
    km = birefnet_masks(fr, keys, name)
    A = {}
    for t in range(lo, hi):
        if t in km:
            m = km[t]
        else:
            a = max(k for k in keys if k < t)
            b = min(k for k in keys if k > t)
            wa = (b - t) / (b - a)
            ma = warp(km[a], flow(fr[t], fr[a], dis))
            mb = warp(km[b], flow(fr[t], fr[b], dis))
            m = wa * ma + (1 - wa) * mb
        g = cv2.cvtColor(fr[t], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        band = cv2.dilate(((m > 0.02) & (m < 0.98)).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
        gm = np.clip(guided(g, m), 0, 1)
        m = np.where(band, 0.5 * gm + 0.5 * m, m)
        A[t] = m
    # motion-aware temporal smoothing: neighbours count only where the pixel colour agrees
    S = {}
    for t in range(lo, hi):
        acc = np.zeros_like(A[t]); ws = np.zeros_like(A[t])
        ft = fr[t].astype(np.float32)
        for k, gk in ((-2, 0.25), (-1, 0.6), (0, 1.0), (1, 0.6), (2, 0.25)):
            u = t + k
            if u < lo or u >= hi:
                continue
            d = np.abs(fr[u].astype(np.float32) - ft).mean(-1)
            w = gk * np.exp(-(d / 10.0) ** 2)
            acc += w * A[u]; ws += w
        a = acc / np.maximum(ws, 1e-6)
        a = np.clip((a - 0.03) / 0.94, 0, 1)
        S[t] = a
    return S


def pushpull(img, w, levels=7):
    """fill pixels with weight 0 from their neighbours (weighted pyramid)"""
    pyr = []
    c, ww = img * w[..., None], w.copy()
    for _ in range(levels):
        pyr.append((c, ww))
        c = cv2.pyrDown(c); ww = cv2.pyrDown(ww)
    out = c / np.maximum(ww[..., None], 1e-6)
    for c, ww in reversed(pyr):
        up = cv2.resize(out, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        k = np.clip(ww * 4, 0, 1)[..., None]
        out = k * (c / np.maximum(ww[..., None], 1e-6)) + (1 - k) * up
    return out


def decontaminate(rgb, a):
    I = rgb.astype(np.float32) / 255.0
    bgw = (a < 0.03).astype(np.float32)
    B = pushpull(I, cv2.erode(bgw, np.ones((5, 5), np.uint8)))
    F = (I - (1 - a[..., None]) * B) / np.maximum(a[..., None], 0.08)
    F = np.clip(F, 0, 1)
    k = np.clip((a - 0.6) / 0.35, 0, 1)[..., None]
    F = k * I + (1 - k) * F
    # extend foreground colour under transparent pixels so filtering never pulls in grey
    fw = np.clip((a - 0.5) * 4, 0, 1)
    F = np.where(fw[..., None] > 0, F, pushpull(F, fw))
    return F


def blend_morph(A, B, w, dis):
    fab = flow(A, B, dis); fba = flow(B, A, dis)
    Aw = warp(A.astype(np.float32), fab * w)
    Bw = warp(B.astype(np.float32), fba * (1 - w))
    return (1 - w) * Aw + w * Bw, fab, fba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('name')
    ap.add_argument('--opaque', action='store_true')
    ap.add_argument('--min-len', type=int, default=60)
    ap.add_argument('--xfade', type=int, default=12)
    ap.add_argument('--key', type=int, default=12)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--skip', type=int, default=3)
    ap.add_argument('--crf', type=int, default=20)
    ap.add_argument('--crf-h264', type=int, default=18)
    ap.add_argument('--mode', default='auto', help='auto | xfade | pingpong | once')
    ap.add_argument('--range', type=str, default='')
    ap.add_argument('--feather', type=float, default=0.03, help='fraction of width faded at the left and right frame edges')
    ap.add_argument('--fade-bottom', type=float, default=0.07, help='fraction of height faded to transparent at the bottom edge')
    args = ap.parse_args()
    fr = read_frames(args.src)
    n = len(fr)
    xf = args.xfade
    weight = None
    if not args.opaque:
        lo0, hi0 = (0, n) if not args.range else (max(0, int(args.range.split(':')[0]) - (xf if args.mode != 'once' else 0)), min(n, int(args.range.split(':')[1]) + 1))
        S = matte(fr, lo0, hi0, args.key, args.name)
        weight = cv2.dilate(np.max(np.stack([S[t] for t in range(lo0, hi0, args.key)]), 0), np.ones((15, 15), np.uint8))
    if args.range:
        i, j = map(int, args.range.split(':')); cost = -1
    else:
        cost, i, j = find_loop(fr, min(args.min_len, n - xf - args.skip - 1), xf, args.skip, weight)
    mode = args.mode if args.mode != 'auto' else ('xfade' if cost < 0.045 else 'pingpong')
    if mode == 'pingpong' and not args.range:
        # turn around where she moves least, so the reversal reads as a pause, not a rewind
        sm = small(fr)
        if weight is not None:
            wt = cv2.resize(weight, (sm.shape[2], sm.shape[1]), interpolation=cv2.INTER_AREA); sm = sm * wt[None, :, :, None]
        v = np.sqrt(((sm[1:] - sm[:-1]) ** 2).mean((1, 2, 3)))
        v = np.convolve(v, np.ones(5) / 5, mode='same')
        a0, a1 = args.skip + 2, max(args.skip + 3, n // 4)
        i = a0 + int(np.argmin(v[a0:a1])); j = (3 * n) // 4 + int(np.argmin(v[(3 * n) // 4:n - 2])) + 1
    print(f'{args.name}: {n} frames, mode {mode}, loop {i}..{j} ({j - i} frames, {(j - i) / 24:.2f} s), cost {cost:.4f}', flush=True)
    stats_mode = mode
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    L = j - i
    seq_rgb, seq_a = [], []
    order = list(range(i, j)) + list(range(j - 2, i, -1)) if stats_mode == 'pingpong' else list(range(i, j))  # once / xfade: forward
    for t in order:
        rgb = fr[t].astype(np.float32)
        a = S[t] if not args.opaque else None
        if stats_mode == 'xfade' and t >= j - xf:  # morph into the frames before i
            u = t - L
            w = (t - (j - xf) + 1) / (xf + 1)
            w = w * w * (3 - 2 * w)
            rgb, fab, fba = blend_morph(fr[t], fr[u], w, dis)
            if not args.opaque:
                a = (1 - w) * warp(S[t], fab * w) + w * warp(S[u], fba * (1 - w))
        seq_rgb.append(np.clip(rgb, 0, 255).astype(np.uint8)); seq_a.append(a)
    H0, W0 = fr.shape[1:3]
    H = min(args.height, H0); W = int(round(W0 * H / H0 / 2)) * 2
    tmp = os.path.join(CACHE, args.name + '_seq'); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.makedirs(OUT, exist_ok=True)
    stats = {'name': args.name, 'src': os.path.basename(args.src), 'loop': [i, j], 'frames': L, 'cost': round(float(cost), 4), 'mode': stats_mode, 'out_frames': len(seq_rgb), 'w': W, 'h': H}
    if args.opaque:
        for k, rgb in enumerate(seq_rgb):
            cv2.imwrite(os.path.join(tmp, f'{k:04d}.png'), cv2.cvtColor(cv2.resize(rgb, (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR))
        pat = os.path.join(tmp, '%04d.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', pat, '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuv420p', '-crf', str(args.crf), '-b:v', '0', '-row-mt', '1', '-an', os.path.join(OUT, args.name + '.webm')], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', pat, '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p', '-crf', '22', '-movflags', '+faststart', '-an', os.path.join(OUT, args.name + '.mp4')], check=True)
        cv2.imwrite(os.path.join(OUT, args.name + '.jpg'), cv2.cvtColor(cv2.resize(seq_rgb[0], (W, H), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        files = [args.name + e for e in ('.webm', '.mp4', '.jpg')]
    else:
        ramp = None
        if args.fade_bottom > 0:
            yy = np.arange(H0, dtype=np.float32) / H0
            ramp = np.clip((1 - yy) / args.fade_bottom, 0, 1)[:, None]
            ramp = ramp * ramp * (3 - 2 * ramp)
        xx = np.arange(W0, dtype=np.float32) / W0
        xr = np.clip(np.minimum(xx, 1 - xx) / max(args.feather, 1e-4), 0, 1)[None, :]; xr = xr * xr * (3 - 2 * xr)
        for k, (rgb, a) in enumerate(zip(seq_rgb, seq_a)):
            a = a * xr
            if ramp is not None:
                a = a * ramp
            F = decontaminate(rgb, a)
            Fs = cv2.resize(F, (W, H), interpolation=cv2.INTER_AREA)
            As = np.clip(cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA), 0, 1)
            rgba = np.dstack([Fs * 255, As * 255]).round().astype(np.uint8)
            cv2.imwrite(os.path.join(tmp, f'{k:04d}.png'), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
            stack = np.concatenate([Fs * 255, np.repeat(As[..., None] * 255, 3, -1)], 0).round().astype(np.uint8)
            cv2.imwrite(os.path.join(tmp, f's{k:04d}.png'), cv2.cvtColor(stack, cv2.COLOR_RGB2BGR))
            if k == 0:
                cv2.imwrite(os.path.join(OUT, args.name + '.png'), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        webm = os.path.join(OUT, args.name + '.webm'); plog = os.path.join(tmp, 'vp9pass')
        vp9 = ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0', '-crf', str(args.crf), '-b:v', '0', '-g', '24', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '1', '-passlogfile', plog, '-an']
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, '%04d.png')] + vp9 + ['-pass', '1', '-f', 'webm', os.devnull], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, '%04d.png')] + vp9 + ['-pass', '2', webm], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, 's%04d.png'), '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-tune', 'film', '-pix_fmt', 'yuv420p', '-crf', str(args.crf_h264),
                        '-g', '24', '-movflags', '+faststart', '-an', os.path.join(OUT, args.name + '_stack.mp4')], check=True)
        files = [args.name + e for e in ('.webm', '_stack.mp4', '.png')]
    stats['bytes'] = {f: os.path.getsize(os.path.join(OUT, f)) for f in files}
    print(json.dumps(stats), flush=True)
    with open(os.path.join(CACHE, args.name + '.json'), 'w') as f:
        json.dump(stats, f, indent=1)


if __name__ == '__main__':
    main()
