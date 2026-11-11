"""Score LTX walk takes: leg motion (does she walk), face drift (does she stay FAV1), dolly drift. Usage: vw_takeqc.py TAKE.mp4 ..."""
import sys, os, subprocess
import numpy as np, cv2
def frames(p):
    pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', p], capture_output=True, text=True)
    w, h = map(int, pr.stdout.strip().split(','))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
for p in sys.argv[1:]:
    F = frames(p); n, H, W = F.shape
    legs = F[:, int(H * 0.62):int(H * 0.97), int(W * 0.2):int(W * 0.8)]
    lm = np.abs(np.diff(legs, axis=0)).mean((1, 2))
    # leg motion per half of the take; alternation period from the autocorrelation of a left-right leg signal
    lr = legs[:, :, :legs.shape[2] // 2].mean((1, 2)) - legs[:, :, legs.shape[2] // 2:].mean((1, 2))
    x = lr[20:] - lr[20:].mean(); ac = np.correlate(x, x, 'full')[len(x) - 1:]; ac /= ac[0] + 1e-6
    per = 12 + int(np.argmax(ac[12:48])) if len(ac) > 48 else -1
    face0 = F[0, int(H * 0.02):int(H * 0.2), int(W * 0.3):int(W * 0.7)]
    def corr(a, b): a = a - a.mean(); b = b - b.mean(); return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-6))
    fd = []
    for t in range(0, n, 8):  # best match of the face anywhere near the top (she may shift)
        best = -1
        for dy in range(-30, 31, 6):
            for dx in range(-30, 31, 6):
                y0, x0 = int(H * 0.02) + dy, int(W * 0.3) + dx
                if y0 < 0 or x0 < 0: continue
                c = F[t, y0:y0 + face0.shape[0], x0:x0 + face0.shape[1]]
                if c.shape == face0.shape: best = max(best, corr(face0, c))
        fd.append(best)
    print(f'{os.path.basename(p)}: legs first/second half {lm[:n//2].mean():.2f}/{lm[n//2:].mean():.2f}  gait period {per} fr (ac {ac[per]:.2f})  face corr min {min(fd):.2f} mean {np.mean(fd):.2f}')
