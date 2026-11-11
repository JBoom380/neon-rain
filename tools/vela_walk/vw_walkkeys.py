"""Stride keyframes for the filmed front walk: FLUX.2 Klein, image 1 = mocap pose (front walk frame in vela_full framing),
image 2 = the vela_full start frame (identity, outfit, light). Output 768x1344 keys/key_PP_sS.png.
Usage: vw_walkkeys.py KEYDIR --phases 0,4,8,12 --seeds 5"""
import os, sys, argparse
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vw_paint as VP
from vw_klein import klein
IDENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'art', 'motion', 'vela', 'keys', 'ident_head.png')  # head crop of vp_vela_full
P = ("Edit the first image. Keep its pose exactly: the same walking stride, the same legs and feet, the same hip sway, the same arms and hands, "
     "the same body position, size and full-length framing. Turn the figure into a photoreal slim young woman whose face and hair are exactly those of "
     "the woman in the second image: the same face, golden blonde 1940s pin curls, makeup and red lips. Warm skin. She wears a glossy black satin halter top "
     "with a deep V neckline, a tight red satin knee-length pencil skirt, long black satin opera gloves and black high heels, and holds a long black "
     "cigarette holder in her raised gloved hand. Plain dark grey studio background, soft studio light. Photoreal, sharp focus, classy.")
import vw_klein as VK
VK.P = P
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('keys'); ap.add_argument('--phases', default='0,4,8,12'); ap.add_argument('--seeds', default='5')
    a = ap.parse_args()
    ident = VP.upload(Image.open(IDENT).convert('RGB'), 'vw_ident_full.png')
    for s in [int(x) for x in a.seeds.split(',')]:
        for ph in [int(x) for x in a.phases.split(',')]:
            out = os.path.join(a.keys, 'key_%02d_s%d.png' % (ph, s))
            if os.path.exists(out): continue
            pose = VP.upload(Image.open(os.path.join(a.keys, 'pose_%02d.png' % ph)).convert('RGB'), 'vw_pose_full_%02d.png' % ph)
            img, dt = klein(pose, ident, s, 768, 1344)
            img.save(out); print('[key]', ph, s, '%.0fs' % dt, flush=True)
