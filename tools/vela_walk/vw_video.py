"""Vela front walk video: one LTX take -> matted, size-locked, seamless gait-cycle loop for the game billboard.
  1. Matte with the video_perf BiRefNet + flow + guided filter + temporal smoothing chain.
  2. Size lock: the take tracks back unevenly, so each frame is scaled and shifted so the slow trend of her height, feet line and
     centre stays fixed (the per-step bob is kept). In the game the billboard itself moves forward at the stride speed.
  3. Loop: the gait cycle (two steps) with the best match inside the walking part, closed with a flow-warped crossfade.
  4. Export assets/video/NAME.webm (VP9 alpha), NAME_stack.mp4 (WebKit), NAME.png, and NAME.json (frames, fps, steps per loop).
Usage: vw_video.py TAKE.mp4 NAME [--skip-start 18] [--xfade 6] [--lag 18:44] [--qc OUT.png]"""
import argparse, os, sys, json, subprocess
import numpy as np, cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'video_perf'))
import process as VP

def trend(y, deg=2):
    t = np.arange(len(y)); return np.polyval(np.polyfit(t, y, deg), t)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('name')
    ap.add_argument('--skip-start', type=int, default=18); ap.add_argument('--xfade', type=int, default=6)
    ap.add_argument('--lag', default='18:44'); ap.add_argument('--qc', default=''); ap.add_argument('--height', type=int, default=896)
    ap.add_argument('--crf', type=int, default=22); ap.add_argument('--no-export', action='store_true')
    ap.add_argument('--whole', action='store_true', help='the take is already one seamless gait cycle: no size lock, no loop search')
    a = ap.parse_args()
    fr = VP.read_frames(a.src); n, H0, W0 = fr.shape[:3]
    S = VP.matte(fr, 0, n, 8, a.name)
    A = np.stack([S[t] for t in range(n)])
    # per-frame figure box from the matte
    top, bot, cx = [], [], []
    for t in range(n):
        rows = np.where(A[t].max(1) > 0.5)[0]; cols = np.where(A[t].max(0) > 0.5)[0]
        top.append(rows[0]); bot.append(rows[-1]); cx.append((A[t].sum(0) * np.arange(W0)).sum() / max(A[t].sum(), 1))
    top, bot, cx = map(np.array, (top, bot, cx)); h = bot - top
    s0 = 0 if a.whole else a.skip_start
    ht, bt, ct = trend(h[s0:]), trend(bot[s0:]), trend(cx[s0:], 1)
    Href = float(np.median(h[s0:])); Bref = H0 * 0.965; Cref = W0 / 2
    print(f'{a.name}: {n} frames, height px {h[s0]}..{h[-1]} (trend {ht[0]:.0f}->{ht[-1]:.0f}), feet {bot[s0]}..{bot[-1]}', flush=True)
    N_rgb, N_a = [], []
    for k, t in enumerate(range(s0, n)):
        sc = Href / ht[k]; tx = Cref - ct[k] * sc; ty = Bref - bt[k] * sc
        if a.whole: sc, tx, ty = Href / float(np.median(h)), 0.0, 0.0; ty = Bref - float(np.median(bot)) * sc; tx = Cref - float(np.median(cx)) * sc
        M = np.float32([[sc, 0, tx], [0, sc, ty]])
        N_rgb.append(cv2.warpAffine(fr[t], M, (W0, H0), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE))
        N_a.append(cv2.warpAffine(A[t], M, (W0, H0), flags=cv2.INTER_LINEAR, borderValue=0))
    N_rgb = np.stack(N_rgb); N_a = np.stack(N_a); m = len(N_rgb)
    # gait-cycle loop: compare small premultiplied frames (+-1 frame neighbourhood, velocity included)
    sm = VP.small(N_rgb, 6) * np.stack([cv2.resize(x, (W0 // 6, H0 // 6), interpolation=cv2.INTER_AREA) for x in N_a])[..., None]
    l0, l1 = map(int, a.lag.split(':')); xf = a.xfade; best = (9, 0, 0)
    if a.whole: l0 = l1 = m
    for L in range(l0, min(l1, m - xf - 3) + 1):
        for i in ([0] if a.whole else range(2, m - L - 2)):
            if a.whole: break
            j = i + L
            c = sum(np.mean((sm[i + d] - sm[j + d]) ** 2) for d in (-1, 0, 1)) + np.mean(((sm[i + 1] - sm[i - 1]) - (sm[j + 1] - sm[j - 1])) ** 2)
            if c < best[0]: best = (c, i, j)
    cost, i, j = best if not a.whole else (0.0, 0, m); L = j - i
    if a.whole: xf = 0
    print(f'  loop {i + s0}..{j + s0} ({L} frames, {L / 24:.2f} s), cost {cost:.5f}', flush=True)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    seq = []
    for t in range(i, j):
        rgb, al = N_rgb[t].astype(np.float32), N_a[t]
        if t >= j - xf:
            u = t - L; w = (t - (j - xf) + 1) / (xf + 1); w = w * w * (3 - 2 * w)
            rgb, fab, fba = VP.blend_morph(N_rgb[t], N_rgb[u], w, dis)
            al = (1 - w) * VP.warp(N_a[t], fab * w) + w * VP.warp(N_a[u], fba * (1 - w))
        seq.append((np.clip(rgb, 0, 255).astype(np.uint8), np.clip(al, 0, 1)))
    if a.qc:
        ks = np.linspace(0, len(seq) - 1, 8).astype(int)
        strip = np.concatenate([np.dstack([s[0] * s[1][..., None] + np.array([70, 70, 74]) * (1 - s[1][..., None])]).astype(np.uint8) for s in (seq[k] for k in ks)], 1)
        cv2.imwrite(a.qc, cv2.cvtColor(cv2.resize(strip, (strip.shape[1] // 2, strip.shape[0] // 2)), cv2.COLOR_RGB2BGR))
    meta = {'name': a.name, 'src': os.path.basename(a.src), 'loop_src': [int(i + s0), int(j + s0)], 'frames': L, 'fps': 24, 'steps': 2, 'cost': round(float(cost), 5),
            'top': round(float((Bref - Href) / H0), 4), 'foot': round(float(Bref / H0), 4), 'cx': 0.5}
    if a.no_export: print(json.dumps(meta)); return
    W, Hh = W0, H0
    if a.height < H0: Hh = a.height; W = int(round(W0 * Hh / H0 / 2)) * 2
    tmp = os.path.join(VP.CACHE, a.name + '_seq'); os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    xx = np.arange(W0, dtype=np.float32) / W0; xr = np.clip(np.minimum(xx, 1 - xx) / 0.03, 0, 1)[None, :]
    for k, (rgb, al) in enumerate(seq):
        al = al * xr; F = VP.decontaminate(rgb.astype(np.float32), al)
        Fs = cv2.resize(F, (W, Hh), interpolation=cv2.INTER_AREA); As = np.clip(cv2.resize(al, (W, Hh), interpolation=cv2.INTER_AREA), 0, 1)
        rgba = np.dstack([Fs * 255, As * 255]).round().astype(np.uint8)
        cv2.imwrite(os.path.join(tmp, f'{k:04d}.png'), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        stack = np.concatenate([Fs * 255, np.repeat(As[..., None] * 255, 3, -1)], 0).round().astype(np.uint8)
        cv2.imwrite(os.path.join(tmp, f's{k:04d}.png'), cv2.cvtColor(stack, cv2.COLOR_RGB2BGR))
        if k == 0: cv2.imwrite(os.path.join(VP.OUT, a.name + '.png'), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    webm = os.path.join(VP.OUT, a.name + '.webm'); plog = os.path.join(tmp, 'vp9pass')
    vp9 = ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0', '-crf', str(a.crf), '-b:v', '0', '-g', '12', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '1', '-passlogfile', plog]
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, '%04d.png')] + vp9 + ['-pass', '1', '-f', 'webm', os.devnull], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, '%04d.png')] + vp9 + ['-pass', '2', webm], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', os.path.join(tmp, 's%04d.png'), '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                    '-crf', '18', '-g', '12', '-movflags', '+faststart', '-an', os.path.join(VP.OUT, a.name + '_stack.mp4')], check=True)
    json.dump(meta, open(os.path.join(VP.OUT, a.name + '.json'), 'w'))
    print(json.dumps(meta), flush=True)

if __name__ == '__main__':
    main()
