"""NEON RAIN environment pass: Harrow's office (prologue), built, lit and baked in Blender, exported to
assets/models/env_office.glb.
Usage: blender -b --python tools/env/office.py -- [--preview] [--bake] [--samples N]
  --preview  Cycles render from the player's start view -> art/env_src/work/office_preview.png
  --bake     bake lightmaps + atlases and export the GLB
Layout (game coords, metres): room x -2.1..2.1, z -4.6 (door/window wall) .. 2.2, ceiling 2.7. Desk centre (0, -0.43),
top 0.78, facing the door; the player starts at (0, 1.65 eye, 1.65) behind the desk chair."""
import sys, json, math, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib, envlib
importlib.reload(envlib)
from envlib import *

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SAMPLES = int(ARGS[ARGS.index('--samples') + 1]) if '--samples' in ARGS else 1024
OUT = ROOT / "assets" / "models" / "env_office.glb"

RW, BACK, FRONT, RH = 2.1, -4.6, 2.2, 2.7
WT = 0.14                                   # wall thickness
DOOR = dict(x0=-1.5, x1=-0.5, h=2.2)
WIN = dict(x0=0.15, x1=1.55, y0=0.8, y1=2.45)
WAINS = 0.95                                 # wainscot height
DESK_Y = 0.78
SLAT_TILT = float(ARGS[ARGS.index('--tilt') + 1]) if '--tilt' in ARGS else -18

reset(SAMPLES)
world_color((0.0018, 0.0024, 0.0042), 1.0)

# ---------------------------------------------------------------- materials
M = dict(
    floor=pbr('floor', 'wood_floor_worn', tint=(0.62, 0.5, 0.42)),
    plaster=pbr('plaster', 'plastered_wall_04', tint=(0.66, 0.62, 0.56)),
    wains=pbr('wains', 'brown_planks_05', tint=(0.34, 0.22, 0.14), normal=0.8),
    trim=pbr('trim', 'black_painted_planks', tint=(0.55, 0.42, 0.32)),
    ceil=pbr('ceil', 'white_plaster_02', tint=(0.5, 0.49, 0.47)),
    hallwall=pbr('hallwall', 'plastered_wall_04', tint=(0.42, 0.46, 0.38)),
    walnut=pbr('walnut', 'black_walnut_veneer_01', tint=(0.42, 0.28, 0.2), rough=0.35),
    leather=pbr('blotter', 'leather_red_02', tint=(0.2, 0.42, 0.24), rough=0.5),
    brass=flat('brass', (0.62, 0.42, 0.16), rough=0.3, metal=1.0),
    darkbrass=flat('darkbrass', (0.3, 0.22, 0.12), rough=0.45, metal=1.0),
    bakelite=flat('bakelite', (0.012, 0.011, 0.01), rough=0.25),
    greenglass=flat('greenglass', (0.03, 0.2, 0.06), rough=0.15, emit=(0.05, 0.6, 0.12), emit_strength=0.12),
    shadein=flat('shadein', (0.8, 0.75, 0.6), rough=0.4),
    bulb=flat('bulb', (1, 0.9, 0.7), emit=INCAND, emit_strength=40.0),
    amber=flat('amberglass', (0.32, 0.1, 0.015), rough=0.08),
    glass=flat('tumbler', (0.5, 0.48, 0.42), rough=0.08),
    whisky=flat('whisky', (0.45, 0.16, 0.02), rough=0.1),
    iron=pbr('iron', 'rusty_metal_02', tint=(0.32, 0.27, 0.22)),
    blind=flat('blind', (0.62, 0.56, 0.45), rough=0.55),
    cord=flat('cord', (0.5, 0.45, 0.35), rough=0.8),
    frame=pbr('frame', 'black_painted_planks', tint=(0.32, 0.24, 0.18)),
    doorglass=imgmat('doorglass', TEX / 'door_glass.png', rough=0.3, emit_strength=0.08),
    hatband=flat('hatband', (0.03, 0.025, 0.02), rough=0.7),
    rug=pbr('rug', 'dirty_carpet', tint=(0.5, 0.18, 0.12), normal=0.5),
)
SHELL, PROPS, DYN, COL = [], [], {}, []


def collide(o_or_box, cover=False, tag='', pad=0.0):
    if isinstance(o_or_box, tuple):
        lo, hi = o_or_box
    else:
        lo, hi = game_bbox(o_or_box)
    COL.append(dict(min=[lo[0] - pad, lo[1], lo[2] - pad], max=[hi[0] + pad, hi[1], hi[2] + pad], cover=cover, tag=tag))


# ---------------------------------------------------------------- shell: floor, ceiling, walls, trim
SHELL.append(box('floor', (-RW, -0.1, BACK), (RW, 0, FRONT), M['floor'], tile=1.6, faces=['+y']))
SHELL.append(box('ceiling', (-RW, RH, BACK), (RW, RH + 0.1, FRONT), M['ceil'], tile=2.0, faces=['-y']))


def wall_x(x, side, z0, z1):  # side: '+x' = inner face points +x
    t = -WT if side == '+x' else WT
    a, b = (x + t, x) if t < 0 else (x, x + t)
    SHELL.append(box('wl', (a, 0, z0), (b, WAINS, z1), M['wains'], tile=1.2, faces=[side], rot90=True))
    SHELL.append(box('wu', (a, WAINS, z0), (b, RH, z1), M['plaster'], tile=1.8, faces=[side]))


def wall_z(z, side, x0, x1, y0=0.0, y1=RH):
    t = -WT if side == '+z' else WT
    a, b = (z + t, z) if t < 0 else (z, z + t)
    if y0 < WAINS:
        SHELL.append(box('wl', (x0, y0, a), (x1, min(WAINS, y1), b), M['wains'], tile=1.2, faces=[side], rot90=True))
    if y1 > WAINS:
        SHELL.append(box('wu', (x0, max(WAINS, y0), a), (x1, y1, b), M['plaster'], tile=1.8, faces=[side]))


wall_x(-RW, '+x', BACK - WT, FRONT + WT)
wall_x(RW, '-x', BACK - WT, FRONT + WT)
wall_z(FRONT, '-z', -RW, RW)
# back wall with the door and the tall window
wall_z(BACK, '+z', -RW, DOOR['x0']); wall_z(BACK, '+z', DOOR['x0'], DOOR['x1'], DOOR['h'], RH)
wall_z(BACK, '+z', DOOR['x1'], WIN['x0']); wall_z(BACK, '+z', WIN['x0'], WIN['x1'], 0, WIN['y0'])
wall_z(BACK, '+z', WIN['x0'], WIN['x1'], WIN['y1'], RH); wall_z(BACK, '+z', WIN['x1'], RW)
# reveals (the wall thickness inside the door and window openings)
SHELL.append(box('rev', (WIN['x0'] - 0.01, WIN['y0'], BACK - WT), (WIN['x0'], WIN['y1'], BACK), M['plaster'], faces=['+x']))
SHELL.append(box('rev', (WIN['x1'], WIN['y0'], BACK - WT), (WIN['x1'] + 0.01, WIN['y1'], BACK), M['plaster'], faces=['-x']))
SHELL.append(box('rev', (WIN['x0'], WIN['y1'], BACK - WT), (WIN['x1'], WIN['y1'] + 0.01, BACK), M['plaster'], faces=['-y']))
for x, s in ((DOOR['x0'], '+x'), (DOOR['x1'], '-x')):
    SHELL.append(box('rev', (x - 0.005, 0, BACK - WT), (x + 0.005, DOOR['h'], BACK), M['trim'], faces=[s]))
SHELL.append(box('rev', (DOOR['x0'], DOOR['h'], BACK - WT), (DOOR['x1'], DOOR['h'] + 0.01, BACK), M['trim'], faces=['-y']))
# baseboard, chair rail, crown, door + window casing
for (x0, x1) in ((-RW, DOOR['x0'] - 0.08), (DOOR['x1'] + 0.08, RW)):
    SHELL.append(box('base', (x0, 0, BACK), (x1, 0.16, BACK + 0.018), M['trim'], tile=1.0, bevel=0.004))
for (x0, x1) in ((-RW, DOOR['x0'] - 0.08), (DOOR['x1'] + 0.08, WIN['x0'] - 0.09), (WIN['x1'] + 0.09, RW)):
    SHELL.append(box('rail', (x0, WAINS - 0.02, BACK), (x1, WAINS + 0.03, BACK + 0.028), M['trim'], bevel=0.006))
SHELL.append(box('base', (-RW, 0, FRONT - 0.018), (RW, 0.16, FRONT), M['trim'], bevel=0.004))
SHELL.append(box('rail', (-RW, WAINS - 0.02, FRONT - 0.028), (RW, WAINS + 0.03, FRONT), M['trim'], bevel=0.006))
for x, s in ((-RW, 1), (RW, -1)):
    a, b = (x, x + 0.018 * s) if s > 0 else (x + 0.018 * s, x)
    SHELL.append(box('base', (a, 0, BACK), (b, 0.16, FRONT), M['trim'], bevel=0.004))
    a, b = (x, x + 0.028 * s) if s > 0 else (x + 0.028 * s, x)
    SHELL.append(box('rail', (a, WAINS - 0.02, BACK), (b, WAINS + 0.03, FRONT), M['trim'], bevel=0.006))
    a, b = (x, x + 0.07 * s) if s > 0 else (x + 0.07 * s, x)
    SHELL.append(box('crown', (a, RH - 0.09, BACK), (b, RH, FRONT), M['trim'], bevel=0.01))
SHELL.append(box('crown', (-RW, RH - 0.09, BACK), (RW, RH, BACK + 0.07), M['trim'], bevel=0.01))
SHELL.append(box('crown', (-RW, RH - 0.09, FRONT - 0.07), (RW, RH, FRONT), M['trim'], bevel=0.01))
for x in (DOOR['x0'] - 0.08, DOOR['x1']):
    SHELL.append(box('casing', (x, 0, BACK), (x + 0.08, DOOR['h'] + 0.08, BACK + 0.03), M['trim'], bevel=0.006))
SHELL.append(box('casing', (DOOR['x0'] - 0.1, DOOR['h'], BACK), (DOOR['x1'] + 0.1, DOOR['h'] + 0.12, BACK + 0.035), M['trim'], bevel=0.008))
for x in (WIN['x0'] - 0.09, WIN['x1']):
    SHELL.append(box('casing', (x, WIN['y0'] - 0.06, BACK), (x + 0.09, WIN['y1'] + 0.09, BACK + 0.03), M['trim'], bevel=0.006))
SHELL.append(box('casing', (WIN['x0'] - 0.11, WIN['y1'], BACK), (WIN['x1'] + 0.11, WIN['y1'] + 0.12, BACK + 0.035), M['trim'], bevel=0.008))
SHELL.append(box('sill', (WIN['x0'] - 0.14, WIN['y0'] - 0.04, BACK - 0.06), (WIN['x1'] + 0.14, WIN['y0'], BACK + 0.12), M['trim'], bevel=0.008))
SHELL.append(box('apron', (WIN['x0'] - 0.08, WIN['y0'] - 0.16, BACK), (WIN['x1'] + 0.08, WIN['y0'] - 0.04, BACK + 0.025), M['trim'], bevel=0.005))
# window sashes (two-over-two, open frame: the glass is a real-time rain shader in the game)
wz = BACK - 0.07
for x in (WIN['x0'], WIN['x1'] - 0.05, (WIN['x0'] + WIN['x1']) / 2 - 0.025):
    PROPS.append(box('sash', (x, WIN['y0'], wz - 0.03), (x + 0.05, WIN['y1'], wz + 0.03), M['frame'], bevel=0.004))
for y in (WIN['y0'], WIN['y1'] - 0.05, (WIN['y0'] + WIN['y1']) / 2 - 0.03, (WIN['y0'] + WIN['y1']) / 2 + 0.03):
    PROPS.append(box('sash', (WIN['x0'], y, wz - 0.03), (WIN['x1'], y + 0.05, wz + 0.03), M['frame'], bevel=0.004))

# ---------------------------------------------------------------- hallway behind the door (seen when Vela comes in)
HX0, HX1, HZ0 = -2.0, 0.0, -7.8
SHELL.append(box('hfloor', (HX0, -0.1, HZ0), (HX1, 0, BACK - WT), M['floor'], tile=1.6, faces=['+y']))
SHELL.append(box('hceil', (HX0, 2.6, HZ0), (HX1, 2.7, BACK - WT), M['ceil'], tile=2.0, faces=['-y']))
for x, s in ((HX0, '+x'), (HX1, '-x')):
    a, b = (x - 0.1, x) if s == '+x' else (x, x + 0.1)
    SHELL.append(box('hw', (a, 0, HZ0), (b, 1.0, BACK - WT), M['wains'], tile=1.2, faces=[s], rot90=True))
    SHELL.append(box('hw', (a, 1.0, HZ0), (b, 2.6, BACK - WT), M['hallwall'], tile=1.8, faces=[s]))
SHELL.append(box('hw', (HX0, 0, HZ0 - 0.1), (HX1, 1.0, HZ0), M['wains'], tile=1.2, faces=['+z'], rot90=True))
SHELL.append(box('hw', (HX0, 1.0, HZ0 - 0.1), (HX1, 2.6, HZ0), M['hallwall'], tile=1.8, faces=['+z']))
SHELL.append(box('hback', (HX0, 0, BACK - WT - 0.05), (DOOR['x0'], RH, BACK - WT), M['hallwall'], faces=['-z']))
SHELL.append(box('hback', (DOOR['x1'], 0, BACK - WT - 0.05), (HX1, RH, BACK - WT), M['hallwall'], faces=['-z']))
# a neighbour's door across the hall + its casing
PROPS.append(box('hdoor', (-1.45, 0, HZ0), (-0.55, 2.15, HZ0 + 0.04), M['walnut'], tile=0.8, bevel=0.006))
PROPS.append(box('hdoorpane', (-1.32, 1.2, HZ0 + 0.04), (-0.68, 1.9, HZ0 + 0.045), M['doorglass']))
PROPS.append(cyl('hknob', (-0.62, 1.0, HZ0 + 0.04), 0.03, 0.06, M['brass'], axis='Z'))
hb = lathe('hbulb', [(0, 0), (0.035, 0.01), (0.04, 0.05), (0.02, 0.09), (0.012, 0.11), (0, 0.11)], (-1.0, 2.49, -6.3), M['bulb'])
PROPS.append(hb)
PROPS.append(cyl('hsock', (-1.0, 2.58, -6.3), 0.025, 0.03, M['darkbrass']))
PROPS.append(cyl('hcord', (-1.0, 2.6, -6.3), 0.005, 0.1, M['bakelite'], seg=6))

# ---------------------------------------------------------------- the desk (walnut pedestal desk, knee hole toward Harrow)
dz0, dz1 = -0.86, 0.0
desk = [box('dtop', (-0.8, DESK_Y - 0.035, dz0), (0.8, DESK_Y, dz1), M['walnut'], tile=0.9, bevel=0.008)]
for s in (-1, 1):
    x0, x1 = (-0.77, -0.33) if s < 0 else (0.33, 0.77)
    desk.append(box('dped', (x0, 0.06, dz0 + 0.02), (x1, DESK_Y - 0.035, dz1 - 0.04), M['walnut'], tile=0.9, bevel=0.005))
    desk.append(box('dplinth', (x0 + 0.015, 0, dz0 + 0.035), (x1 - 0.015, 0.06, dz1 - 0.055), M['trim'], bevel=0.003))
    for k, (y0, y1) in enumerate(((0.08, 0.32), (0.34, 0.52), (0.54, 0.7))):
        desk.append(box('ddrawer', (x0 + 0.025, y0, dz1 - 0.04), (x1 - 0.025, y1, dz1 - 0.022), M['walnut'], tile=0.9, bevel=0.006))
        cx = (x0 + x1) / 2
        desk.append(box('dpull', (cx - 0.05, (y0 + y1) / 2 - 0.008, dz1 - 0.022), (cx + 0.05, (y0 + y1) / 2 + 0.008, dz1 - 0.008), M['brass'], bevel=0.004))
desk.append(box('dcenter', (-0.31, 0.64, dz1 - 0.04), (0.31, DESK_Y - 0.04, dz1 - 0.022), M['walnut'], tile=0.9, bevel=0.005))
desk.append(box('dpullc', (-0.06, 0.693, dz1 - 0.022), (0.06, 0.707, dz1 - 0.01), M['brass'], bevel=0.004))
desk.append(box('dmodesty', (-0.34, 0.25, dz0 + 0.02), (0.34, DESK_Y - 0.035, dz0 + 0.045), M['walnut'], tile=0.9, bevel=0.004))
desk.append(box('dblotter', (-0.36, DESK_Y, -0.66), (0.36, DESK_Y + 0.006, -0.16), M['leather'], tile=0.5, bevel=0.002))
for x in (-0.36, 0.33):
    desk.append(box('dcorner', (x, DESK_Y, -0.66), (x + 0.03, DESK_Y + 0.009, -0.16), M['bakelite'], bevel=0.002))
PROPS += desk
collide(((-0.8, 0, dz0), (0.8, DESK_Y, dz1)), cover=True, tag='desk')

# banker's lamp (brass base, green glass shade), back-left corner of the desk
LX, LZ = -0.52, -0.7
PROPS.append(lathe('lbase', [(0, 0), (0.085, 0), (0.088, 0.012), (0.07, 0.022), (0.03, 0.03), (0.012, 0.04), (0, 0.04)], (LX, DESK_Y, LZ), M['brass']))
PROPS.append(cyl('lstem', (LX, DESK_Y + 0.03, LZ), 0.007, 0.26, M['brass'], seg=10))
PROPS.append(box('lyoke', (LX - 0.11, DESK_Y + 0.28, LZ - 0.006), (LX + 0.11, DESK_Y + 0.292, LZ + 0.006), M['brass'], bevel=0.003))
for x in (LX - 0.11, LX + 0.105):
    PROPS.append(box('lyoke2', (x, DESK_Y + 0.28, LZ - 0.006), (x + 0.006, DESK_Y + 0.33, LZ + 0.006), M['brass']))
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.075, radius2=0.075, depth=0.27)
bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context='VERTS')
bmesh.ops.translate(bm, verts=bm.verts, vec=G(LX, DESK_Y + 0.31, LZ + 0.03))
shade = mesh_obj('lshade', bm, M['greenglass']); box_uv(shade, 0.3)
sol = shade.modifiers.new('s', 'SOLIDIFY'); sol.thickness = 0.004; select_only([shade]); bpy.ops.object.modifier_apply(modifier='s')
for p in shade.data.polygons:
    p.use_smooth = True
PROPS.append(shade)
lbulb = lathe('lbulb', [(0, 0), (0.016, 0.0), (0.016, 0.07), (0, 0.07)], (LX - 0.035, DESK_Y + 0.29, LZ + 0.03), M['bulb'], seg=10)
lbulb.rotation_euler = (0, math.pi / 2, 0); lbulb.location = G(LX - 0.035, DESK_Y + 0.295, LZ + 0.03); apply_xform(lbulb)
PROPS.append(lbulb)
PROPS.append(cyl('lchain', (LX + 0.05, DESK_Y + 0.17, LZ + 0.09), 0.002, 0.14, M['brass'], seg=4))

# candlestick telephone, ashtray, lighter, whisky-free desk
TX, TZ = 0.55, -0.66
PROPS.append(lathe('tbase', [(0, 0), (0.06, 0), (0.06, 0.012), (0.05, 0.03), (0.016, 0.05), (0.014, 0.26), (0, 0.26)], (TX, DESK_Y, TZ), M['bakelite']))
PROPS.append(lathe('tmouth', [(0, 0), (0.018, 0.0), (0.03, 0.05), (0.032, 0.06), (0, 0.06)], (TX, DESK_Y + 0.25, TZ), M['bakelite']))
rec = lathe('treceiver', [(0, 0), (0.012, 0), (0.024, 0.03), (0.026, 0.06), (0.012, 0.075), (0.01, 0.12), (0, 0.12)], (TX + 0.05, DESK_Y + 0.12, TZ), M['bakelite'])
PROPS.append(rec)
PROPS.append(box('thook', (TX + 0.012, DESK_Y + 0.2, TZ - 0.005), (TX + 0.055, DESK_Y + 0.21, TZ + 0.005), M['brass']))
PROPS.append(tube_path('tcord', [(TX, DESK_Y + 0.01, TZ + 0.05), (TX + 0.05, DESK_Y + 0.004, TZ + 0.15), (TX + 0.18, DESK_Y + 0.004, TZ + 0.12), (TX + 0.26, DESK_Y - 0.1, TZ + 0.05)], 0.004, M['bakelite']))
PROPS.append(lathe('ashtray', [(0, 0.0), (0.072, 0.0), (0.084, 0.024), (0.076, 0.027), (0.062, 0.009), (0, 0.009)], (0.3, DESK_Y, -0.62), M['darkbrass'], smooth=False))
for k in range(3):
    a = k * 2.094
    PROPS.append(cyl('butt', (0.3 + 0.035 * math.cos(a), DESK_Y + 0.012, -0.62 + 0.035 * math.sin(a)), 0.0045, 0.03, M['shadein'], seg=6, axis='X'))

# ---------------------------------------------------------------- Poly Haven furniture
chair = ph('modern_arm_chair_01', (0.98, 0, 0.82), ry_deg=148, target=4500)
PROPS.append(chair); collide(chair, tag='chair', pad=-0.06)
client = ph('GreenChair_01', (0.72, 0, -1.48), ry_deg=-15, target=3500)
PROPS.append(client); collide(client, tag='chair', pad=-0.05)
fc1 = ph('vintage_wooden_drawer_01', (1.86, 0, -3.62), ry_deg=-90, target=2600)
fc2 = dup(fc1, (1.86, 0.55, -3.62), 0)

PROPS += [fc1, fc2]; collide(((1.62, 0, -4.06), (2.1, 1.1, -3.18)), cover=True, tag='cabinet')
shelf = ph('wooden_bookshelf_worn', (1.8, 0, -0.25), ry_deg=-90, target=3600)
PROPS.append(shelf); collide(shelf, cover=True, tag='shelf')
# books on the shelves: probe the shelf boards with downward rays
sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
levels, y = [], 2.0
while y > 0.05:
    hit, loc, n, *_ = sc.ray_cast(dg, G(1.82, y, -0.25), Vector((0, 0, -1)))
    if not hit:
        break
    levels.append(loc.z); y = loc.z - 0.05
print('[office] shelf boards', [round(v, 2) for v in levels])
books = ph('book_encyclopedia_set_01', (0, 0, 0), target=3000)
for i, yb in enumerate(levels[1:5]):
    if i == 1:
        continue
    b = dup(books, (1.84, yb, -0.25 + (0.08 if i % 2 else -0.06)), ry_deg=-90)
    PROPS.append(b)
bpy.data.objects.remove(books, do_unlink=True)
sofa = ph('Sofa_01', (-1.76, 0, 1.0), ry_deg=90, target=4000)
PROPS.append(sofa); collide(sofa, cover=True, tag='sofa', pad=-0.04)
st = ph('side_table_01', (-1.82, 0, -4.05), ry_deg=90, target=1500)
PROPS.append(st); collide(st, tag='table')
pic = ph('hanging_picture_frame_01', (-2.08, 1.7, 1.0), ry_deg=90, target=1200)
PROPS.append(pic)
sp = ph('standing_picture_frame_01', (-0.22, DESK_Y, -0.76), ry_deg=20, target=800)
PROPS.append(sp)
pads = ph('office_notepads', (0, 0, 0), keep=['a4_stack', 'note_stack'], target=600)
pads.location = G(0.14, DESK_Y + 0.006, -0.45); pads.rotation_euler = (0, 0, math.radians(12)); apply_xform(pads)
PROPS.append(pads)
clip = ph('clipboard', (0.42, DESK_Y + 0.006, -0.32), ry_deg=-70, target=900)
PROPS.append(clip)
binder = ph('binder_notebook', (0, 0, 0), keep=['binder_notebook_closed'], target=1500)
binder.location = G(-1.82, 0.555, -4.05); apply_xform(binder); PROPS.append(binder)
lighter = ph('vintage_lighter', (0.43, DESK_Y + 0.035, -0.5), ry_deg=30, target=800, keep=['body', 'hammer', 'hinge'])
PROPS.append(lighter)
fan = ph('ceiling_fan', (0.2, RH, -1.9), target=3000, drop=['blades'])
blades = ph('ceiling_fan', (0.2, RH, -1.9), target=1500, keep=['blades'], name='fan_blades')
PROPS.append(fan); DYN['fan_blades'] = (blades, 256, (0.2, None, -1.9))

# whisky + glass on the filing cabinet
PROPS.append(lathe('bottle', [(0, 0), (0.042, 0), (0.044, 0.006), (0.044, 0.17), (0.03, 0.205), (0.013, 0.225), (0.013, 0.28), (0.016, 0.29), (0, 0.29)], (1.86, 1.1, -3.85), M['amber']))
PROPS.append(lathe('glass', [(0, 0), (0.036, 0), (0.04, 0.085), (0.036, 0.085), (0.032, 0.008), (0, 0.008)], (1.8, 1.1, -3.55), M['glass'], smooth=False))
PROPS.append(cyl('whisky', (1.8, 1.108, -3.55), 0.033, 0.025, M['whisky']))

# coat rack (front-right corner) with a hat hook; the fedora itself is the game's model
CRX, CRZ = 1.78, 1.86
PROPS.append(cyl('crpole', (CRX, 0.04, CRZ), 0.022, 1.74, M['walnut'], seg=12))
PROPS.append(lathe('crtop', [(0, 0), (0.03, 0), (0.035, 0.03), (0, 0.06)], (CRX, 1.78, CRZ), M['walnut']))
for a in range(4):
    r = math.radians(45 + 90 * a)
    PROPS.append(box_rot('crfoot', (CRX + 0.16 * math.cos(r), 0.03, CRZ + 0.16 * math.sin(r)), (0.36, 0.04, 0.05), 0, -math.degrees(r), M['walnut'], bevel=0.01))
    PROPS.append(tube_path('crhook', [(CRX + 0.02 * math.cos(r), 1.62, CRZ + 0.02 * math.sin(r)), (CRX + 0.12 * math.cos(r), 1.66, CRZ + 0.12 * math.sin(r)), (CRX + 0.15 * math.cos(r), 1.72, CRZ + 0.15 * math.sin(r))], 0.007, M['brass']))
collide(((CRX - 0.2, 0, CRZ - 0.2), (CRX + 0.2, 1.8, CRZ + 0.2)), tag='rack')

# cast-iron radiator under the window
for i in range(15):
    x = 0.3 + i * 0.077
    PROPS.append(box('radfin', (x, 0.1, BACK + 0.04), (x + 0.06, 0.66, BACK + 0.15), M['iron'], tile=0.4, bevel=0.012))
PROPS.append(box('radpipe', (0.28, 0.12, BACK + 0.07), (1.44, 0.16, BACK + 0.12), M['iron'], tile=0.4, bevel=0.01))
PROPS.append(cyl('radvalve', (0.22, 0.0, BACK + 0.1), 0.02, 0.2, M['iron']))
collide(((0.25, 0, BACK), (1.45, 0.66, BACK + 0.16)), tag='radiator')

# rug under the desk
PROPS.append(box('rug', (-1.3, 0, -2.2), (1.3, 0.008, 1.2), M['rug'], tile=1.2, bevel=0.003))

# venetian blinds: tilted slats (open about 35 degrees), head rail, ladder tapes, pull cord
BZ = BACK + 0.06
PROPS.append(box('bhead', (WIN['x0'] + 0.02, WIN['y1'] - 0.06, BZ - 0.035), (WIN['x1'] - 0.02, WIN['y1'] - 0.01, BZ + 0.035), M['blind'], bevel=0.004))
y = WIN['y1'] - 0.1
while y > WIN['y0'] + 0.32:
    PROPS.append(box_rot('slat', ((WIN['x0'] + WIN['x1']) / 2, y, BZ), (WIN['x1'] - WIN['x0'] - 0.06, 0.003, 0.05), SLAT_TILT, 0, M['blind']))
    y -= 0.055
PROPS.append(box('bbottom', (WIN['x0'] + 0.03, y - 0.01, BZ - 0.025), (WIN['x1'] - 0.03, y + 0.01, BZ + 0.025), M['blind'], bevel=0.003))
for x in (WIN['x0'] + 0.25, WIN['x1'] - 0.25):
    for dz in (-0.024, 0.024):
        PROPS.append(box('ladder', (x - 0.006, y, BZ + dz - 0.001), (x + 0.006, WIN['y1'] - 0.06, BZ + dz + 0.001), M['cord']))
PROPS.append(box('pullcord', (WIN['x1'] - 0.08, 1.3, BZ + 0.03), (WIN['x1'] - 0.075, WIN['y1'] - 0.06, BZ + 0.035), M['cord']))
PROPS.append(lathe('pullknob', [(0, 0), (0.008, 0.005), (0.008, 0.03), (0, 0.035)], (WIN['x1'] - 0.0775, 1.27, BZ + 0.0325), M['walnut'], seg=8))

# the office door (dynamic: swings open in the game). Origin = hinge on the left jamb.
dleaf = [box('dleaf', (DOOR['x0'] + 0.01, 0, BACK - 0.07), (DOOR['x1'] - 0.01, DOOR['h'] - 0.01, BACK - 0.025), M['walnut'], tile=0.9, bevel=0.006)]
for (y0, y1) in ((0.12, 0.95),):
    dleaf.append(box('dpanel', (DOOR['x0'] + 0.12, y0, BACK - 0.025), (DOOR['x1'] - 0.12, y1, BACK - 0.012), M['walnut'], tile=0.9, bevel=0.012))
pane = box('dpane', (DOOR['x0'] + 0.13, 1.1, BACK - 0.026), (DOOR['x1'] - 0.13, 2.02, BACK - 0.02), M['doorglass'])
fit_uv(pane, 'z'); dleaf.append(pane)
for (x0, x1, y0, y1) in ((DOOR['x0'] + 0.1, DOOR['x1'] - 0.1, 1.07, 1.1), (DOOR['x0'] + 0.1, DOOR['x1'] - 0.1, 2.02, 2.05),
                         (DOOR['x0'] + 0.1, DOOR['x0'] + 0.13, 1.07, 2.05), (DOOR['x1'] - 0.13, DOOR['x1'] - 0.1, 1.07, 2.05)):
    dleaf.append(box('dbead', (x0, y0, BACK - 0.025), (x1, y1, BACK - 0.008), M['walnut'], bevel=0.004))
dleaf.append(cyl('dknob', (DOOR['x1'] - 0.09, 1.0, BACK - 0.025), 0.028, 0.06, M['brass'], axis='Z'))
dleaf.append(box('dplate', (DOOR['x1'] - 0.115, 0.92, BACK - 0.026), (DOOR['x1'] - 0.065, 1.1, BACK - 0.02), M['brass'], bevel=0.003))
door = join(dleaf, 'door')
set_origin(door, (DOOR['x0'] + 0.01, 0, BACK - 0.045))
DYN['door'] = (door, 512, None)

# walls as colliders (the door collider is the game's)
for c in (((-RW - 0.3, 0, BACK - 0.3), (-RW, RH, FRONT + 0.3)), ((RW, 0, BACK - 0.3), (RW + 0.3, RH, FRONT + 0.3)),
          ((-RW, 0, FRONT), (RW, RH, FRONT + 0.3)), ((-RW, 0, BACK - WT), (DOOR['x0'], RH, BACK)),
          ((DOOR['x1'], 0, BACK - WT), (RW, RH, BACK)), ((HX0 - 0.3, 0, HZ0 - 0.3), (HX0, RH, BACK)), ((HX1, 0, HZ0 - 0.3), (HX1 + 0.3, RH, BACK)),
          ((HX0, 0, HZ0 - 0.3), (HX1, RH, HZ0))):
    COL.append(dict(min=list(c[0]), max=list(c[1]), cover=False, tag='wall'))

# ---------------------------------------------------------------- lights: sodium street lamp + neon signs outside, desk lamp, hall bulb
KEY_POS, KEY_AIM = (2.2, 3.66, -11.3), (0.0, 0.8, -0.4)
light('SPOT', KEY_POS, SODIUM_HP, 7000, radius=0.05, gaim=KEY_AIM, spot_deg=16, blend=0.35, name='sodium_key')
light('AREA', (0.7, 0.2, -6.2), NEON_RED, 28, gaim=(0.5, 2.7, -2.0), size=(1.4, 0.2), name='neon_red')
light('AREA', (2.8, 1.6, -6.6), NEON_TEAL, 40, gaim=(-1.5, 1.2, -1.0), size=(0.6, 0.15), name='neon_teal')
light('AREA', (0.8, 4.5, -9.0), SODIUM_HP, 40, gaim=(0.8, 0.0, -4.6), size=(6, 3), name='sodium_sky')
light('POINT', (LX - 0.0, DESK_Y + 0.295, LZ + 0.03), INCAND, 9, radius=0.015, name='desk_lamp')
light('POINT', (-1.0, 2.44, -6.3), INCAND, 28, radius=0.03, name='hall_bulb')
light('POINT', (-1.0, 1.6, -7.6), INCAND, 2.5, radius=0.2, name='hall_fill')

bpy.context.scene['colliders'] = json.dumps(COL)
print('[office] tris shell', sum(tris(o) for o in SHELL), 'props', sum(tris(o) for o in PROPS), 'dyn', {k: tris(v[0]) for k, v in DYN.items()})


# ---------------------------------------------------------------- preview render from the player's start view
def preview(path, eye=(0.0, 1.65, 1.65), look=(0.35, 1.25, -4.6), res=(390, 844), samples=96):
    cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); link(cam)
    cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(74); cd.clip_start = 0.05
    cam.location = G(*eye); d = (G(*look) - cam.location).normalized(); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc = bpy.context.scene; sc.camera = cam; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    old = sc.cycles.samples; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.view_settings.exposure = 0.8
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    sc.cycles.samples = old; sc.cycles.use_denoising = False
    bpy.data.objects.remove(cam)


if '--preview' in ARGS:
    preview(WORK / 'office_preview.png')
    preview(WORK / 'office_preview_desk.png', eye=(-0.9, 1.65, -3.2), look=(0.0, 0.7, 0.4))
    preview(WORK / 'office_preview_floor.png', eye=(-1.2, 1.65, 0.8), look=(0.6, 0.2, -3.0))

if '--bake' in ARGS:
    shell = join(SHELL, 'SHELL'); props = join(PROPS, 'PROPS')
    unwrap(shell, 'lm', margin=0.003); unwrap(props, 'atlas', margin=0.002)
    lm = new_float_image('office_lm', 2048, 2048); at = new_float_image('office_atlas', 2048, 2048)
    bake([shell], [lm], 'lm', 'DIFFUSE')
    bake([props], [at], 'atlas', 'COMBINED')
    dimgs = {}
    for k, (o, size, _) in DYN.items():
        unwrap(o, 'atlas', margin=0.004); im = new_float_image('office_' + k, size, size * (2 if k == 'door' else 1)); dimgs[k] = im
        bake([o], [im], 'atlas', 'COMBINED')
    # one exposure for everything baked (lightmap is irradiance, the atlases already include albedo)
    lm_mult, lm_img = save_ldr(lm, WORK / 'office_lm.jpg', pct=99.8)
    at_mult, at_img = save_ldr(at, WORK / 'office_atlas.jpg', pct=99.6)
    for k, (o, size, _) in DYN.items():
        m, im = save_ldr(dimgs[k], WORK / f'office_{k}.jpg', scale=1 / at_mult)
        single_material(o, export_mat_baked('BAKED_' + k, im, 'atlas', at_mult)); strip_uv_except(o, ['atlas'])
    # shell: per-material lightmapped export materials
    for i, slot in enumerate(shell.material_slots):
        slot.material = export_mat_lightmapped(slot.material, lm_img, lm_mult)
    strip_uv_except(shell, ['UVMap', 'lm'])
    single_material(props, export_mat_baked('BAKED_props', at_img, 'atlas', at_mult)); strip_uv_except(props, ['atlas'])
    for k, (o, size, piv) in DYN.items():
        if piv:
            lo, hi = bbox(o); set_origin(o, (piv[0], (lo.z + hi.z) / 2, piv[2]))
    export_glb([shell, props] + [v[0] for v in DYN.values()], OUT)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK / 'office_baked.blend'))
