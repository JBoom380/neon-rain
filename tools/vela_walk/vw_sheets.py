"""Assemble Vela's cut-out frames into game sprite sheets (webp) and src/anim_data.js.
Usage: vw_sheets.py CUTDIR MOTION.json ASSETDIR [--walk 256] [--stop 256] [--idle 320] [--pose 320]"""
import os, sys, json, argparse
from PIL import Image
ap = argparse.ArgumentParser()
ap.add_argument('cut'); ap.add_argument('motion'); ap.add_argument('assets')
ap.add_argument('--walk', type=int, default=256); ap.add_argument('--stop', type=int, default=256)
ap.add_argument('--idle', type=int, default=320); ap.add_argument('--pose', type=int, default=320)
ap.add_argument('--q', type=int, default=88)
a = ap.parse_args()
J = json.load(open(a.motion))
ANG = [0, 45, 90, 135, 180, 225, 270, 315]
CUTS = a.cut.split(',')  # priority list: the first directory holding a complete sequence wins
def frames(sub, n):
    for c in CUTS:
        if all(os.path.exists(os.path.join(c, sub, 'cut_%02d.png' % i)) for i in range(n)):
            print('  ', sub, '<-', c); return [Image.open(os.path.join(c, sub, 'cut_%02d.png' % i)).convert('RGBA') for i in range(n)]
    raise FileNotFoundError(sub)
def build(ims, cw, cols, name):
    ch = cw * 2; rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGBA', (cw * cols, ch * rows), (0, 0, 0, 0))
    for i, im in enumerate(ims):
        sh.paste(im.resize((cw, ch), Image.LANCZOS), ((i % cols) * cw, (i // cols) * ch))
    p = os.path.join(a.assets, name); sh.save(p, 'WEBP', quality=a.q, method=4)
    print(name, sh.size, round(os.path.getsize(p) / 1024), 'KB')
    return {'sheet': name, 'cols': cols, 'rows': rows}
nf = J['walk_frames']
out = {'world': [1.0, 2.0], 'centerY': 0.97,
       'walk': {'frames': nf, 'cycle': J['cycle_len'], 'speed': J['natural_speed'], 'plants': J['plants'], 'angles': {}},
       'stop': {'frames': J['stop_frames'], 'fps': J['stop_fps'], 'root': J['stop_root_fwd_left'], 'turn': J['turn_deg'],
                'phase': J['stop_start_phase'], 'heels': J['stop_heels']},
       'idle': {'frames': J['idle_frames'], 'fps': J['idle_fps']}, 'pose': {'index': {}}}
for az in ANG:
    out['walk']['angles'][str(az)] = build(frames('walk/a%03d' % az, nf), a.walk, 4, 'vela_walk_a%03d.webp' % az)
if all(any(os.path.exists(os.path.join(c, 'stop/a%03d' % az, 'cut_%02d.png' % (J['stop_frames'] - 1))) for c in CUTS) for az in ANG):
    out['stop']['angles'] = {str(az): build(frames('stop/a%03d' % az, J['stop_frames']), a.stop, 6, 'vela_stop_a%03d.webp' % az) for az in ANG}
else:
    out['stop'].update(build(frames('stop/a000', J['stop_frames']), a.stop, 6, 'vela_stop.webp'))
out['idle'].update(build(frames('idle/a000', J['idle_frames']), a.idle, 8, 'vela_idlew.webp'))
pims = []
for i, az in enumerate(ANG):
    pims.append(frames('pose/a%03d' % az, 1)[0]); out['pose']['index'][str(az)] = i
out['pose'].update(build(pims, a.pose, 4, 'vela_pose.webp'))
js = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'anim_data.js')
HDR = "// NEON RAIN: Vela's painted walk animation table (written by tools/vela_walk/vw_sheets.py). null = not built yet: the old billboard is used."
open(js, 'w', encoding='utf-8').write(HDR + chr(10) + 'NR.ANIM = NR.ANIM || {};' + chr(10) + 'NR.ANIM.vela = ' + json.dumps(out, separators=(',', ':')) + ';' + chr(10))
print('wrote', os.path.normpath(js))
