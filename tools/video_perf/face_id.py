"""Face identity check against FAV1 (OpenCV YuNet detector + SFace recogniser, opencv_zoo, Apache-2.0 / MIT).
python face_id.py FILE [FILE ...]          images or videos; videos are sampled every 6th frame
Prints cosine similarity to FAV1 (SFace: >= 0.363 = same person) per image, or min / mean / max over a video."""
import os, subprocess, sys, json
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.normpath(os.path.join(HERE, '..', '..', 'art', 'vela_favorites', 'FAV1_blonde_seed52.png'))
det = cv2.FaceDetectorYN.create(os.path.join(HERE, 'models', 'yunet.onnx'), '', (320, 320), 0.6, 0.3, 5000)
rec = cv2.FaceRecognizerSF.create(os.path.join(HERE, 'models', 'sface.onnx'), '')


def embed(bgr):
    s = max(1.0, 900 / max(bgr.shape[:2]))  # small faces in full-length frames: enlarge before detection
    im = cv2.resize(bgr, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC) if s > 1 else bgr
    det.setInputSize((im.shape[1], im.shape[0]))
    _, faces = det.detect(im)
    if faces is None or not len(faces): return None
    f = max(faces, key=lambda r: r[2] * r[3])
    return rec.feature(rec.alignCrop(im, f))


ref = embed(cv2.imread(REF))
sim = lambda e: float(rec.match(ref, e, cv2.FaceRecognizerSF_FR_COSINE))


def frames(path):
    w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip().split(','))
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


out = {}
for p in sys.argv[1:]:
    if p.lower().endswith(('.mp4', '.mkv', '.webm', '.mov')):
        fr = frames(p)
        ss = [sim(e) for e in (embed(np.ascontiguousarray(f[:f.shape[0] // 2] if '_stack' in p else f)) for f in fr[::6]) if e is not None]
        out[os.path.basename(p)] = {'n': len(ss), 'min': round(min(ss), 3), 'mean': round(float(np.mean(ss)), 3), 'max': round(max(ss), 3)} if ss else 'no face'
    else:
        e = embed(cv2.imread(p)); out[os.path.basename(p)] = round(sim(e), 3) if e is not None else 'no face'
print(json.dumps(out, indent=1))
