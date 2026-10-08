"""Draw OpenPose (COCO-18) skeleton images from vw_render kp.json, controlnet_aux style.
Usage: vw_pose.py DIR [DIR ...]  -> DIR/pose_NN.png (512x1024)"""
import sys, os, json, math
import numpy as np, cv2
LIMBS = [[2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10], [10, 11], [2, 12], [12, 13], [13, 14], [2, 1], [1, 15], [15, 17], [1, 16], [16, 18]]
COL = [[255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0], [170, 255, 0], [85, 255, 0], [0, 255, 0], [0, 255, 85], [0, 255, 170], [0, 255, 255],
       [0, 170, 255], [0, 85, 255], [0, 0, 255], [85, 0, 255], [170, 0, 255], [255, 0, 255], [255, 0, 170], [255, 0, 85]]
def draw(kp, W=512, H=1024, sw=5):
    c = np.zeros((H, W, 3), np.uint8)
    for i, (a, b) in enumerate(LIMBS):
        p, q = kp[a - 1], kp[b - 1]
        if p is None or q is None: continue
        X = [p[1], q[1]]; Y = [p[0], q[0]]; mx, my = np.mean(X), np.mean(Y)
        L = math.hypot(X[0] - X[1], Y[0] - Y[1]); ang = math.degrees(math.atan2(X[0] - X[1], Y[0] - Y[1]))
        poly = cv2.ellipse2Poly((int(my), int(mx)), (int(L / 2), sw), int(ang), 0, 360, 1)
        cv2.fillConvexPoly(c, poly, [int(x * 0.6) for x in COL[i]])
    for i, p in enumerate(kp):
        if p is None: continue
        cv2.circle(c, (int(p[0]), int(p[1])), 5, COL[i], -1)
    return c
if __name__ == '__main__':
    for d in sys.argv[1:]:
        kp = json.load(open(os.path.join(d, 'kp.json')))
        for k, v in kp.items(): cv2.imwrite(os.path.join(d, 'pose_%s.png' % k), cv2.cvtColor(draw(v), cv2.COLOR_RGB2BGR))
        print(d, len(kp))
