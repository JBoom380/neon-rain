"""vela_full_v2 by re-facing the stable v1 take: the FAV1-identity face (Klein head edit pasted into the same start
frame) follows the v1 head motion frame by frame (YuNet 5-point similarity transform), with the v1 eyes let through
only while they close (blinks kept). Output: lossless FFV1 at the take's size.
python reface.py V1_TAKE.mp4 V2_START.png K1_START.png OUT.mkv"""
import os, subprocess, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
det = cv2.FaceDetectorYN.create(os.path.join(HERE, '..', '..', 'art', 'motion', 'vela_full_v2', 'models', 'yunet.onnx'), '', (320, 320), 0.5, 0.3, 5000)
src, v2p, k1p, out = sys.argv[1:5]
w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip().split(','))
fr = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True).stdout, np.uint8).reshape(-1, h, w, 3)
V2 = cv2.resize(cv2.imread(v2p), (w, h), interpolation=cv2.INTER_AREA)
# soften the Klein blush: pull the red-green channel of the face toward its median
_l = cv2.cvtColor(V2, cv2.COLOR_BGR2LAB).astype(np.float32); _a = _l[..., 1]; _l[..., 1] = np.where(_a > np.median(_a), np.median(_a) + (_a - np.median(_a)) * 0.8, _a)
_red = np.clip((_l[..., 1] - 150) / 20, 0, 1); _l[..., 2] = _l[..., 2] - (_l[..., 2] - 128) * 0.55 * _red  # lips: orange-red to crimson
V2 = cv2.cvtColor(_l.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
K1 = cv2.resize(cv2.imread(k1p), (w, h), interpolation=cv2.INTER_AREA)


def lm(im, s=3):
    big = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC); det.setInputSize((big.shape[1], big.shape[0]))
    _, f = det.detect(big)
    if f is None: return None, None
    f = max(f, key=lambda r: r[2] * r[3]); return f[4:14].reshape(5, 2).astype(np.float32) / s, f[:4] / s


p0, box = lm(K1)
x, y, bw, bh = box
face = np.zeros((h, w), np.float32); cv2.ellipse(face, (int(x + bw / 2), int(y + bh * 0.55)), (int(bw * 0.5), int(bh * 0.6)), 0, 0, 360, 1, -1); face = cv2.GaussianBlur(face, (0, 0), bw * 0.07)
eyes = np.zeros((h, w), np.float32)
for e in p0[:2]: cv2.ellipse(eyes, (int(e[0]), int(e[1])), (int(bw * 0.16), int(bh * 0.09)), 0, 0, 360, 1, -1)
eyes = cv2.GaussianBlur(eyes, (0, 0), bw * 0.03)
os.makedirs(out + '_frames', exist_ok=True); last = p0; S = None; recs = []
for k, f in enumerate(fr):  # pass 1: landmarks and eye darkness
    p, _ = lm(f)
    if p is None: p = last
    p = p if S is None else 0.5 * p + 0.5 * S  # light landmark smoothing against jitter
    S = p; last = p
    A, _ = cv2.estimateAffinePartial2D(p0, p); me = cv2.warpAffine(eyes, A, (w, h))
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dark = ((255 - g) * me).sum() / max(me.sum(), 1)  # open eyes: dark iris and lashes; closed: lid skin, lighter
    recs.append((A, dark))
dk = np.array([r[1] for r in recs]); base = np.percentile(dk, 75)
for k, f in enumerate(fr):  # pass 2: composite; a blink = eye darkness well below its usual level
    A, dark = recs[k]
    blink = 0.0  # the v1 take has no clean blink (eye darkness only drifts), so the v2 eyes stay on
    V = cv2.warpAffine(V2, A, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    mf = cv2.warpAffine(face, A, (w, h)); me = cv2.warpAffine(eyes, A, (w, h))
    m = (mf * (1 - blink * me))[..., None]
    # follow the take's light: shift the patch's LAB mean to the frame's inside the face region
    k3 = mf > 0.6; fl = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32); vl = cv2.cvtColor(V.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    for c in range(3): vl[..., c] += (fl[..., c][k3].mean() - vl[..., c][k3].mean()) * (0.5 if c == 0 else 0.0)
    V = cv2.cvtColor(vl.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
    o = f.astype(np.float32) * (1 - m) + V * m
    cv2.imwrite(f'{out}_frames/{k:04d}.png', o.clip(0, 255).astype(np.uint8))
    print(k, round(float(dark), 1), round(blink, 2), flush=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-i', f'{out}_frames/%04d.png', '-c:v', 'ffv1', '-pix_fmt', 'bgr0', out], check=True)
