"""NEON RAIN first-person viewmodel: a 1940s 1911-pattern .45 service pistol (generic, no marks) in the right hand (trench-coat
sleeve), and a gloved left hand holding a cigarette. Procedural materials (blued steel with edge wear, walnut grip,
dark leather glove, wool coat, paper) baked with AO into one 1k base-colour atlas. Exports assets/models/vm_1911.glb (the .38 revolver build is kept in viewmodel_38.py.bak).

Blender axes: x right, y forward (muzzle), z up. glTF export (+Y up) maps this to three: x right, -z forward, y up.
Nodes: rig_r > pistol > slide > eject, pistol > hammer, magazine, muzzle; rig_r > casing; rig_r > hand_r, sleeve_r; rig_l > hand_l, sleeve_l, cig > cig_tip.
Usage: blender -b --python tools/env/viewmodel.py"""
import bpy, bmesh, math, pathlib
from mathutils import Vector, Matrix

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models" / "vm_1911.glb"
TEXP = ROOT / "art" / "vm_atlas.png"
RES = 1024
BORE = 0.03  # bore axis height (z)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 64


def link(o):
    sc.collection.objects.link(o); return o


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))


def activate(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o


def apply_mods(o):
    activate(o)
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def bevel(o, w, seg=2, angle=40):
    m = o.modifiers.new("bev", 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'; m.angle_limit = math.radians(angle)
    return m


def cyl(name, r1, r2, length, seg, axis='Y', at=(0, 0, 0), caps=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=length)
    rot = {'Y': Matrix.Rotation(-math.pi / 2, 4, 'X'), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Z': Matrix.Identity(4)}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(at) @ rot, verts=bm.verts)
    return mesh_obj(name, bm)


def box(name, mn, mx):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    c = [(a + b) / 2 for a, b in zip(mn, mx)]; s = [b - a for a, b in zip(mn, mx)]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ Matrix.Diagonal((*s, 1)), verts=bm.verts)
    return mesh_obj(name, bm)


def profile_x(name, pts_yz, width, x0=0.0):
    """Extrude a closed (y, z) outline along x, centred on x0."""
    bm = bmesh.new()
    vs = [bm.verts.new((x0 - width / 2, y, z)) for y, z in pts_yz]
    f = bm.faces.new(vs); bmesh.ops.recalc_face_normals(bm, faces=[f])
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(width, 0, 0), verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)


def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new("b", 'BOOLEAN'); m.object = cutter; m.operation = op; m.solver = 'EXACT'
    apply_mods(o); bpy.data.objects.remove(cutter)


def join(objs, name):
    activate(objs[0])
    for o in objs: o.select_set(True)
    bpy.ops.object.join(); o = bpy.context.object; o.name = name; o.data.name = name; return o


def tube_curve(name, pts, r, flat=1.0):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 2; cu.resolution_u = 6
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = link(bpy.data.objects.new(name, cu)); activate(o); bpy.ops.object.convert(target='MESH')
    o = bpy.context.object; o.scale.x = flat; bpy.ops.object.transform_apply(scale=True); return o


def smooth(o, angle=35):
    activate(o); bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))


def set_origin(o, p):
    p = Vector(p); o.data.transform(Matrix.Translation(-p)); o.location = p


# ================================================================ materials (procedural, for the bake)
def mat(name, build):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']; build(nt, bsdf); return m


def n(nt, t, **kw):
    node = nt.nodes.new(t)
    for k, v in kw.items(): setattr(node, k, v)
    return node


def ramp(nt, stops):
    r = n(nt, 'ShaderNodeValToRGB'); e = r.color_ramp.elements
    e[0].position, e[0].color = stops[0]; e[1].position, e[1].color = stops[1]
    for p, c in stops[2:]:
        el = e.new(p); el.color = c
    return r


def steel_build(nt, b):
    L = nt.links
    geo = n(nt, 'ShaderNodeNewGeometry')
    wear = ramp(nt, [(0.6, (0, 0, 0, 1)), (0.72, (1, 1, 1, 1))])
    L.new(geo.outputs['Pointiness'], wear.inputs['Fac'])
    noi = n(nt, 'ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 260; noi.inputs['Detail'].default_value = 6
    blued = n(nt, 'ShaderNodeMix', data_type='RGBA'); blued.inputs['A'].default_value = (0.12, 0.125, 0.115, 1); blued.inputs['B'].default_value = (0.17, 0.175, 0.16, 1)
    L.new(noi.outputs['Fac'], blued.inputs['Factor'])
    mix = n(nt, 'ShaderNodeMix', data_type='RGBA'); mix.inputs['B'].default_value = (0.34, 0.33, 0.31, 1)
    L.new(blued.outputs['Result'], mix.inputs['A']); L.new(wear.outputs['Color'], mix.inputs['Factor'])
    L.new(mix.outputs['Result'], b.inputs['Base Color'])


def wood_build(nt, b):
    L = nt.links
    tc = n(nt, 'ShaderNodeTexCoord'); mp = n(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (60, 6, 6)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    w = n(nt, 'ShaderNodeTexWave'); w.inputs['Scale'].default_value = 1.2; w.inputs['Distortion'].default_value = 6; w.inputs['Detail'].default_value = 3
    L.new(mp.outputs['Vector'], w.inputs['Vector'])
    grain = ramp(nt, [(0.0, (0.09, 0.035, 0.014, 1)), (1.0, (0.23, 0.10, 0.045, 1))])
    L.new(w.outputs['Fac'], grain.inputs['Fac'])
    # checkering: two crossed fine waves darken a diamond grid
    mp2 = n(nt, 'ShaderNodeMapping'); mp2.inputs['Rotation'].default_value = (math.radians(45), 0, 0)
    L.new(tc.outputs['Object'], mp2.inputs['Vector'])
    c1 = n(nt, 'ShaderNodeTexWave', bands_direction='Y'); c1.inputs['Scale'].default_value = 520
    c2 = n(nt, 'ShaderNodeTexWave', bands_direction='Z'); c2.inputs['Scale'].default_value = 520
    for c in (c1, c2): L.new(mp2.outputs['Vector'], c.inputs['Vector'])
    mul = n(nt, 'ShaderNodeMath', operation='MULTIPLY'); L.new(c1.outputs['Fac'], mul.inputs[0]); L.new(c2.outputs['Fac'], mul.inputs[1])
    chk = n(nt, 'ShaderNodeMix', data_type='RGBA'); chk.inputs['B'].default_value = (0.03, 0.012, 0.005, 1)
    inv = n(nt, 'ShaderNodeMath', operation='MULTIPLY'); inv.inputs[1].default_value = 0.55
    L.new(mul.outputs[0], inv.inputs[0]); L.new(inv.outputs[0], chk.inputs['Factor'])
    L.new(grain.outputs['Color'], chk.inputs['A']); L.new(chk.outputs['Result'], b.inputs['Base Color'])


def flat_noise_build(c1, c2, scale, pointy=None):
    def f(nt, b):
        L = nt.links
        noi = n(nt, 'ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = scale; noi.inputs['Detail'].default_value = 8
        mx = n(nt, 'ShaderNodeMix', data_type='RGBA'); mx.inputs['A'].default_value = c1; mx.inputs['B'].default_value = c2
        L.new(noi.outputs['Fac'], mx.inputs['Factor'])
        out = mx
        if pointy:  # scuffed highlights on convex edges (knuckles, cuff fold)
            geo = n(nt, 'ShaderNodeNewGeometry'); r = ramp(nt, [(0.5, (0, 0, 0, 1)), (0.58, (1, 1, 1, 1))]); L.new(geo.outputs['Pointiness'], r.inputs['Fac'])
            m2 = n(nt, 'ShaderNodeMix', data_type='RGBA'); m2.inputs['B'].default_value = pointy
            fac = n(nt, 'ShaderNodeMath', operation='MULTIPLY'); fac.inputs[1].default_value = 0.6
            L.new(r.outputs['Color'], fac.inputs[0]); L.new(fac.outputs[0], m2.inputs['Factor'])
            L.new(mx.outputs['Result'], m2.inputs['A']); out = m2
        L.new(out.outputs['Result'], b.inputs['Base Color'])
    return f


M_STEEL = mat("steel", steel_build)
M_WOOD = mat("walnut", wood_build)
M_GLOVE = mat("glove", flat_noise_build((0.045, 0.026, 0.016, 1), (0.075, 0.045, 0.028, 1), 140, (0.16, 0.11, 0.075, 1)))
M_COAT = mat("coat", flat_noise_build((0.030, 0.027, 0.023, 1), (0.05, 0.045, 0.038, 1), 400, (0.08, 0.072, 0.06, 1)))
M_PAPER = mat("paper", flat_noise_build((0.62, 0.64, 0.66, 1), (0.72, 0.74, 0.76, 1), 80))
M_EMBER = mat("ember", flat_noise_build((0.25, 0.06, 0.01, 1), (0.6, 0.18, 0.03, 1), 60))


def give(o, m):
    o.data.materials.clear(); o.data.materials.append(m)


# ================================================================ pistol: 1911-pattern .45 service pistol (generic, no marks)
B = BORE
def M_BRASS_build(nt, b):
    L = nt.links
    noi = n(nt, 'ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 300
    mx = n(nt, 'ShaderNodeMix', data_type='RGBA'); mx.inputs['A'].default_value = (0.42, 0.26, 0.07, 1); mx.inputs['B'].default_value = (0.62, 0.42, 0.14, 1)
    L.new(noi.outputs['Fac'], mx.inputs['Factor']); L.new(mx.outputs['Result'], b.inputs['Base Color'])
M_BRASS = mat("brass", M_BRASS_build)

# slide: taller at the front (recoil-spring tunnel), sights, rear serrations, ejection port on the right
slide = profile_x("slide", [(-0.090, B - 0.011), (0.000, B - 0.011), (0.004, B - 0.020), (0.110, B - 0.020), (0.110, B + 0.012), (0.106, B + 0.016),
                            (-0.086, B + 0.016), (-0.090, B + 0.012)], 0.023)
cut = [box("ser", (sx * 0.0103 - 0.003, -0.087 + k * 0.0034, B - 0.008), (sx * 0.0103 + 0.003, -0.087 + k * 0.0034 + 0.0013, B + 0.013)) for k in range(9) for sx in (-1, 1)]
cut.append(box("port", (0.0045, -0.024, B + 0.002), (0.03, 0.016, B + 0.03)))
cut.append(box("tunnel", (-0.006, -0.03, B - 0.0072), (0.006, 0.12, B + 0.0072)))  # barrel channel so the barrel shows in the port
boolean(slide, join(cut, "cutters"))
rs = box("rsight", (-0.005, -0.086, B + 0.015), (0.005, -0.076, B + 0.0205))
fs = profile_x("fsight", [(0.097, B + 0.015), (0.106, B + 0.015), (0.105, B + 0.0215), (0.100, B + 0.0215)], 0.003)
plug = cyl("plug", 0.0052, 0.0052, 0.004, 16, 'Y', (0, 0.111, B - 0.0135))
bush = cyl("bush", 0.0088, 0.0088, 0.005, 20, 'Y', (0, 0.1115, B))
slide = join([slide, rs, fs, plug, bush], "slide_j"); bevel(slide, 0.0011, 2, 35); apply_mods(slide); give(slide, M_STEEL)
# barrel (static, frame-mounted): crown at the muzzle, hood under the port
barrel = cyl("barrel", 0.0072, 0.0072, 0.146, 20, 'Y', (0, 0.041, B))
boolean(barrel, cyl("bore", 0.0058, 0.0058, 0.02, 16, 'Y', (0, 0.114, B)))
give(barrel, M_STEEL)

# frame: dust cover, square trigger guard, grip, beavertail grip-safety tang
frame = profile_x("frame", [(-0.072, B - 0.011), (0.0, B - 0.011), (0.0, B - 0.020), (0.084, B - 0.020), (0.084, B - 0.028), (0.030, B - 0.028), (0.030, B - 0.047),
                            (0.024, B - 0.053), (-0.028, B - 0.053), (-0.034, B - 0.048), (-0.050, B - 0.124), (-0.052, B - 0.130), (-0.090, B - 0.130), (-0.093, B - 0.124),
                            (-0.078, B - 0.040), (-0.084, B - 0.024), (-0.095, B - 0.016), (-0.091, B - 0.008), (-0.080, B - 0.009)], 0.021)
boolean(frame, box("guardwin", (-0.06, -0.024, B - 0.048), (0.06, 0.025, B - 0.029)))
boolean(frame, box("magwell", (-0.009, -0.088, B - 0.135), (0.009, -0.054, B - 0.127)))
bevel(frame, 0.0012, 2, 35); apply_mods(frame)
trig = box("trigger", (-0.004, 0.003, B - 0.044), (0.004, 0.009, B - 0.029)); bevel(trig, 0.0012, 2); apply_mods(trig)
tsafe = join([box("ts", (-0.0138, -0.080, B - 0.016), (-0.0105, -0.060, B - 0.010)), box("tsp", (-0.0145, -0.066, B - 0.013), (-0.0105, -0.056, B - 0.008))], "tsafe")
sstop = join([box("ss", (-0.013, -0.012, B - 0.0175), (-0.0105, 0.012, B - 0.012)), cyl("ssp", 0.0022, 0.0022, 0.027, 10, 'X', (0, 0.008, B - 0.016))], "sstop")
mrel = cyl("mrel", 0.0042, 0.0042, 0.004, 14, 'X', (-0.011, -0.030, B - 0.034))
bpy.ops.mesh.primitive_torus_add(major_radius=0.0045, minor_radius=0.0012, major_segments=12, minor_segments=6, location=(0, -0.086, B - 0.134), rotation=(0, math.pi / 2, 0))
lanyard = bpy.context.object; lanyard.name = "lanyard"
metal = join([frame, barrel, trig, tsafe, sstop, mrel, lanyard], "frame_j"); give(metal, M_STEEL)
# checkered walnut grip panels with plain screws
panel = profile_x("panel", [(-0.037, B - 0.046), (-0.051, B - 0.117), (-0.088, B - 0.117), (-0.077, B - 0.042), (-0.071, B - 0.034), (-0.045, B - 0.034)], 0.031)
bevel(panel, 0.003, 3, 30); apply_mods(panel); give(panel, M_WOOD)
screws = [cyl("scr", 0.0033, 0.0033, 0.0322, 12, 'X', (0, y, z)) for y, z in ((-0.057, B - 0.047), (-0.071, B - 0.106))]
for s_ in screws: give(s_, M_STEEL)
pistol = join([metal, panel] + screws, "pistol_j")
# hammer (cocked spur hammer), pivot behind the slide
HPIV = Vector((0, -0.083, B - 0.004))
hammer = profile_x("hammer", [(-0.080, B - 0.008), (-0.085, B + 0.004), (-0.096, B + 0.010), (-0.104, B + 0.012), (-0.103, B + 0.007), (-0.094, B + 0.002), (-0.088, B - 0.010)], 0.0065)
bevel(hammer, 0.001, 2); apply_mods(hammer); give(hammer, M_STEEL)
# magazine: body along the grip + base plate, a round showing at the top
mag = profile_x("mag", [(-0.074, B - 0.036), (-0.044, B - 0.036), (-0.056, B - 0.129), (-0.088, B - 0.129)], 0.018)
base_ = profile_x("magbase", [(-0.091, B - 0.129), (-0.054, B - 0.129), (-0.053, B - 0.134), (-0.092, B - 0.134)], 0.022)
round_ = cyl("round", 0.0058, 0.0058, 0.022, 14, 'Y', (0, -0.058, B - 0.031))
give(mag, M_STEEL); give(base_, M_STEEL); give(round_, M_BRASS)
magazine = join([mag, base_, round_], "magazine_m")
# spent casing (spawned by the game at 'eject')
casing = cyl("casing_m", 0.006, 0.006, 0.023, 14, 'X'); give(casing, M_BRASS)
for o in (pistol, slide, hammer, magazine, casing): smooth(o, 35)
MAG_ORIGIN = Vector((0, -0.072, B - 0.13))


# ================================================================ hands: real hand meshes (CharMorph MB-Lab male), posed
import sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import charhand as H
SKIN = H.base()['skin']
for nd in SKIN.node_tree.nodes:  # sample the body albedo through the original UVs (kept as 'skinUV' for the bake)
    if nd.type == 'TEX_IMAGE':
        uvn = SKIN.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'skinUV'; SKIN.node_tree.links.new(uvn.outputs['UV'], nd.inputs['Vector'])
M_SHIRT = mat("shirt", flat_noise_build((0.42, 0.40, 0.35, 1), (0.50, 0.48, 0.42, 1), 300, (0.6, 0.58, 0.52, 1)))

import os, json
THUMB_GUN = json.loads(os.environ.get("THUMB", "[[70, -35], [-100, 0], [-60, 0]]"))
POSES = {
    "gun": H.pose_dict(H.curl(*json.loads(os.environ.get("INDEX", "[-12, -70, -45]"))), H.curl(-82, -96, -48), H.curl(-86, -96, -48), H.curl(-90, -94, -45), THUMB_GUN),
    "cig": H.pose_dict(H.curl(-14, -16, -8, 7), H.curl(-12, -16, -8, -5), H.curl(-48, -62, -30), H.curl(-58, -66, -30), [(-6, -24), (-14, 0), (-12, 0)]),
    "cup": H.pose_dict(H.curl(-36, -42, -26), H.curl(-40, -44, -26), H.curl(-44, -46, -26), H.curl(-48, -46, -26), [(10, -10), (-12, 0), (-16, 0)]),
    "relax": H.pose_dict(H.curl(-14, -18, -10), H.curl(-17, -22, -12), H.curl(-22, -26, -14), H.curl(-27, -30, -15), [(-4, -18), (-8, 0), (-8, 0)]),
}


def cuffs(name, rf=1.0):
    """Shirt cuff + trench-coat sleeve in the hand frame (forearm runs -Y from the wrist at the origin)."""
    def tube(nm, y0, y1, r0, r1, seg=24, wob=0.0):
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=seg, radius1=r1, radius2=r0, depth=abs(y1 - y0))
        for v in bm.verts:
            a = math.atan2(v.co.y, v.co.x); k = 1 + wob * math.sin(a * 3 + v.co.z * 30) + wob * 0.6 * math.sin(a * 7 - v.co.z * 55)
            v.co.x *= k; v.co.y *= k
        bmesh.ops.transform(bm, matrix=Matrix.Translation((0, (y0 + y1) / 2, -0.004)) @ Matrix.Rotation(math.pi / 2, 4, 'X'), verts=bm.verts)
        o = mesh_obj(nm, bm); s = o.modifiers.new("s", 'SOLIDIFY'); s.thickness = 0.003; apply_mods(o); smooth(o, 60); return o
    shirt = tube(name + "_shirt", -0.022, -0.075, 0.037 * rf, 0.039 * rf, 24, 0.015); give(shirt, M_SHIRT)
    coat = tube(name + "_coat", -0.055, -0.40, 0.052 * rf, 0.066 * rf, 24, 0.05)
    fold = tube(name + "_fold", -0.052, -0.095, 0.056 * rf, 0.057 * rf, 24, 0.03)
    coat = join([coat, fold], name + "_coatj"); give(coat, M_COAT)
    return join([coat, shirt], name)


def fit(o_list, src_a, src_p, src_c, dst_a, dst_p, dst_c):
    """Rigid transform taking the frame (a, p) at c onto (a', p') at c'."""
    def basis(a, p):
        a = a.normalized(); p = (p - a * p.dot(a)).normalized(); return Matrix((a, p, a.cross(p))).transposed()
    Rm = basis(dst_a, dst_p) @ basis(src_a, src_p).transposed()
    M = Matrix.Translation(dst_c) @ Rm.to_4x4() @ Matrix.Translation(-src_c)
    for o in o_list: o.data.transform(M)
    return M


# ---- right hand on the grip
hand_r, P = H.make_hand('R', POSES["gun"], "hand_r"); H.decimate(hand_r, 2400)
sleeve_r = cuffs("sleeve_r")
def hole(f): return sum((P[f + k][i] for k, i in ((".01", 0), (".01", 1), (".02", 1), (".03", 1))), Vector()) / 4
C = (hole("f_middle") + hole("f_ring") + hole("f_pinky")) / 3
a_h = hole("f_middle") - hole("f_pinky")
palm_c = (P["palm.02"][0] + P["palm.02"][1] + P["palm.03"][0] + P["palm.03"][1]) / 4
p_h = palm_c - C
gtop = Vector((0, -0.057, BORE - 0.043)); gbot = Vector((0, -0.071, BORE - 0.124))
a_g = gtop - gbot; ax = a_g.normalized(); fw = Vector((0, ax.z, -ax.y)).normalized()
if fw.y < 0: fw = -fw
GRIP_T, PALM_BACK, PALM_RIGHT, SHIFT = float(os.environ.get("GRIP_T", "0.36")), 0.55, 0.85, 0.004
p_g = -fw * PALM_BACK + Vector((1, 0, 0)) * PALM_RIGHT
c_g = gtop + (gbot - gtop) * GRIP_T + p_g.normalized() * SHIFT
fit([hand_r, sleeve_r], a_h, p_h, C, a_g, p_g, c_g)

# ---- left hand variants (hand frame; placed by player.js): cigarette, cupped (lighting a match), relaxed
hand_l, PL = H.make_hand('L', POSES["cig"], "hand_l"); H.decimate(hand_l, 3000)
hand_l_cup, _ = H.make_hand('L', POSES["cup"], "hand_l_cup"); H.decimate(hand_l_cup, 3000)
hand_l_relax, _ = H.make_hand('L', POSES["relax"], "hand_l_relax"); H.decimate(hand_l_relax, 3000)
sleeve_l = cuffs("sleeve_l")
# cigarette through the gap between index and middle fingers at the proximal phalanx, standing out of the back of the hand
mi = (P_i := PL["f_index.01"])[0] * 0.45 + P_i[1] * 0.55; mm = PL["f_middle.01"][0] * 0.45 + PL["f_middle.01"][1] * 0.55
# cigarette: cork filter (lips end, ~25 %, slightly flattened) below the fingers on the palm side, white paper through the
# finger gap, grey ash and an orange ember at the far end out of the back of the hand. Held near the filter end.
cbase = (mi + mm) / 2 + Vector((0, 0, -0.034)); cdir = Vector((0.0, 0.45, 1.0)).normalized()
def cig_seg(nm, a, b, r0, r1, m, flat=1.0):
    o = cyl(nm, r0, r1, b - a, 12, 'Z'); o.data.transform(Matrix.Diagonal((flat, 1, 1, 1)))
    o.data.transform(Matrix.Translation(cbase + cdir * (a + b) / 2) @ Vector((0, 0, 1)).rotation_difference(cdir).to_matrix().to_4x4()); give(o, m); return o
def cork_build(nt, b_):
    L_ = nt.links; noi = n(nt, 'ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 900
    mx = n(nt, 'ShaderNodeMix', data_type='RGBA'); mx.inputs['A'].default_value = (0.42, 0.22, 0.08, 1); mx.inputs['B'].default_value = (0.60, 0.36, 0.14, 1)
    L_.new(noi.outputs['Fac'], mx.inputs['Factor']); L_.new(mx.outputs['Result'], b_.inputs['Base Color'])
M_CORK = mat("cork", cork_build)
M_ASH = mat("ash", flat_noise_build((0.18, 0.17, 0.16, 1), (0.32, 0.31, 0.29, 1), 500))
segs = [cig_seg("filter", 0.0, 0.020, 0.0044, 0.0044, M_CORK, 0.86), cig_seg("paper", 0.020, 0.074, 0.0045, 0.0045, M_PAPER),
        cig_seg("ashc", 0.074, 0.079, 0.0045, 0.0042, M_ASH), cig_seg("emb", 0.079, 0.081, 0.0042, 0.0034, M_EMBER)]
cig = join(segs, "cig"); smooth(cig, 50)
CIG_TIP = cbase + cdir * 0.083  # the lit end: smoke + ember glow attach here
def skin_build(nt, b):  # bare skin: warm base, mottling, pinker knuckles/tips (convex), darker creases (concave)
    L = nt.links
    noi = n(nt, 'ShaderNodeTexNoise'); noi.inputs['Scale'].default_value = 180; noi.inputs['Detail'].default_value = 6
    base = n(nt, 'ShaderNodeMix', data_type='RGBA'); base.inputs['A'].default_value = (0.34, 0.24, 0.19, 1); base.inputs['B'].default_value = (0.42, 0.30, 0.24, 1)
    L.new(noi.outputs['Fac'], base.inputs['Factor'])
    geo = n(nt, 'ShaderNodeNewGeometry')
    cv = ramp(nt, [(0.5, (0, 0, 0, 1)), (0.6, (1, 1, 1, 1))]); L.new(geo.outputs['Pointiness'], cv.inputs['Fac'])
    knu = n(nt, 'ShaderNodeMix', data_type='RGBA'); knu.inputs['B'].default_value = (0.52, 0.24, 0.17, 1)
    L.new(base.outputs['Result'], knu.inputs['A']); L.new(cv.outputs['Color'], knu.inputs['Factor'])
    cc = ramp(nt, [(0.42, (1, 1, 1, 1)), (0.5, (0, 0, 0, 1))]); L.new(geo.outputs['Pointiness'], cc.inputs['Fac'])
    cre = n(nt, 'ShaderNodeMix', data_type='RGBA'); cre.inputs['B'].default_value = (0.16, 0.08, 0.05, 1)
    L.new(knu.outputs['Result'], cre.inputs['A']); L.new(cc.outputs['Color'], cre.inputs['Factor'])
    L.new(cre.outputs['Result'], b.inputs['Base Color'])
M_SKINP = mat("skinp", skin_build)
for hnd in (hand_r, hand_l, hand_l_cup, hand_l_relax):  # bare hands: the real hand shape reads best as skin
    hnd.data.uv_layers[0].name = 'skinUV'; give(hnd, M_SKINP)

# ================================================================ UV atlas + bake (base colour x AO)
HANDS = [hand_r, hand_l, hand_l_cup, hand_l_relax]
bakeables = [pistol, slide, hammer, magazine, casing, hand_r, sleeve_r, hand_l, hand_l_cup, hand_l_relax, sleeve_l, cig]
for o in bakeables:
    for uv in list(o.data.uv_layers):
        if uv.name != 'skinUV': o.data.uv_layers.remove(uv)
    u = o.data.uv_layers.new(name="UVMap"); o.data.uv_layers.active = u
    if 'skinUV' in o.data.uv_layers: o.data.uv_layers['skinUV'].active_render = True
bpy.ops.object.select_all(action='DESELECT')
for o in bakeables: o.select_set(True)
bpy.context.view_layer.objects.active = pistol
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
WEIGHT = {pistol: 1.5, slide: 1.6, hammer: 1.2, magazine: 1.0, casing: 0.8, hand_r: 1.25, hand_l: 1.1, hand_l_cup: 0.8, hand_l_relax: 0.8, cig: 1.0, sleeve_r: 0.35, sleeve_l: 0.3}
for o, wgt in WEIGHT.items():
    uv = o.data.uv_layers['UVMap'].data
    for d in uv: d.uv = d.uv * wgt
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(margin=0.004, rotate=True, scale=True)
bpy.ops.object.mode_set(mode='OBJECT')
# give the gun more texels: scale the revolver/cylinder islands up before the final pack is not trivial; atlas is 1k for all.

img_c = bpy.data.images.new("vm_col", RES, RES, float_buffer=True); img_a = bpy.data.images.new("vm_ao", RES, RES, float_buffer=True)
def target(img):
    for m in (M_STEEL, M_WOOD, M_GLOVE, M_COAT, M_PAPER, M_EMBER, SKIN, M_SHIRT, M_SKINP, M_BRASS, M_CORK, M_ASH):
        nt = m.node_tree; t = nt.nodes.get("BAKE") or nt.nodes.new('ShaderNodeTexImage'); t.name = "BAKE"; t.image = img
        nt.nodes.active = t
bk = sc.render.bake; bk.margin = 6; bk.use_clear = True
target(img_c); bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
target(img_a); sc.cycles.samples = 96; sc.world = bpy.data.worlds.new("w"); bpy.ops.object.bake(type='AO')
import numpy as np
c = np.array(img_c.pixels[:]).reshape(-1, 4); a = np.array(img_a.pixels[:]).reshape(-1, 4)
ao = np.clip(a[:, :1] * 0.85 + 0.15, 0, 1)
lin = np.clip(c[:, :3] * ao, 0, 1)
srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
out = bpy.data.images.new("vm_atlas", RES, RES); out.colorspace_settings.name = 'sRGB'
px = np.concatenate([srgb, np.ones((srgb.shape[0], 1))], 1).astype(np.float32)
out.pixels.foreach_set(px.ravel()); TEXP.parent.mkdir(parents=True, exist_ok=True)
out.filepath_raw = str(TEXP); out.file_format = 'PNG'; out.save()

# ================================================================ export materials: one shared atlas, PBR factors per surface
def emat(name, metal, rough, emis=None):
    m = bpy.data.materials.new("vm_" + name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = out; nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Metallic'].default_value = metal; b.inputs['Roughness'].default_value = rough
    if emis:
        b.inputs['Emission Color'].default_value = emis; b.inputs['Emission Strength'].default_value = 3.0
    return m
EX = {M_STEEL: emat("steel", 0.4, 0.5), M_WOOD: emat("walnut", 0.0, 0.42), M_GLOVE: emat("glove", 0.0, 0.45), M_COAT: emat("coat", 0.0, 0.9),
      M_PAPER: emat("paper", 0.0, 0.8), SKIN: emat("skin", 0.0, 0.55), M_SKINP: emat("skin", 0.0, 0.5), M_BRASS: emat("brass", 0.85, 0.3), M_CORK: emat("cork", 0.0, 0.7), M_ASH: emat("ash", 0.0, 0.95), M_SHIRT: emat("shirt", 0.0, 0.85), M_EMBER: emat("ember", 0.0, 0.6, (1.0, 0.28, 0.04, 1))}
for o in bakeables:
    for i, s in enumerate(o.material_slots):
        if s.material in EX: o.material_slots[i].material = EX[s.material]

# ================================================================ hierarchy
def empty(name, loc, parent=None):
    e = link(bpy.data.objects.new(name, None)); e.location = loc; e.empty_display_size = 0.01
    if parent: e.parent = parent
    return e

rig_r = empty("rig_r", (0, 0, 0)); rig_l = empty("rig_l", (0, 0, 0))
pistol.name = "pistol"; pistol.parent = rig_r
slide.name = "slide"; slide.parent = pistol                     # moves along the bore (three +z = back)
empty("eject", (0.013, -0.004, B + 0.011), slide)              # ejection port, right side
hammer.name = "hammer_m"; hm = empty("hammer", HPIV, pistol); set_origin(hammer, HPIV); hammer.location = (0, 0, 0); hammer.parent = hm
mg = empty("magazine", MAG_ORIGIN, pistol); set_origin(magazine, MAG_ORIGIN); magazine.location = (0, 0, 0); magazine.parent = mg
empty("muzzle", (0, 0.118, B), pistol)
casing.name = "casing"; casing.parent = rig_r; casing.location = (0, 0, -1)
for o in (hand_r, sleeve_r): o.parent = rig_r
for o in (hand_l, hand_l_cup, hand_l_relax, sleeve_l, cig): o.parent = rig_l
for o in HANDS:
    if 'skinUV' in o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers['skinUV'])
empty("cig_tip", CIG_TIP, cig)

tot = {}
for o in bakeables:
    o.data.calc_loop_triangles(); tot[o.name] = len(o.data.loop_triangles)
print("VMTRIS", tot, "right", sum(v for k, v in tot.items() if k in ("pistol", "slide", "hammer_m", "magazine_m", "casing", "hand_r", "sleeve_r")), "left", sum(v for k, v in tot.items() if k in ("hand_l", "sleeve_l", "cig", "hand_l_cup", "hand_l_relax")))
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', export_yup=True, export_apply=True, export_materials='EXPORT',
                          export_image_format='JPEG', export_jpeg_quality=90, export_extras=False, export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art" / "vm_1911.blend"))
print("VMOK", OUT, OUT.stat().st_size)
