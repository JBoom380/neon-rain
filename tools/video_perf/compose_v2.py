"""Paste the Klein head edit (FAV1 identity) into the full-length Klein frame, aligned by YuNet landmarks.
python compose_v2.py HEAD.png OUT.png"""
import sys, os, numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
det = cv2.FaceDetectorYN.create(os.path.join(HERE, '..', '..', 'art', 'motion', 'vela_full_v2', 'models', 'yunet.onnx'), '', (320, 320), 0.6, 0.3, 5000)
def lm(im):
    det.setInputSize((im.shape[1], im.shape[0])); _, f = det.detect(im); f = max(f, key=lambda r: r[2] * r[3]); return f[4:14].reshape(5, 2).astype(np.float32), f
full = cv2.imread('C:/Users/John/Documents/ComfyUI_Output/vperf/vela_full_k1_00001_.png')
base = cv2.imread('E:/ComfyUI_windows_portable/ComfyUI/input/vp_k1_head.png')  # crop (233,60)-(533,360) of full, at 1024
head = cv2.imread(sys.argv[1])
pb, fb = lm(base); ph, _ = lm(head)
A, _ = cv2.estimateAffinePartial2D(ph, pb)
hw = cv2.warpAffine(head, A, (1024, 1024), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
# colour match the warped face to the base inside the face box
x, y, w, h = fb[:4]; m = np.zeros((1024, 1024), np.float32)
cv2.ellipse(m, (int(x + w / 2), int(y + h * 0.52)), (int(w * 0.52), int(h * 0.62)), 0, 0, 360, 1, -1); m = cv2.GaussianBlur(m, (0, 0), w * 0.06)
bl = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype(np.float32); hl = cv2.cvtColor(hw.clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32); k = m > 0.5
for c in range(3): hl[..., c] = (hl[..., c] - hl[..., c][k].mean()) * (bl[..., c][k].std() / (hl[..., c][k].std() + 1e-6)) * 0.5 + (hl[..., c] - hl[..., c][k].mean()) * 0.5 + bl[..., c][k].mean()
hw = cv2.cvtColor(hl.clip(0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
mixed = base * (1 - m[..., None]) + hw * m[..., None]
small = cv2.resize(mixed, (300, 300), interpolation=cv2.INTER_AREA); ms = cv2.resize(m, (300, 300), interpolation=cv2.INTER_AREA)[..., None]
out = full.astype(np.float32); out[60:360, 233:533] = out[60:360, 233:533] * (1 - ms) + small * ms
cv2.imwrite(sys.argv[2], out.clip(0, 255).astype(np.uint8)); print('ok', sys.argv[2])
