"""NEON RAIN environment pass: the Blue Orchid nightclub (title backdrop, SCAN, interrogation, gunfight), built, lit and
baked in Blender, exported to assets/models/env_club.glb.
Usage: blender -b --python tools/env/club.py -- [--preview] [--bake] [--samples N]
Layout (game coords) keeps the grey-box footprints: room x -8..8, z -24..1.1, ceiling 4.2; stage x -7..4, z -24..-18,
0.6 high; bar on the left wall; leather booths on the right wall; dressing room x 4.6..8, z -24..-15.1."""
import sys, json, math, pathlib, random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib, envlib
importlib.reload(envlib)
from envlib import *

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(ARGS[ARGS.index('--samples') + 1]) if '--samples' in ARGS else 768
OUT = ROOT / "assets" / "models" / "env_club.glb"
HW, Z0, Z1, RH = 8.0, 1.1, -24.0, 4.2
rnd = random.Random(5)

reset(SAMPLES)
world_color((0.002, 0.0016, 0.0014), 1.0)

M = dict(
    carpet=pbr('carpet', 'dirty_carpet', tint=(0.62, 0.14, 0.1), normal=0.4),
    wains=pbr('wains', 'dark_wooden_planks', tint=(0.5, 0.36, 0.28), normal=0.6),
    wall=pbr('wall', 'plastered_wall_04', tint=(0.32, 0.38, 0.33)),
    ceil=pbr('ceil', 'white_plaster_02', tint=(0.22, 0.2, 0.19)),
    trim=pbr('trim', 'black_painted_planks', tint=(0.5, 0.42, 0.3)),
    stage=pbr('stage', 'herringbone_parquet', tint=(0.55, 0.42, 0.32), rough=0.3),
    stagefront=pbr('stagefront', 'dark_wooden_planks', tint=(0.4, 0.3, 0.24)),
    velvet=pbr('velvet', 'velour_velvet', tint=(0.75, 0.18, 0.16), normal=0.8),
    leather=pbr('leather', 'leather_red_02', tint=(0.85, 0.3, 0.26), rough=0.4),
    marble=pbr('marble', 'marble_01', tint=(0.35, 0.3, 0.27), rough=0.15),
    barwood=pbr('barwood', 'black_walnut_veneer_01', tint=(0.45, 0.3, 0.22), rough=0.3),
    brass=flat('brass', (0.62, 0.42, 0.16), rough=0.3, metal=1.0),
    chrome=flat('chrome', (0.5, 0.48, 0.45), rough=0.2, metal=1.0),
    black=flat('black', (0.012, 0.011, 0.01), rough=0.3),
    ivory=flat('ivory', (0.75, 0.7, 0.6), rough=0.3),
    shade=flat('shade', (0.85, 0.6, 0.35), emit=(1.0, 0.62, 0.3), emit_strength=1.6),
    bulb=flat('bulb', (1, 0.9, 0.7), emit=kelvin(2700), emit_strength=25.0),
    bottles=flat('bottles', (0.25, 0.12, 0.04), rough=0.1),
    bottles2=flat('bottles2', (0.08, 0.16, 0.06), rough=0.1),
    mirror=flat('mirror', (0.5, 0.48, 0.45), rough=0.05, metal=1.0),
    cloth=flat('cloth', (0.6, 0.55, 0.48), rough=0.8),
)
NEONM = {}
DG, DL = deco_gold(), deco_lacquer()


def neon_mat(col, name, strength=18.0):
    if name not in NEONM:
        NEONM[name] = flat('NEON_' + name, col, rough=0.2, emit=col, emit_strength=strength)
    return NEONM[name]


SHELL, PROPS, NEON, COL = [], [], [], []


def collide(lo, hi, cover=False, tag='', step=False):
    COL.append(dict(min=list(lo), max=list(hi), cover=cover, tag=tag, step=step))


# ---------------------------------------------------------------- shell
SHELL.append(box('floor', (-HW, -0.1, Z1), (HW, 0, Z0), M['carpet'], tile=1.6, faces=['+y']))
SHELL.append(box('ceil', (-HW, RH, Z1), (HW, RH + 0.1, Z0), M['ceil'], tile=2.4, faces=['-y']))
WS = 1.2


def wallz(z, side, x0, x1):
    t = -0.2 if side == '+z' else 0.2
    a, b = (z + t, z) if t < 0 else (z, z + t)
    SHELL.append(box('wl', (x0, 0, a), (x1, WS, b), M['wains'], tile=1.2, faces=[side], rot90=True))
    SHELL.append(box('wu', (x0, WS, a), (x1, RH, b), M['wall'], tile=2.0, faces=[side]))


def wallx(x, side, z0, z1):
    t = -0.2 if side == '+x' else 0.2
    a, b = (x + t, x) if t < 0 else (x, x + t)
    SHELL.append(box('wl', (a, 0, z0), (b, WS, z1), M['wains'], tile=1.2, faces=[side], rot90=True))
    SHELL.append(box('wu', (a, WS, z0), (b, RH, z1), M['wall'], tile=2.0, faces=[side]))


wallx(-HW, '+x', Z1, Z0); wallx(HW, '-x', Z1, Z0); wallz(Z0, '-z', -HW, HW); wallz(Z1, '+z', -HW, HW)
for c in (((-HW - 0.4, 0, Z1 - 0.4), (-HW, RH, Z0 + 0.4)), ((HW, 0, Z1 - 0.4), (HW + 0.4, RH, Z0 + 0.4)),
          ((-HW, 0, Z0), (HW, RH, Z0 + 0.4)), ((-HW, 0, Z1 - 0.4), (HW, RH, Z1))):
    collide(*c, tag='wall')
# trim: chair rail, baseboard, crown
for (lo, hi) in (((-HW, WS - 0.03, Z1), (-HW + 0.04, WS + 0.04, Z0)), ((HW - 0.04, WS - 0.03, Z1), (HW, WS + 0.04, Z0)),
                 ((-HW, WS - 0.03, Z0 - 0.04), (HW, WS + 0.04, Z0)), ((-HW, RH - 0.14, Z1), (-HW + 0.1, RH, Z0)),
                 ((HW - 0.1, RH - 0.14, Z1), (HW, RH, Z0)), ((-HW, RH - 0.14, Z0 - 0.1), (HW, RH, Z0))):
    SHELL.append(box('trim', lo, hi, M['trim'], bevel=0.008))
# ceiling beams (coffers)
for z in range(-22, 1, 4):
    PROPS.append(box('beam', (-HW, RH - 0.28, z - 0.15), (HW, RH, z + 0.15), M['trim'], tile=1.0, bevel=0.01))
# entrance doors (front) and kitchen door (left, back)
for x0, x1 in ((-0.9, -0.02), (0.02, 0.9)):
    PROPS.append(box('fdoor', (x0, 0, Z0 - 0.05), (x1, 2.4, Z0), DL, bevel=0.01))
for x in (-0.46, 0.46):
    PROPS += deco_porthole('fport', (x, 1.55, Z0 - 0.07), 0.17)
    PROPS += deco_stepped_frame('fpanel', 'z', (x, 0.6, Z0 - 0.06), 0.62, 0.7, t=0.025, steps=1)
PROPS.append(box('fdoorc', (-1.0, 2.4, Z0 - 0.08), (1.0, 2.55, Z0), M['brass'], bevel=0.01))
for x in (-0.15, 0.15):
    PROPS.append(box('fdoorh', (x - 0.02, 0.9, Z0 - 0.09), (x + 0.02, 1.4, Z0 - 0.05), M['brass']))
PROPS.append(box('kdoor', (-HW, 0, -16.6), (-HW + 0.05, 2.4, -15.4), M['barwood'], tile=0.9, bevel=0.01))
PROPS += deco_porthole('kport', (-HW + 0.07, 1.6, -16.0), 0.15, plane='x')

# ---------------------------------------------------------------- stage, curtain, piano, mic
PROPS.append(box('stage', (-7, 0, -24), (4, 0.6, -18), M['stagefront'], tile=0.9, bevel=0.01))
PROPS.append(box('stagetop', (-7, 0.6, -24), (4, 0.62, -18), M['stage'], tile=1.4))
PROPS.append(box('stagelip', (-7.05, 0.56, -18.05), (4.05, 0.64, -17.95), M['brass'], bevel=0.01))
collide((-7, 0, -24), (4, 0.6, -18), tag='stage', step=True)
for x in (-5.5, -3.0, 0.0, 2.5):   # footlights
    PROPS.append(lathe('foot', [(0, 0), (0.08, 0), (0.06, 0.08), (0, 0.08)], (x, 0.62, -18.2), M['brass'], seg=12))
# curtain: pleated velvet, gathered at the sides
bm = bmesh.new()
cols, rows = 90, 12
verts = []
for j in range(rows + 1):
    y = 0.62 + (RH - 0.25 - 0.62) * j / rows
    row = []
    for i in range(cols + 1):
        x = -7.0 + 11.0 * i / cols
        z = -23.7 + 0.09 * math.sin(i * math.pi / 1.5) + 0.06 * math.sin(i * 0.37)
        row.append(bm.verts.new(G(x, y, z)))
    verts.append(row)
for j in range(rows):
    for i in range(cols):
        bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
cur = mesh_obj('curtain', bm, M['velvet']); box_uv(cur, 1.6)
for p in cur.data.polygons:
    p.use_smooth = True
PROPS.append(cur)
PROPS.append(box('valance', (-7.2, RH - 0.7, -23.75), (4.2, RH - 0.15, -23.45), M['velvet'], tile=1.2, bevel=0.03))
for x in (-7.3, 4.0):
    PROPS.append(box('proscenium', (x, 0.6, -23.8), (x + 0.3, RH, -23.3), DL, bevel=0.01))
    for k in range(3):   # stepped crown on the pier
        PROPS.append(box('prostep', (x - 0.03 - 0.03 * k, RH - 0.5 - 0.12 * k, -23.82), (x + 0.33 + 0.03 * k, RH - 0.42 - 0.12 * k, -23.26 + 0.02 * k), DG, bevel=0.004))
    for fx in (0.05, 0.15, 0.25):
        PROPS.append(cyl('proflute', (x + fx, 0.62, -23.28), 0.018, RH - 0.95, DG, seg=8))
# upright piano (stage left)
PX, PZ = -5.2, -21.5
PROPS.append(box('piano', (PX - 0.8, 0.62, PZ - 0.35), (PX + 0.8, 1.9, PZ + 0.0), M['black'], bevel=0.02))
PROPS.append(box('pianokb', (PX - 0.75, 1.32, PZ), (PX + 0.75, 1.36, PZ + 0.3), M['ivory']))
for i in range(36):
    x = PX - 0.72 + i * 0.041
    if i % 7 not in (2, 6):
        PROPS.append(box('blackkey', (x + 0.025, 1.36, PZ + 0.0), (x + 0.042, 1.38, PZ + 0.18), M['black']))
PROPS.append(box('pianolid', (PX - 0.8, 1.36, PZ - 0.05), (PX + 0.8, 1.6, PZ + 0.02), M['black'], bevel=0.01))
PROPS.append(box('pianobench', (PX - 0.45, 0.62, PZ + 0.55), (PX + 0.45, 1.1, PZ + 0.9), M['black'], bevel=0.02))
collide((PX - 0.8, 0, PZ - 0.4), (PX + 0.8, 1.6, PZ + 0.6), cover=True, tag='piano')
# 1940s ribbon microphone on a chrome stand
MX, MZ = -1.5, -19.5
PROPS.append(lathe('micbase', [(0, 0), (0.17, 0), (0.17, 0.02), (0.05, 0.05), (0, 0.05)], (MX, 0.62, MZ), M['chrome']))
PROPS.append(cyl('micpole', (MX, 0.66, MZ), 0.012, 1.0, M['chrome'], seg=10))
PROPS.append(box('micbody', (MX - 0.05, 1.66, MZ - 0.03), (MX + 0.05, 1.86, MZ + 0.03), M['chrome'], bevel=0.02))
PROPS.append(box('micgrille', (MX - 0.045, 1.68, MZ + 0.03), (MX + 0.045, 1.84, MZ + 0.035), M['black']))
collide((MX - 0.12, 0.6, MZ - 0.12), (MX + 0.12, 2.0, MZ + 0.12), tag='mic')

# neon over the stage: script lettering + an orchid
nb = neon_mat(NEON_BLUE, 'blue', 22.0); nt = neon_mat(NEON_TEAL, 'teal', 18.0); npk = neon_mat((1.0, 0.1, 0.45), 'pink', 16.0)
NEON.append(neon_text('n_title', 'The Blue Orchid', (-1.5, 3.55, -23.34), 0, 0.82, nb, depth=0.026, res=2,
                      font='C:/Windows/Fonts/georgiaz.ttf'))
for k in range(5):   # orchid petals
    a = math.radians(90 + k * 72)
    cx, cy = 2.35 + 0.0, 3.6
    pts = []
    for t in range(13):
        u = t / 12 * math.pi
        r = 0.32 * math.sin(u)
        ang = a + (u - math.pi / 2) * 0.55
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang), -23.36))
    NEON.append(tube_path('petal', pts, 0.011, npk))
NEON.append(tube_path('stem', [(2.35, 3.6, -23.36), (2.25, 3.1, -23.36), (2.4, 2.7, -23.36)], 0.01, nt))
PROPS += deco_sunburst('arch', (-1.5, 0.62, -23.36), 2.75, 3.3, n=45, thick=0.02, hub=False, w=(0.035, 0.05))
light('AREA', (-1.5, 3.4, -22.9), NEON_BLUE, 80, gaim=(-1.5, 0.6, -20.5), size=(5.0, 0.6), name='neon_blue')
light('AREA', (2.35, 3.4, -22.9), (1.0, 0.1, 0.45), 50, gaim=(2.4, 1.5, -18.0), size=(0.7, 0.7), name='neon_pink')
# a red neon over the bar
nr = neon_mat(NEON_RED, 'red', 18.0)
NEON.append(neon_text('n_cocktails', 'COCKTAILS', (-7.86, 3.15, -9.0), 90, 0.42, nr, depth=0.012, res=2))
light('AREA', (-7.6, 3.15, -9.0), NEON_RED, 90, gaim=(-3.0, 2.0, -9.0), size=(0.4, 2.4), name='neon_bar')

# ---------------------------------------------------------------- the bar (left wall)
PROPS.append(box('barbody', (-5.8, 0, -14), (-5.0, 1.06, -4), M['barwood'], tile=0.9, bevel=0.015))
PROPS.append(box('barfront', (-5.02, 0.12, -13.9), (-4.98, 0.98, -4.1), DL, bevel=0.01))
for yc in (0.36, 0.74):
    pts = []
    zz = -13.85
    while zz < -4.15:
        pts.append((-4.975, yc + (0.09 if len(pts) % 2 else -0.0), zz)); zz += 0.3
    PROPS.append(tube_path('chevron', pts, 0.011, DG))
PROPS.append(box('barband', (-4.99, 0.95, -13.9), (-4.96, 0.99, -4.1), DG))
PROPS.append(box('barband', (-4.99, 0.12, -13.9), (-4.96, 0.16, -4.1), DG))
PROPS.append(box('bartop', (-5.92, 1.06, -14.1), (-4.88, 1.13, -3.9), M['marble'], tile=1.0, bevel=0.012))
PROPS.append(box('barrail', (-4.92, 0.18, -14.0), (-4.84, 0.22, -4.0), M['brass']))
collide((-5.9, 0, -14.1), (-4.9, 1.1, -3.9), cover=True, tag='bar')
# back bar: cabinet, shelves, mirror, bottles
PROPS.append(box('backbar', (-8.0, 0, -13.5), (-7.4, 1.0, -4.5), M['barwood'], tile=0.9, bevel=0.01))
PROPS.append(box('bbmirror', (-7.99, 1.3, -13.3), (-7.97, 2.6, -4.7), M['mirror']))
PROPS += deco_stepped_frame('mframe', 'x', (-7.96, 1.95, -9.0), 8.7, 1.4, t=0.05, d=0.025, steps=2)
for y in (1.6, 2.2):
    PROPS.append(box('shelf', (-8.0, y - 0.03, -13.5), (-7.5, y, -4.5), M['barwood'], bevel=0.005))
for i in range(52):
    y = 1.6 if i % 2 == 0 else 2.2
    z = -13.3 + (i // 2) * 0.33 + rnd.uniform(-0.05, 0.05)
    h = rnd.uniform(0.24, 0.34)
    m = M['bottles'] if rnd.random() < 0.65 else M['bottles2']
    PROPS.append(lathe('bottle', [(0, 0), (0.035, 0), (0.036, h * 0.62), (0.014, h * 0.8), (0.012, h), (0, h)], (-7.75 + rnd.uniform(-0.05, 0.05), y, z), m, seg=6))
for i in range(6):
    st = ph('bar_chair_round_01', (0, 0, 0), ry_deg=rnd.uniform(0, 360), target=900) if i == 0 else dup(stool, (-4.45, 0, -12.5 + i * 1.6), rnd.uniform(0, 360))
    if i == 0:
        stool = st; place_bottom(st, -4.45, 0, -12.5)
    PROPS.append(st)
    collide((-4.7, 0, -12.75 + i * 1.6), (-4.2, 0.75, -12.25 + i * 1.6), tag='stool')
light('AREA', (-6.6, 3.0, -9.0), INCAND, 70, gaim=(-6.6, 0, -9.0), size=(0.8, 8.0), name='bar_down')
light('AREA', (-7.5, 1.05, -9.0), INCAND, 20, gaim=(-7.5, 3.0, -9.0), size=(0.3, 8.0), name='backbar_up')

# ---------------------------------------------------------------- booths (right wall)
for z in (-4.5, -8.5, -12.5):
    for zz in (z, z - 2.2):
        PROPS.append(box('bseat', (6.1, 0, zz - 0.25), (7.7, 0.45, zz + 0.25), M['leather'], tile=0.6, bevel=0.04))
        back_z = (zz + 0.05, zz + 0.25) if zz == z else (zz - 0.25, zz - 0.05)
        PROPS.append(box('bback', (6.1, 0.45, back_z[0]), (7.7, 1.15, back_z[1]), M['leather'], tile=0.6, bevel=0.05))
        PROPS.append(box('bcap', (6.08, 1.12, back_z[0] - 0.02), (7.72, 1.2, back_z[1] + 0.02), M['barwood'], bevel=0.02))
        collide((6.1, 0, zz - 0.2), (7.7, 1.1, zz + 0.2), cover=True, tag='booth')
    PROPS.append(box('bside', (7.4, 0, z - 2.45), (7.98, 1.2, z + 0.25), M['leather'], tile=0.6, bevel=0.04))
    collide((7.4, 0, z - 2.4), (7.8, 1.2, z + 0.2), cover=True, tag='booth')
    PROPS.append(cyl('btleg', (6.6, 0, z - 1.1), 0.05, 0.72, M['brass'], seg=10))
    PROPS.append(lathe('btbase', [(0, 0), (0.25, 0), (0.25, 0.02), (0.05, 0.05), (0, 0.05)], (6.6, 0, z - 1.1), M['brass']))
    PROPS.append(box('bttop', (6.1, 0.72, z - 1.6), (7.1, 0.76, z - 0.6), M['barwood'], bevel=0.015))
    PROPS.append(box('btcloth', (6.15, 0.76, z - 1.55), (7.05, 0.765, z - 0.65), M['cloth']))
    collide((6.1, 0, z - 1.6), (7.1, 0.76, z - 0.6), cover=True, tag='table')
    # brass table lamp with a silk shade
    PROPS.append(lathe('tlamp', [(0, 0), (0.06, 0), (0.03, 0.02), (0.012, 0.03), (0.012, 0.2), (0, 0.2)], (6.9, 0.765, z - 1.1), M['brass'], seg=12))
    PROPS.append(lathe('tshade', [(0.09, 0.0), (0.05, 0.13), (0.045, 0.13), (0.085, 0.0)], (6.9, 0.94, z - 1.1), M['shade'], seg=16, smooth=True))
    light('POINT', (6.9, 1.01, z - 1.1), kelvin(2500), 6, radius=0.03, name='booth_lamp')
    # sconce above each booth
    PROPS += deco_fountain('bsconce', (7.94, 2.3, z - 1.1), scale=1.0, plane_ry=-90, shade=M['shade'])
    light('POINT', (7.82, 2.42, z - 1.1), kelvin(2600), 18, radius=0.05, name='booth_sconce')

# ---------------------------------------------------------------- round tables with lamps and chairs (the floor)
tbl = ph('round_wooden_table_01', (0, 0, 0), scale=0.72, target=1200)
chair = ph('GreenChair_01', (0, 0, 0), target=500, scale=0.92)
first = True
for (x, z) in ((-1.5, -5.5), (1.8, -8), (-2.2, -11.5), (1.2, -13.5), (-0.5, -15.6)):
    t = dup(tbl, (x, 0, z), rnd.uniform(0, 90)); PROPS.append(t)
    PROPS.append(cyl('tcloth', (x, 0.72, z), 0.5, 0.012, M['cloth'], seg=24))
    PROPS.append(lathe('tlamp', [(0, 0), (0.05, 0), (0.025, 0.02), (0.01, 0.03), (0.01, 0.17), (0, 0.17)], (x + 0.12, 0.732, z - 0.1), M['brass'], seg=12))
    PROPS.append(lathe('tshade', [(0.08, 0.0), (0.045, 0.11), (0.04, 0.11), (0.075, 0.0)], (x + 0.12, 0.88, z - 0.1), M['shade'], seg=16))
    light('POINT', (x + 0.12, 0.94, z - 0.1), kelvin(2500), 6, radius=0.03, name='table_lamp')
    collide((x - 0.5, 0, z - 0.5), (x + 0.5, 0.72, z + 0.5), cover=True, tag='table')
    for a in (rnd.uniform(0, 60), rnd.uniform(170, 230)):
        r = math.radians(a)
        cx, cz = x + 0.85 * math.sin(r), z + 0.85 * math.cos(r)
        PROPS.append(dup(chair, (cx, 0, cz), a + 180 + rnd.uniform(-15, 15)))
bpy.data.objects.remove(tbl, do_unlink=True); bpy.data.objects.remove(chair, do_unlink=True)

# pillars with brass capitals
for (x, z) in ((-3.2, -3.5), (3.6, -3.5), (-3.2, -16.8), (3.4, -16.8)):
    PROPS.append(box('pillar', (x - 0.3, 0, z - 0.3), (x + 0.3, RH, z + 0.3), DL, bevel=0.02))
    for k in (-0.15, 0.0, 0.15):
        for (fx, fz) in ((x + k, z + 0.3), (x + k, z - 0.3), (x + 0.3, z + k), (x - 0.3, z + k)):
            PROPS.append(cyl('flute', (fx, 0.14, fz), 0.022, 2.82, DG, seg=5))
    for i, (w, y) in enumerate(((0.38, 3.06), (0.42, 3.12), (0.46, 3.18))):
        PROPS.append(box('pcap2', (x - w, y, z - w), (x + w, y + 0.06, z + w), DG if i % 2 == 0 else DL, bevel=0.005))
    PROPS.append(box('pcap', (x - 0.34, 2.96, z - 0.34), (x + 0.34, 3.06, z + 0.34), M['brass'], bevel=0.01))
    PROPS.append(box('pbase', (x - 0.34, 0, z - 0.34), (x + 0.34, 0.14, z + 0.34), M['brass'], bevel=0.01))
    collide((x - 0.3, 0, z - 0.3), (x + 0.3, RH, z + 0.3), cover=True, tag='pillar')
# chandeliers
chan = ph('Chandelier_02', (0, 0, 0), scale=1.45, target=1800)
for (x, z) in ((-2, -6), (2.5, -10), (-1, -14)):
    c = dup(chan, (x, 0, z), rnd.uniform(0, 60)); lo, hi = bbox(c)
    c.location.z += RH - hi.z; apply_xform(c); PROPS.append(c)
    light('POINT', (x, RH - 0.85, z), kelvin(2600), 70, radius=0.25, name='chandelier')
bpy.data.objects.remove(chan, do_unlink=True)
for (x, s_) in ((-HW, 1), (HW, -1)):
    for z in (-1.5, -6.5, -10.5, -14.5):
        if x > 0 and -14.0 < z < -3.0:
            continue
        PROPS.append(box('pilaster', (min(x, x + s_ * 0.08), 0, z - 0.22), (max(x, x + s_ * 0.08), 3.6, z + 0.22), DL, bevel=0.01))
        for k in (-0.12, 0.0, 0.12):
            PROPS.append(cyl('pflute', (x + s_ * 0.09, 0.2, z + k), 0.02, 3.2, DG, seg=5))
        PROPS.append(box('pilcap', (min(x, x + s_ * 0.12), 3.6, z - 0.28), (max(x, x + s_ * 0.12), 3.72, z + 0.28), DG, bevel=0.01))
# wall sconces (art deco fans)
for (x, z, s) in ((-HW, -3, 1), (-HW, -16.0, 1), (-HW, -19.5, 1), (HW, -2.5, -1), (HW, -15.6, -1)):
    PROPS += deco_fountain('sconce', (x + s * 0.06, 2.42, z), scale=1.15, plane_ry=90 * s, shade=M['shade'])
    light('POINT', (x + s * 0.16, 2.6, z), kelvin(2600), 22, radius=0.06, name='sconce')

# ---------------------------------------------------------------- dressing room
PROPS.append(box('part1', (4.5, 0, -20.0), (4.7, RH, -17.0), M['wall'], tile=2.0))
PROPS.append(box('part2', (4.5, 2.4, -17.0), (4.7, RH, -15.4), M['wall'], tile=2.0))
PROPS.append(box('part3', (4.5, 0, -24.0), (4.7, RH, -21.6), M['wall'], tile=2.0))
PROPS.append(box('part4', (4.6, 0, -15.2), (8.0, RH, -15.0), M['wall'], tile=2.0))
for c in (((4.5, 0, -20.0), (4.7, RH, -17.0)), ((4.5, 0, -24.0), (4.7, RH, -21.6)), ((4.6, 0, -15.2), (8.0, RH, -15.0))):
    collide(*c, tag='wall')
PROPS.append(box('vanity', (6.9, 0, -20.5), (7.9, 0.8, -17.9), M['barwood'], tile=0.9, bevel=0.015))
collide((6.9, 0, -20.5), (7.9, 0.8, -17.9), cover=True, tag='vanity')
mir = ph('ornate_mirror_01', (0, 0, 0), ry_deg=-90, scale=1.5, target=1500); place_bottom(mir, 7.98, 1.05, -19.2, side='-x'); PROPS.append(mir)
for i in range(7):   # vanity bulbs around the mirror
    PROPS.append(lathe('vbulb', [(0, 0), (0.03, 0.01), (0.035, 0.04), (0, 0.07)], (7.9, 2.18, -19.75 + i * 0.18), M['bulb'], seg=8))
light('AREA', (7.6, 2.3, -19.2), kelvin(2700), 60, gaim=(5.5, 1.2, -19.2), size=(0.3, 1.2), name='vanity')
scr = ph('chinese_screen_panels', (0, 0, 0), ry_deg=60, target=800); place_bottom(scr, 5.4, 0, -21.4); PROPS.append(scr)
PROPS.append(box('wardrobe', (4.8, 0, -23.7), (6.4, 1.8, -22.9), M['barwood'], tile=0.9, bevel=0.02))
collide((4.8, 0, -23.7), (6.4, 1.8, -22.9), cover=True, tag='wardrobe')
PROPS.append(box('rack', (6.6, 1.7, -23.5), (7.8, 1.73, -23.45), M['chrome']))
for i in range(5):
    PROPS.append(box_rot('gown', (6.75 + i * 0.25, 1.15, -23.45), (0.22, 1.1, 0.12), 0, 0, M['velvet'] if i % 2 else M['leather'], bevel=0.04))

# ---------------------------------------------------------------- stage spotlight (warm, from the back of the room)
light('SPOT', (1.0, RH - 0.3, -11.5), kelvin(3200), 2200, radius=0.05, gaim=(-1.5, 0.6, -19.5), spot_deg=16, blend=0.3, name='stage_spot')
PROPS.append(cyl('spotcan', (1.15, RH - 0.25, -11.2), 0.1, 0.25, M['black'], seg=12))

bpy.context.scene['colliders'] = json.dumps(COL)
print('[club] tris shell', sum(tris(o) for o in SHELL), 'props', sum(tris(o) for o in PROPS), 'neon', sum(tris(o) for o in NEON))


def preview(path, eye, look, res=(390, 844), samples=96):
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); link(cam)
    cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(74); cd.clip_start = 0.05; cd.clip_end = 200
    cam.location = G(*eye); d = (G(*look) - cam.location).normalized(); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc = bpy.context.scene; sc.camera = cam; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    old = sc.cycles.samples; sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.view_settings.exposure = 0.8
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    sc.cycles.samples = old; sc.cycles.use_denoising = False
    bpy.data.objects.remove(cam)


if '--preview' in ARGS:
    preview(WORK / 'club_preview.png', (0.6, 1.7, -9.5), (-1.5, 1.6, -19.0))
    preview(WORK / 'club_preview_entry.png', (0, 1.65, -0.6), (0, 1.3, -12))

if '--bake' in ARGS:
    shell = join(SHELL, 'SHELL'); props = join(PROPS, 'PROPS'); neon = join(NEON, 'NEON')
    unwrap(shell, 'lm', margin=0.002); unwrap(props, 'atlas', margin=0.0015)
    lm = new_float_image('club_lm', 2048, 2048); at = new_float_image('club_atlas', 2048, 2048)
    bake([shell], [lm], 'lm', 'DIFFUSE')
    bake([props], [at], 'atlas', 'COMBINED')
    lm_mult, lm_img = save_ldr(lm, WORK / 'club_lm.jpg', pct=99.5, smooth=2)
    at_mult, at_img = save_ldr(at, WORK / 'club_atlas.jpg', pct=99.3)
    for slot in shell.material_slots:
        slot.material = export_mat_lightmapped(slot.material, lm_img, lm_mult)
    strip_uv_except(shell, ['UVMap', 'lm'])
    single_material(props, export_mat_baked('BAKED_props', at_img, 'atlas', at_mult)); strip_uv_except(props, ['atlas'])
    strip_uv_except(neon, [])
    export_glb([shell, props, neon], OUT)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / 'club_baked.blend'))
