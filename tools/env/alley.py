"""NEON RAIN environment pass: the alley behind Kestrel Street (tutorial fight), built, lit and baked in Blender,
exported to assets/models/env_alley.glb.
Usage: blender -b --python tools/env/alley.py -- [--preview] [--bake] [--samples N]
Layout (game coords): alley x -3.2..3.2 between brick walls, from the entrance z 3.2 to the street mouth at z -40.
The cover pieces keep the grey-box footprints (the fight is tuned on them). Miles lies at (0.2, -34.5) under a sodium
street lamp at the mouth. Neon blade signs hang off the walls on steel brackets; their tubes are separate NEON_*
materials (unlit + flicker in the game, mirrored into the puddles)."""
import sys, json, math, pathlib, random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib, envlib
importlib.reload(envlib)
from envlib import *

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(ARGS[ARGS.index('--samples') + 1]) if '--samples' in ARGS else 768
OUT = ROOT / "assets" / "models" / "env_alley.glb"
HW, Z0, Z1, WH = 3.2, 3.2, -40.5, 12.0
rnd = random.Random(11)

reset(SAMPLES)
world_color((0.006, 0.0032, 0.0016), 1.0)   # sodium sky glow over the city

M = dict(
    ground=pbr('ground', 'asphalt_02', tint=(0.42, 0.4, 0.38), rough=0.25),
    curb=pbr('curb', 'concrete_wall_006', tint=(0.45, 0.42, 0.38)),
    brick=pbr('brick', 'red_brick_03', tint=(0.62, 0.5, 0.44)),
    brick2=pbr('brick2', 'dark_brick_wall', tint=(0.7, 0.6, 0.52)),
    green=pbr('dumpster', 'green_metal_rust', tint=(0.55, 0.62, 0.5)),
    shutter=pbr('shutter', 'rusty_metal_shutter', tint=(0.5, 0.45, 0.4)),
    rust=pbr('rust', 'rusty_metal_02', tint=(0.45, 0.4, 0.36)),
    planks=pbr('planks', 'dark_wooden_planks', tint=(0.75, 0.62, 0.5)),
    steel=flat('steel', (0.06, 0.06, 0.065), rough=0.45, metal=0.8),
    cabinet=flat('signbox', (0.03, 0.028, 0.026), rough=0.5, metal=0.3),
    winlit=flat('winlit', (0.9, 0.55, 0.25), emit=(1.0, 0.55, 0.22), emit_strength=1.1),
    shoplit=flat('shoplit', (0.5, 0.3, 0.15), emit=(1.0, 0.5, 0.2), emit_strength=0.35),
    windark=flat('windark', (0.02, 0.02, 0.025), rough=0.08),
    frame=flat('winframe', (0.08, 0.06, 0.05), rough=0.6),
    doorwood=pbr('doorwood', 'dark_wooden_planks', tint=(0.4, 0.3, 0.24)),
    bulb=flat('bulb', (1, 0.9, 0.7), emit=INCAND, emit_strength=30.0),
    awn1=flat('awn1', (0.32, 0.05, 0.04), rough=0.7),
    awn2=flat('awn2', (0.05, 0.2, 0.2), rough=0.7),
    awn3=flat('awn3', (0.35, 0.22, 0.05), rough=0.7),
    stallwood=pbr('stallwood', 'dark_wooden_planks', tint=(0.6, 0.45, 0.32)),
    lantern=flat('lantern', (0.9, 0.3, 0.1), emit=(1.0, 0.32, 0.08), emit_strength=6.0),
    menu=flat('menu', (0.8, 0.6, 0.3), emit=(1.0, 0.7, 0.35), emit_strength=1.5),
    pot=flat('pot', (0.2, 0.2, 0.21), rough=0.35, metal=0.9),
    sodlamp=flat('sodlamp', (1, 0.6, 0.2), emit=SODIUM, emit_strength=40.0),
)
NEONM = {}


def neon_mat(col, name):
    if name not in NEONM:
        NEONM[name] = flat('NEON_' + name, col, rough=0.2, emit=col, emit_strength=18.0)
    return NEONM[name]


SHELL, SHELL_HI, PROPS, NEON, COL = [], [], [], [], []


def collide(lo, hi, cover=False, tag=''):
    COL.append(dict(min=list(lo), max=list(hi), cover=cover, tag=tag))


# ---------------------------------------------------------------- shell: wet asphalt, curbs, brick walls
SHELL.append(box('ground', (-HW, -0.1, Z1), (HW, 0, Z0), M['ground'], tile=3.0, faces=['+y']))
for s in (-1, 1):
    x0, x1 = (-HW, -HW + 0.35) if s < 0 else (HW - 0.35, HW)
    SHELL.append(box('curb', (x0, 0, Z1), (x1, 0.012, Z0), M['curb'], tile=1.5, faces=['+y']))
    wx0, wx1 = (-HW - 0.4, -HW) if s < 0 else (HW, HW + 0.4)
    side = '+x' if s < 0 else '-x'
    SHELL.append(box('wall', (wx0, 0, Z1), (wx1, 5.0, Z0), M['brick'], tile=2.4, faces=[side]))
    SHELL_HI.append(box('wallhi', (wx0, 5.0, Z1), (wx1, WH, Z0), M['brick2'], tile=3.0, faces=[side]))
    collide((wx0 - 0.2, 0, Z1 - 3), (wx1 + 0.2, WH, Z0 + 3), tag='wall')
SHELL.append(box('back', (-HW, 0, Z0), (HW, 6.0, Z0 + 0.4), M['brick2'], tile=2.4, faces=['-z']))
collide((-HW - 1, 0, Z0), (HW + 1, 6, Z0 + 0.6), tag='wall')
# the street mouth: a low wall and a chain gate, the street lamp, the city beyond
SHELL.append(box('mouthwall', (-HW, 0, Z1 - 0.4), (HW, 1.0, Z1), M['brick'], tile=2.4))
collide((-HW - 1, 0, Z1 - 0.6), (HW + 1, 6, Z1), tag='wall')
SHELL.append(box('street', (-12, -0.12, Z1 - 14), (12, -0.02, Z1 - 0.4), M['ground'], tile=3.0, faces=['+y']))
for x in (-HW, HW - 0.3):
    PROPS.append(box('pier', (x, 0, Z1 - 0.45), (x + 0.3, 2.6, Z1 + 0.05), M['brick2'], tile=1.2, bevel=0.02))
for i in range(13):
    x = -HW + 0.3 + i * 0.47
    PROPS.append(box('rail', (x, 1.0, Z1 - 0.25), (x + 0.025, 2.1, Z1 - 0.2), M['steel']))
PROPS.append(box('railtop', (-HW + 0.3, 2.06, Z1 - 0.26), (HW - 0.3, 2.1, Z1 - 0.19), M['steel']))
# far side of the street: a facade with shopfronts
SHELL.append(box('facade', (-14, 0, Z1 - 14.4), (14, 14, Z1 - 14), M['brick2'], tile=3.0, faces=['+z']))
for i, x in enumerate((-6.5, -2.0, 2.5, 7.0)):
    PROPS.append(box('shop', (x - 1.5, 0.4, Z1 - 13.98), (x + 1.5, 3.0, Z1 - 13.9), M['shoplit'] if i % 2 == 0 else M['windark']))

# ---------------------------------------------------------------- windows up the walls (some lit, warm)
for s in (-1, 1):
    wx = -HW if s < 0 else HW
    for z in range(-38, 2, 4):
        for y in (4.2, 6.9, 9.6):
            if rnd.random() < 0.25:
                continue
            zz = z + rnd.uniform(-0.3, 0.3)
            lit = rnd.random() < 0.35
            a, b = (wx - 0.06, wx + 0.02) if s < 0 else (wx - 0.02, wx + 0.06)
            PROPS.append(box('win', (a, y, zz - 0.45), (b, y + 1.4, zz + 0.45), M['winlit'] if lit else M['windark']))
            c, d = (wx, wx + 0.06) if s < 0 else (wx - 0.06, wx)
            PROPS.append(box('wsill', (c - 0.02 * s, y - 0.08, zz - 0.55), (d + 0.04 * -s, y, zz + 0.55), M['curb']))
            for (y0, y1, z0, z1_) in ((y, y + 1.4, zz - 0.5, zz - 0.45), (y, y + 1.4, zz + 0.45, zz + 0.5), (y + 1.38, y + 1.45, zz - 0.5, zz + 0.5), (y + 0.68, y + 0.72, zz - 0.45, zz + 0.45)):
                PROPS.append(box('wframe', (c, y0, z0), (d, y1, z1_), M['frame']))

# ---------------------------------------------------------------- doors with warm lamps (the grey-box doorways)
for (x, z) in ((-HW, -9), (HW, -17), (-HW, -27)):
    s = -1 if x < 0 else 1
    a, b = (x - 0.02, x + 0.03) if s < 0 else (x - 0.03, x + 0.02)
    PROPS.append(box('door', (a, 0.08, z - 0.55), (b, 2.25, z + 0.55), M['shutter'] if z == -17 else M['doorwood'], tile=1.2, bevel=0.005))
    c, d = (x, x + 0.12) if s < 0 else (x - 0.12, x)
    for (z0, z1_) in ((z - 0.68, z - 0.55), (z + 0.55, z + 0.68)):
        PROPS.append(box('jamb', (c, 0, z0), (d, 2.38, z1_), M['curb'], bevel=0.01))
    PROPS.append(box('lintel', (c, 2.25, z - 0.68), (d, 2.4, z + 0.68), M['curb'], bevel=0.01))
    PROPS.append(box('step', (min(c, c + 0.3 * -s), 0, z - 0.7), (max(d, d + 0.3 * -s), 0.1, z + 0.7), M['curb'], bevel=0.01))
    lamp = ph('industrial_wall_lamp', (0, 0, 0), ry_deg=90 if s < 0 else -90, target=1500)
    place_bottom(lamp, x, 2.5, z, side='+x' if s < 0 else '-x'); PROPS.append(lamp)
    light('POINT', (x - 0.22 * s, 2.62, z), kelvin(2500), 55, radius=0.05, name='doorlamp')
    PROPS.append(box('knob', (x - 0.06 * s - 0.02, 1.0, z + 0.35), (x - 0.06 * s + 0.02, 1.05, z + 0.42), M['steel']))

# ---------------------------------------------------------------- fire escapes, pipes, gutters
def fire_escape(x, zc, s, floors=(3.4, 6.2, 9.0), half=2.2, depth=1.15):
    """Steel fire escape on the wall at x (s = +1 right wall, -1 left wall): grated landings, rails, switchback stairs,
    a drop ladder and wall brackets."""
    xo = x - s * depth
    xa, xb = min(x, xo), max(x, xo)
    for k, y in enumerate(floors):
        PROPS.append(box('fe_deck', (xa, y - 0.05, zc - half), (xb, y, zc + half), M['rust'], tile=0.6))
        for (y0, y1) in ((y + 0.98, y + 1.02), (y + 0.48, y + 0.51)):
            PROPS.append(box('fe_rail', (xo - 0.02, y0, zc - half), (xo + 0.02, y1, zc + half), M['steel']))
            for ze in (zc - half, zc + half - 0.03):
                PROPS.append(box('fe_rail', (xa, y0, ze), (xb, y1, ze + 0.03), M['steel']))
        n = int(2 * half / 0.5)
        for i in range(n + 1):
            z = zc - half + i * (2 * half / n)
            PROPS.append(box('fe_post', (xo - 0.015, y, z - 0.015), (xo + 0.015, y + 1.0, z + 0.015), M['steel']))
        for z in (zc - half + 0.4, zc + half - 0.4):   # wall brackets
            PROPS.append(box_rot('fe_brace', ((x + xo) / 2, y - 0.45, z), (0.04, 0.04, 1.3), 0, 90, M['steel']) if False else
                         tube_path('fe_brace', [(x - s * 0.02, y - 0.9, z), (xo + s * 0.1, y - 0.06, z)], 0.02, M['steel']))
        if k < len(floors) - 1:   # stair up to the next landing, alternating direction, along the outer half
            y1 = floors[k + 1]; dz = 2 * half - 0.9; zs = zc - half + 0.45; ze_ = zs + dz
            if k % 2: zs, ze_ = ze_, zs
            ang = math.degrees(math.atan2(y1 - y, abs(ze_ - zs))) * (1 if ze_ < zs else -1)
            L_ = math.hypot(y1 - y, ze_ - zs); xc = x - s * 0.62
            for dx in (-0.3, 0.3):
                PROPS.append(box_rot('fe_stringer', (xc + dx, (y + y1) / 2, (zs + ze_) / 2), (0.03, 0.14, L_), ang, 0, M['steel']))
            steps = int((y1 - y) / 0.2)
            for j in range(1, steps):
                f = j / steps
                PROPS.append(box('fe_step', (xc - 0.3, y + f * (y1 - y) - 0.02, zs + f * (ze_ - zs) - 0.1), (xc + 0.3, y + f * (y1 - y), zs + f * (ze_ - zs) + 0.1), M['rust'], tile=0.5))
    # drop ladder under the first landing
    y = floors[0]; xl = x - s * 0.62; zl = zc + half - 0.35
    for dz in (-0.2, 0.2):
        PROPS.append(box('fe_lad', (xl - 0.02, 1.5, zl + dz - 0.015), (xl + 0.02, y + 1.0, zl + dz + 0.015), M['steel']))
    yy = 1.6
    while yy < y:
        PROPS.append(box('fe_rung', (xl - 0.012, yy, zl - 0.2), (xl + 0.012, yy + 0.025, zl + 0.2), M['steel'])); yy += 0.3


fire_escape(HW, -6.0, 1); fire_escape(-HW, -21.0, -1)
for (x, z) in ((-HW, -2.0), (-HW, -15.5), (HW, -11.0), (HW, -27.5), (-HW, -33.0)):
    s = -1 if x < 0 else 1
    px = x - 0.1 * s
    PROPS.append(tube_path('downpipe', [(px, WH, z), (px, 0.35, z), (px - 0.18 * s, 0.12, z)], 0.055, M['rust']))
    for y in (2.0, 5.0, 8.0):
        PROPS.append(box('pclip', (min(x, px), y, z - 0.03), (max(x, px) + 0.0, y + 0.05, z + 0.03), M['steel']))
pp = ph('modular_industrial_pipes_01', (0, 0, 0), ry_deg=90, target=4000)
place_bottom(pp, -HW, 0.6, -24.5, side='+x'); PROPS.append(pp)
pp2 = ph('modular_industrial_pipes_01', (0, 0, 0), ry_deg=-90, target=4000)
place_bottom(pp2, HW, 1.4, -31.0, side='-x'); PROPS.append(pp2)
# overhead cables between the walls
for z in (-4.0, -18.5, -30.0):
    PROPS.append(tube_path('cable', [(-HW, 7.5, z), (0, 6.9, z + 0.4), (HW, 7.6, z + 0.8)], 0.012, M['steel']))

# ---------------------------------------------------------------- cover: dumpsters, crates, barrels (grey-box footprints)
def dumpster(cx, cz):
    x0, x1, z0, z1_ = cx - 0.65, cx + 0.65, cz - 1.0, cz + 1.0
    PROPS.append(box('dbody', (x0, 0.14, z0), (x1, 1.2, z1_), M['green'], tile=1.0, bevel=0.025))
    PROPS.append(box('drim', (x0 - 0.04, 1.16, z0 - 0.04), (x1 + 0.04, 1.24, z1_ + 0.04), M['green'], tile=1.0, bevel=0.015))
    PROPS.append(box_rot('dlid', (cx, 1.33, cz - 0.48), (1.36, 0.035, 1.0), -8, 0, M['green'], tile=1.0, bevel=0.01))
    PROPS.append(box_rot('dlid2', (cx + 0.05, 1.36, cz + 0.5), (1.36, 0.035, 1.0), 14, 0, M['green'], tile=1.0, bevel=0.01))
    for (wx, wz) in ((x0 + 0.12, z0 + 0.15), (x1 - 0.12, z0 + 0.15), (x0 + 0.12, z1_ - 0.15), (x1 - 0.12, z1_ - 0.15)):
        PROPS.append(cyl('wheel', (wx - 0.03, 0.07, wz), 0.07, 0.06, M['steel'], seg=10, axis='X'))
    for z in (z0 - 0.07, z1_ + 0.02):
        PROPS.append(box('dbar', (x0 + 0.1, 0.7, z), (x1 - 0.1, 0.75, z + 0.05), M['steel']))
    collide((x0, 0, z0), (x1, 1.3, z1_), cover=True, tag='dumpster')
    tb = ph('trashbag', (0, 0, 0), ry_deg=rnd.uniform(0, 360), target=900)
    place_bottom(tb, cx + 0.3 * (1 if cx < 0 else -1), 0, z1_ + 0.35); PROPS.append(tb)


dumpster(-HW + 0.75, -12); dumpster(HW - 0.75, -22)


def crate(cx, cy, cz, w, h, d, ry=0):
    PROPS.append(box_rot('crate', (cx, cy + h / 2, cz), (w, h, d), 0, ry, M['planks'], tile=0.8, bevel=0.02))
    for k in (-1, 1):
        PROPS.append(box_rot('crateband', (cx, cy + h / 2 + k * h * 0.32, cz), (w + 0.012, 0.06, d + 0.012), 0, ry, M['doorwood'], tile=0.6))


crate(1.2, 0, -16, 1.0, 1.0, 1.0, 4); crate(1.0, 1.0, -16.1, 0.5, 0.5, 0.5, -12)
collide((0.7, 0, -16.5), (1.7, 1.0, -15.5), cover=True, tag='crate'); collide((0.75, 1.0, -16.35), (1.25, 1.5, -15.85), cover=True, tag='crate')
crate(-1.25, 0, -29, 0.7, 1.1, 0.9, 0); crate(-0.55, 0, -29.05, 0.7, 0.75, 0.85, 6)
cb = ph('cardboard_box_01', (0, 0, 0), ry_deg=20, target=1200); place_bottom(cb, -0.5, 0.75, -29.0); PROPS.append(cb)
collide((-1.6, 0, -29.45), (-0.2, 1.1, -28.55), cover=True, tag='crate')
for (x, z) in ((HW - 0.6, -31), (-HW + 0.5, -5)):
    br = ph('barrel_03', (0, 0, 0), ry_deg=rnd.uniform(0, 360), target=1200); place_bottom(br, x, 0, z); PROPS.append(br)
    collide((x - 0.35, 0, z - 0.35), (x + 0.35, 0.9, z + 0.35), cover=True, tag='barrel')
# trash cans + bags along the walls (small colliders, not cover)
for (x, z) in ((HW - 0.45, -8.2), (-HW + 0.45, -16.6), (HW - 0.45, -25.4), (-HW + 0.45, -34.5)):
    can = ph('metal_trash_can', (0, 0, 0), exact=['metal_trash_can', 'metal_trash_can_handle_left', 'metal_trash_can_handle_right'], target=2200)
    place_bottom(can, x, 0, z); PROPS.append(can)
    lo, hi = bbox(can)
    PROPS.append(lathe('canlid', [(0, 0), (0.29, 0), (0.29, 0.03), (0.2, 0.06), (0.03, 0.07), (0.03, 0.1), (0, 0.1)], (x + 0.03, hi.z - 0.005, z - 0.02), M['rust'], seg=20))
    collide((x - 0.3, 0, z - 0.3), (x + 0.3, 0.9, z + 0.3), tag='can')
for (x, z) in ((HW - 0.5, -9.0), (-HW + 0.6, -33.6), (2.6, -35.6)):
    tb = ph('trashbag', (0, 0, 0), ry_deg=rnd.uniform(0, 360), target=900); place_bottom(tb, x, 0, z); PROPS.append(tb)
tyre = ph('old_tyre', (0, 0, 0), target=900); tyre.rotation_euler = (math.radians(80), 0, 0.3); apply_xform(tyre); place_bottom(tyre, -2.7, 0, -8.0); PROPS.append(tyre)
mh = ph('water_manhole_cover', (0, 0, 0), target=1200); place_bottom(mh, 0.4, -0.015, -19.0); PROPS.append(mh)

# ---------------------------------------------------------------- neon blade signs on steel brackets
def blade(text, col, cname, x, z, y0, height, out=1.0, size=0.42):
    s = -1 if x < 0 else 1
    xin, xout = x - s * 0.18, x - s * (0.18 + out)
    cx = (xin + xout) / 2
    PROPS.append(box('sign', (min(xin, xout), y0, z - 0.11), (max(xin, xout), y0 + height, z + 0.11), M['cabinet'], bevel=0.02))
    for y in (y0 + 0.25, y0 + height - 0.25):
        PROPS.append(box('bracket', (min(x, xin), y - 0.03, z - 0.03), (max(x, xin), y + 0.03, z + 0.03), M['steel']))
    PROPS.append(tube_path('brace', [(x - s * 0.02, y0 + height + 0.45, z), (xout + s * 0.1, y0 + height, z)], 0.015, M['steel']))
    for face in (1, -1):   # deco border: stepped gold frame on both faces
        PROPS.extend(deco_stepped_frame('sframe', 'z', (cx, y0 + height / 2, z + face * 0.115), abs(out) + 0.02, height + 0.02, t=0.03, d=0.012, steps=1))
    nm = neon_mat(col, cname)
    for face in (1, -1):
        zf = z + face * 0.125
        letters = list(text)
        step = min(size * 1.15, (height - 0.35) / len(letters))
        for i, ch in enumerate(letters):
            yy = y0 + height - 0.3 - step * (i + 0.5)
            NEON.append(neon_text('n_' + ch, ch, (cx, yy, zf), 0 if face > 0 else 180, step * 1.05, nm, depth=0.011))
        bw = abs(xout - xin) - 0.12
        NEON.append(tube_path('nborder', [(cx - bw / 2, y0 + 0.08, zf), (cx + bw / 2, y0 + 0.08, zf), (cx + bw / 2, y0 + height - 0.08, zf), (cx - bw / 2, y0 + height - 0.08, zf), (cx - bw / 2, y0 + 0.08, zf)], 0.009, nm))
    lc = (cx, y0 + height / 2, z)
    for face in (1, -1):
        light('AREA', (cx, y0 + height / 2, z + face * 0.3), col, 70 * height, gaim=(cx, y0 + height / 2 - 0.3, z + face * 3), size=(abs(out), height * 0.9), name='neon_' + cname)
    light('POINT', (cx, y0 - 0.2, z), col, 25, radius=0.3, name='neon_down')


blade('HOTEL', NEON_RED, 'red', -HW, -7.0, 3.2, 2.6)
blade('NOODLES', NEON_TEAL, 'teal', HW, -14.0, 3.0, 3.1, size=0.4)
blade('BAR', NEON_ORANGE, 'orange', -HW, -24.0, 2.9, 1.7)
blade('ROOMS', (1.0, 0.08, 0.3), 'pink', HW, -30.0, 4.0, 2.6)

# ---------------------------------------------------------------- the sodium street lamp at the mouth (over Miles)
sl = ph('street_lamp_01', (0, 0, 0), target=6000); place_bottom(sl, 2.1, 0, -36.6); PROPS.append(sl)
lo, hi = bbox(sl)
LAMP_TOP = hi.z
print('[alley] street lamp top', round(LAMP_TOP, 2))
light('SPOT', (2.1, LAMP_TOP - 0.45, -36.6), SODIUM, 3200, radius=0.12, gaim=(1.2, 0, -35.2), spot_deg=120, blend=0.6, name='sodium_lamp')
light('POINT', (2.1, LAMP_TOP - 0.4, -36.6), SODIUM, 160, radius=0.15, name='sodium_glow')
light('SPOT', (-6.0, 7.0, Z1 - 8.0), SODIUM, 9000, radius=0.3, gaim=(0, 0, Z1 - 2), spot_deg=60, blend=0.5, name='street_far')
light('AREA', (0, 14, -18), SODIUM_HP, 160, gaim=(0, 0, -18), size=(5, 40), name='sky_fill')


# ---------------------------------------------------------------- density pass: made-up neon glyph signs, awnings, a noodle stall
GRND = random.Random(42)
GPTS = [(-0.5, 0.5), (0, 0.5), (0.5, 0.5), (-0.5, 0), (0, 0), (0.5, 0), (-0.5, -0.5), (0, -0.5), (0.5, -0.5)]


def glyph(cx, cy, z, s, nm, face, seed):
    """An invented character: 2-4 tube strokes on a 3x3 grid (never a real script)."""
    r = random.Random(seed)
    for _ in range(r.randint(2, 4)):
        a, b = r.sample(range(9), 2)
        path = [GPTS[a], GPTS[b]]
        if r.random() < 0.4:
            path.append(GPTS[r.randrange(9)])
        NEON.append(tube_path('glyph', [(cx + px * s * face, cy + py * s, z) for px, py in path], 0.008, nm))


def glyph_blade(x, z, y0, height, col, cname, n, out=0.75, seed=0):
    s_ = -1 if x < 0 else 1
    xin, xout = x - s_ * 0.18, x - s_ * (0.18 + out)
    cx = (xin + xout) / 2
    PROPS.append(box('gsign', (min(xin, xout), y0, z - 0.09), (max(xin, xout), y0 + height, z + 0.09), M['cabinet'], bevel=0.015))
    for face in (1, -1):
        PROPS.extend(deco_stepped_frame('gframe', 'z', (cx, y0 + height / 2, z + face * 0.095), out + 0.02, height + 0.02, t=0.025, d=0.01, steps=1))
    for y in (y0 + 0.2, y0 + height - 0.2):
        PROPS.append(box('gbr', (min(x, xin), y - 0.025, z - 0.025), (max(x, xin), y + 0.025, z + 0.025), M['steel']))
    nm = neon_mat(col, cname)
    step = (height - 0.2) / n
    for face in (1, -1):
        zf = z + face * 0.1
        for i in range(n):
            glyph(cx, y0 + height - 0.1 - step * (i + 0.5), zf, min(step * 0.62, out * 0.55), nm, face, seed * 31 + i)
        bw = abs(out) - 0.1
        NEON.append(tube_path('gborder', [(cx - bw / 2, y0 + 0.05, zf), (cx + bw / 2, y0 + 0.05, zf), (cx + bw / 2, y0 + height - 0.05, zf), (cx - bw / 2, y0 + height - 0.05, zf), (cx - bw / 2, y0 + 0.05, zf)], 0.007, nm))
    for face in (1, -1):
        light('AREA', (cx, y0 + height / 2, z + face * 0.25), col, 28 * height, gaim=(cx, y0 + height / 2 - 0.3, z + face * 3), size=(abs(out), height * 0.9), name='neon_' + cname)


def wall_sign(x, z, y, w, h, col, cname, n, seed):
    """A sign box flush on the wall with a row of invented glyphs."""
    s_ = -1 if x < 0 else 1
    xf = x - s_ * 0.12
    PROPS.append(box('wsign', (min(x, xf), y, z - w / 2), (max(x, xf), y + h, z + w / 2), M['cabinet'], bevel=0.01))
    nm = neon_mat(col, cname)
    xg = xf - s_ * 0.015
    step = w / n
    for i in range(n):
        zc = z - w / 2 + step * (i + 0.5)
        r = random.Random(seed * 17 + i)
        for _ in range(r.randint(2, 4)):
            a, b = r.sample(range(9), 2); sz = min(step, h) * 0.6
            NEON.append(tube_path('wglyph', [(xg, y + h / 2 + GPTS[a][1] * sz, zc + GPTS[a][0] * sz), (xg, y + h / 2 + GPTS[b][1] * sz, zc + GPTS[b][0] * sz)], 0.008, nm))
    light('AREA', (xg - s_ * 0.2, y + h / 2, z), col, 22 * w, gaim=(0, y - 1.0, z), size=(0.3, w), name='neon_' + cname)


AMBER, CYAN, GREEN, MAG = (1.0, 0.45, 0.05), (0.05, 0.75, 1.0), (0.2, 1.0, 0.25), (1.0, 0.08, 0.6)
for (x, z, y0, hgt, col, cn, n) in ((HW, -4.2, 4.4, 2.2, CYAN, 'g_cyan', 4), (-HW, -12.2, 4.2, 2.6, GREEN, 'g_green', 5), (HW, -20.0, 3.6, 1.9, AMBER, 'g_amber', 3),
                                    (-HW, -17.5, 6.2, 2.4, MAG, 'g_mag', 4), (HW, -9.6, 6.4, 2.0, NEON_RED, 'g_red', 3), (-HW, -31.0, 3.4, 2.2, CYAN, 'g_cyan', 4),
                                    (HW, -26.0, 6.0, 2.6, GREEN, 'g_green', 5), (-HW, -2.8, 5.6, 1.8, AMBER, 'g_amber', 3)):
    glyph_blade(x, z, y0, hgt, col, cn, n, seed=int(abs(z) * 10))
for (x, z, y, w, h, col, cn, n) in ((-HW, -10.5, 2.6, 1.6, 0.42, AMBER, 'g_amber', 4), (HW, -19.2, 2.55, 1.4, 0.38, MAG, 'g_mag', 3),
                                    (-HW, -26.0, 2.55, 1.2, 0.36, CYAN, 'g_cyan', 3), (HW, -29.0, 2.7, 1.8, 0.42, NEON_RED, 'g_red', 4)):
    wall_sign(x, z, y, w, h, col, cn, n, int(abs(z) * 7))
# warm orange bar lights on the walls
for (x, z, y) in ((-HW, -14.8, 2.5), (HW, -11.8, 2.4), (-HW, -21.8, 2.5), (HW, -33.2, 2.5)):
    s_ = -1 if x < 0 else 1
    NEON.append(box('wallbar', (min(x, x - s_ * 0.06), y, z - 0.45), (max(x, x - s_ * 0.06), y + 0.07, z + 0.45), neon_mat(AMBER, 'g_amber')))
    light('AREA', (x - s_ * 0.2, y, z), (1.0, 0.5, 0.1), 40, gaim=(0, y - 1, z), size=(0.1, 0.9), name='wallbar')
# awnings over the doorways: sloped canvas, valance, two struts
for (x, z, m) in ((-HW, -9, 'awn1'), (HW, -17, 'awn2'), (-HW, -27, 'awn3')):
    s_ = -1 if x < 0 else 1
    xm = x - s_ * 0.55
    bm = bmesh.new()
    vs = [bm.verts.new(G(*p)) for p in ((x, 2.95, z - 0.9), (x, 2.95, z + 0.9), (x - s_ * 1.1, 2.55, z + 0.9), (x - s_ * 1.1, 2.55, z - 0.9))]
    bm.faces.new(vs)
    aw = mesh_obj('awning', bm, M[m]); box_uv(aw, 0.6)
    sol = aw.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.02; select_only([aw]); bpy.ops.object.modifier_apply(modifier='s')
    PROPS.append(aw)
    PROPS.append(box('valance', (min(x - s_ * 1.08, x - s_ * 1.11), 2.36, z - 0.9), (max(x - s_ * 1.08, x - s_ * 1.11), 2.56, z + 0.9), M[m]))
    for dz in (-0.85, 0.85):
        PROPS.append(tube_path('strut', [(x, 3.05, z + dz), (x - s_ * 1.08, 2.58, z + dz)], 0.012, M['steel']))
# a noodle stall near the entrance (right side): counter, canopy, stools, stove and pot, paper lanterns, menu board
SX0, SX1, SZ0, SZ1 = 1.75, 3.15, -4.6, -1.7
PROPS.append(box('stallctr', (SX0, 0, SZ0), (SX0 + 0.55, 1.0, SZ1), M['stallwood'], tile=0.8, bevel=0.01))
PROPS.append(box('stalltop', (SX0 - 0.08, 1.0, SZ0 - 0.05), (SX0 + 0.6, 1.05, SZ1 + 0.05), M['stallwood'], bevel=0.008))
PROPS.append(box('stallback', (SX1 - 0.1, 0, SZ0), (SX1, 2.4, SZ1), M['stallwood'], tile=0.8))
for zz in (SZ0, SZ1 - 0.05):
    PROPS.append(box('stallpost', (SX0 - 0.05, 0, zz), (SX0, 2.45, zz + 0.05), M['steel']))
bm = bmesh.new()
vs = [bm.verts.new(G(*p)) for p in ((SX1, 2.6, SZ0 - 0.15), (SX1, 2.6, SZ1 + 0.15), (SX0 - 0.35, 2.4, SZ1 + 0.15), (SX0 - 0.35, 2.4, SZ0 - 0.15))]
bm.faces.new(vs); can_ = mesh_obj('canopy', bm, M['awn1']); box_uv(can_, 0.6)
sol = can_.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.02; select_only([can_]); bpy.ops.object.modifier_apply(modifier='s')
PROPS.append(can_)
PROPS.append(box('menuboard', (SX1 - 0.12, 1.4, SZ0 + 0.3), (SX1 - 0.1, 2.0, SZ1 - 0.3), M['menu']))
PROPS.append(box('stove', (SX0 + 0.6, 0, SZ0 + 0.4), (SX0 + 1.1, 1.0, SZ0 + 1.0), M['steel']))
PROPS.append(lathe('stockpot', [(0, 0), (0.18, 0), (0.18, 0.28), (0.17, 0.28), (0.17, 0.02), (0, 0.02)], (SX0 + 0.85, 1.0, SZ0 + 0.7), M['pot'], seg=14))
for zz in (SZ0 + 0.5, (SZ0 + SZ1) / 2, SZ1 - 0.5):
    PROPS.append(lathe('lantern', [(0, 0), (0.1, 0.03), (0.13, 0.15), (0.1, 0.28), (0, 0.3)], (SX0 - 0.15, 1.95, zz), M['lantern'], seg=12))
    PROPS.append(cyl('lstring', (SX0 - 0.15, 2.25, zz), 0.004, 0.2, M['steel'], seg=4))
    light('POINT', (SX0 - 0.15, 2.08, zz), (1.0, 0.35, 0.08), 18, radius=0.1, name='lantern')
    PROPS.append(cyl('stoolp', (SX0 - 0.45, 0, zz), 0.03, 0.7, M['steel'], seg=8))
    PROPS.append(cyl('stools', (SX0 - 0.45, 0.68, zz), 0.17, 0.05, M['stallwood'], seg=14))
collide((SX0, 0, SZ0), (SX1, 1.0, SZ1), cover=True, tag='stall')
# more overhead cables, sagging, at several heights
for k in range(9):
    z = -2 - k * 4.2 + GRND.uniform(-1, 1)
    y1, y2 = GRND.uniform(5.5, 9.5), GRND.uniform(5.5, 9.5)
    PROPS.append(tube_path('cable2', [(-HW, y1, z), (-1, min(y1, y2) - 0.8, z + 0.3), (1, min(y1, y2) - 0.8, z + 0.6), (HW, y2, z + GRND.uniform(-1.5, 1.5))], 0.01, M['steel']))

bpy.context.scene['colliders'] = json.dumps(COL)
print('[alley] tris shell', sum(tris(o) for o in SHELL + SHELL_HI), 'props', sum(tris(o) for o in PROPS), 'neon', sum(tris(o) for o in NEON))


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
    preview(WORK / 'alley_preview.png', (0, 1.65, 0.5), (0, 1.4, -20))
    preview(WORK / 'alley_preview_mid.png', (0.5, 1.65, -18), (0.2, 0.8, -34.5))

if '--bake' in ARGS:
    shell = join(SHELL, 'SHELL'); shellhi = join(SHELL_HI, 'SHELL_HI'); props = join(PROPS, 'PROPS'); neon = join(NEON, 'NEON')
    unwrap(shell, 'lm', margin=0.002); unwrap(shellhi, 'lm', margin=0.004); unwrap(props, 'atlas', margin=0.0015)
    lm = new_float_image('alley_lm', 2048, 2048); lmh = new_float_image('alley_lmhi', 1024, 1024); at = new_float_image('alley_atlas', 2048, 2048)
    bake([shell, shellhi], [lm, lmh], 'lm', 'DIFFUSE')
    bake([props], [at], 'atlas', 'COMBINED')
    lm_mult, lm_img = save_ldr(lm, WORK / 'alley_lm.jpg', pct=99.5, smooth=2)
    lmh_mult, lmh_img = save_ldr(lmh, WORK / 'alley_lmhi.jpg', pct=99.5, smooth=2)
    at_mult, at_img = save_ldr(at, WORK / 'alley_atlas.jpg', pct=99.3)
    for o, img, mult in ((shell, lm_img, lm_mult), (shellhi, lmh_img, lmh_mult)):
        for slot in o.material_slots:
            slot.material = export_mat_lightmapped(slot.material, img, mult)
        strip_uv_except(o, ['UVMap', 'lm'])
    for slot in shell.material_slots:
        if slot.material.name.startswith('LM_ground'):
            slot.material.name = 'LM_WET_ground'
    single_material(props, export_mat_baked('BAKED_props', at_img, 'atlas', at_mult)); strip_uv_except(props, ['atlas'])
    strip_uv_except(neon, [])
    export_glb([shell, shellhi, props, neon], OUT)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / 'alley_baked.blend'))
