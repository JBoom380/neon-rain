"""Paint a slow blink into Vela's idle loop (the rig has no eyelids). The lids are painted from the eye keypoints:
skin sampled just below each eye fills the eye down to the lid line, a soft dark lash line closes it.
Half-closed frames stop the lid halfway. Restores from a clean copy first, so it can be re-run.
Usage: vw_blink.py GUIDEDIR FINALDIR CLEANDIR --frames 10,11,12   (closure per frame: 0.5,1,0.5)"""
import os, json, argparse, shutil
import numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument('guides'); ap.add_argument('final'); ap.add_argument('clean')
ap.add_argument('--frames', default='10,11,12'); ap.add_argument('--amount', default='0.55,1,0.55')
a = ap.parse_args()
gd = os.path.join(a.guides, 'idle', 'a000'); fd = os.path.join(a.final, 'idle', 'a000')
kp = json.load(open(os.path.join(gd, 'kp.json')))
for i, amt in zip([int(x) for x in a.frames.split(',')], [float(x) for x in a.amount.split(',')]):
    src = os.path.join(a.clean, 'cut_%02d.png' % i); dst = os.path.join(fd, 'cut_%02d.png' % i)
    im = cv2.imread(src, cv2.IMREAD_UNCHANGED).astype(np.float32)
    e = kp['%02d' % i]
    for k in (14, 15):
        if not e[k]: continue
        x, y = e[k]; rx, ry = 9.0, 5.5
        skin = np.median(im[int(y + 9):int(y + 13), int(x - 5):int(x + 5), :3].reshape(-1, 3), axis=0)
        lid = np.zeros(im.shape[:2], np.float32)
        top, bot = y - ry, y - ry + 2 * ry * amt  # the lid comes down from above the eye
        cv2.ellipse(lid, (int(round(x)), int(round(y))), (int(rx), int(ry)), 0, 0, 360, 1.0, -1)
        rows = np.arange(im.shape[0], dtype=np.float32)[:, None]
        lid *= np.clip((bot - rows) / 1.5 + 0.5, 0, 1)
        lid = cv2.GaussianBlur(lid, (5, 5), 1.0)
        im[..., :3] = im[..., :3] * (1 - lid[..., None]) + skin * lid[..., None]
        lash = np.zeros(im.shape[:2], np.float32)
        ly = int(round(bot)); cv2.ellipse(lash, (int(round(x)), ly - 2), (int(rx) - 1, 2), 0, 15, 165, 1.0, 1)
        lash = cv2.GaussianBlur(lash, (3, 3), 0.8) * (0.7 if amt >= 1 else 0.35)
        im[..., :3] = im[..., :3] * (1 - lash[..., None]) + np.array([30, 24, 36], np.float32) * lash[..., None]
    cv2.imwrite(dst, np.clip(im, 0, 255).astype(np.uint8))
print('blink painted into', a.frames)
