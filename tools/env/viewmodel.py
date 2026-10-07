"""NEON RAIN first-person viewmodel: a 1940s 4-inch .38 swing-out revolver held in a gloved right hand (trench-coat
sleeve), and a gloved left hand holding a cigarette. Procedural materials (blued steel with edge wear, walnut grip,
dark leather glove, wool coat, paper) baked with AO into one 1k base-colour atlas. Exports assets/models/vm_revolver.glb.

Blender axes: x right, y forward (muzzle), z up. glTF export (+Y up) maps this to three: x right, -z forward, y up.
Nodes: rig_r > revolver > crane > cylinder, revolver > muzzle; rig_r > hand_r, sleeve_r; rig_l > hand_l, sleeve_l, cig > cig_tip.
Usage: blender -b --python tools/env/viewmodel.py"""
import bpy, bmesh, math, pathlib
from mathutils import Vector, Matrix

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "models" / "vm_revolver.glb"
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
    blued = n(nt, 'ShaderNodeMix', data_type='RGBA'); blued.inputs['A'].default_value = (0.06, 0.066, 0.08, 1); blued.inputs['B'].default_value = (0.11, 0.115, 0.13, 1)
    L.new(noi.outputs['Fac'], blued.inputs['Factor'])
    mix = n(nt, 'ShaderNodeMix', data_type='RGBA'); mix.inputs['B'].default_value = (0.17, 0.165, 0.155, 1)
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


# ================================================================ revolver
# cylinder: 6 chambers, 6 flutes; axis along y at (0, ?, BORE)
CYL_R, CYL_L, CYL_Y = 0.0185, 0.040, -0.0005
cylo = cyl("cylinder", CYL_R, CYL_R, CYL_L, 24, 'Y', (0, CYL_Y, BORE))
for k in range(6):
    a = math.radians(30 + 60 * k)
    fl = cyl("flute", 0.0042, 0.0042, CYL_L * 0.62, 8, 'Y', (math.cos(a) * 0.0205, CYL_Y + 0.004, BORE + math.sin(a) * 0.0205))
    boolean(cylo, fl)
for k in range(6):
    a = math.radians(60 * k)
    ch = cyl("chamber", 0.0047, 0.0047, 0.016, 8, 'Y', (math.cos(a) * 0.0118, CYL_Y + CYL_L / 2, BORE + math.sin(a) * 0.0118))
    boolean(cylo, ch)
bevel(cylo, 0.0012, 2, 30); apply_mods(cylo); give(cylo, M_STEEL)
# crane arm + ejector rod (swing out with the cylinder)
rod = cyl("rod", 0.0024, 0.0024, 0.058, 10, 'Y', (0, CYL_Y + CYL_L / 2 + 0.029, BORE - 0.0135))
rodtip = cyl("rodtip", 0.0034, 0.0034, 0.006, 12, 'Y', (0, CYL_Y + CYL_L / 2 + 0.057, BORE - 0.0135))
arm = box("arm", (-0.004, CYL_Y + CYL_L / 2 - 0.002, BORE - 0.024), (0.004, CYL_Y + CYL_L / 2 + 0.004, BORE - 0.006))
crane = join([rod, rodtip, arm], "crane_mesh"); give(crane, M_STEEL)

# barrel with top rib, front sight, ejector-rod lug, bore
BAR_Y0, BAR_L = 0.022, 0.102
bar = cyl("barrel", 0.0088, 0.0082, BAR_L, 24, 'Y', (0, BAR_Y0 + BAR_L / 2, BORE))
rib = box("rib", (-0.0032, BAR_Y0, BORE + 0.005), (0.0032, BAR_Y0 + BAR_L, BORE + 0.0108))
sight = profile_x("sight", [(BAR_Y0 + BAR_L - 0.014, BORE + 0.0105), (BAR_Y0 + BAR_L - 0.002, BORE + 0.0105), (BAR_Y0 + BAR_L - 0.002, BORE + 0.0175), (BAR_Y0 + BAR_L - 0.007, BORE + 0.0172)], 0.0028)
lug = box("lug", (-0.0035, BAR_Y0 + BAR_L - 0.016, BORE - 0.017), (0.0035, BAR_Y0 + BAR_L - 0.004, BORE - 0.004))
barrel = join([bar, rib, sight, lug], "barrel_j")
boolean(barrel, cyl("bore", 0.0046, 0.0046, 0.03, 16, 'Y', (0, BAR_Y0 + BAR_L, BORE)))

# frame: cylinder window with top strap, recoil shield, hammer hump, grip frame
fr_pts = [(-0.050, BORE + 0.012), (-0.040, BORE + 0.024), (-0.026, BORE + 0.026), (0.024, BORE + 0.0255), (0.028, BORE + 0.018),
          (0.028, BORE - 0.030), (-0.004, BORE - 0.031), (-0.030, BORE - 0.030), (-0.044, BORE - 0.036), (-0.056, BORE - 0.030), (-0.058, BORE - 0.010)]
frame = profile_x("frame", fr_pts, 0.029)
win = box("win", (-0.06, CYL_Y - CYL_L / 2 - 0.0008, BORE - 0.0205), (0.06, CYL_Y + CYL_L / 2 + 0.0008, BORE + 0.0205))
boolean(frame, win)
# sideplate line and thumb latch on the left
latch = box("latch", (-0.0175, -0.040, BORE - 0.002), (-0.0135, -0.026, BORE + 0.006))
pins = [cyl("pin", 0.0016, 0.0016, 0.031, 8, 'X', (0, y, z)) for y, z in ((-0.012, BORE - 0.026), (-0.040, BORE - 0.020), (-0.050, BORE + 0.004))]
frame = join([frame] + pins + [latch], "frame_j")
bevel(frame, 0.0014, 2, 35); apply_mods(frame)

# hammer with checkered spur
ham = profile_x("hammer", [(-0.046, BORE + 0.008), (-0.036, BORE + 0.018), (-0.040, BORE + 0.030), (-0.050, BORE + 0.037), (-0.060, BORE + 0.036),
                           (-0.059, BORE + 0.031), (-0.050, BORE + 0.028), (-0.052, BORE + 0.010)], 0.0072)
bevel(ham, 0.0012, 2); apply_mods(ham)

# trigger guard + trigger
guard = tube_curve("guard", [(0, 0.004, BORE - 0.030), (0, -0.002, BORE - 0.050), (0, -0.024, BORE - 0.060), (0, -0.040, BORE - 0.050), (0, -0.044, BORE - 0.034)], 0.0024, 1.3)
trig = tube_curve("trigger", [(0, -0.016, BORE - 0.028), (0, -0.017, BORE - 0.040), (0, -0.022, BORE - 0.050), (0, -0.026, BORE - 0.053)], 0.0026, 1.6)
metal = join([frame, barrel, ham, guard, trig], "revolver_mesh"); give(metal, M_STEEL)

# walnut grip (two panels shape as one stock) with plain steel screw
grip_pts = [(-0.044, BORE - 0.030), (-0.040, BORE - 0.060), (-0.047, BORE - 0.092), (-0.054, BORE - 0.118), (-0.066, BORE - 0.124), (-0.080, BORE - 0.118),
            (-0.083, BORE - 0.104), (-0.076, BORE - 0.072), (-0.066, BORE - 0.040), (-0.058, BORE - 0.026)]
grip = profile_x("grip", grip_pts, 0.033)
bevel(grip, 0.006, 4, 30); apply_mods(grip)
butt = profile_x("butt", [(-0.054, BORE - 0.116), (-0.066, BORE - 0.122), (-0.080, BORE - 0.116), (-0.081, BORE - 0.121), (-0.066, BORE - 0.127), (-0.053, BORE - 0.121)], 0.025)
give(grip, M_WOOD)
screw = cyl("screw", 0.0028, 0.0028, 0.036, 12, 'X', (0, -0.063, BORE - 0.075))
give(butt, M_STEEL); give(screw, M_STEEL)
revolver = join([metal, butt, screw, grip], "revolver_j")
smooth(revolver, 35); smooth(cylo, 35); smooth(crane, 35)


# ================================================================ hands: real hand meshes (CharMorph MB-Lab male), posed
import sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import charhand as H
SKIN = H.base()['skin']
for nd in SKIN.node_tree.nodes:  # sample the body albedo through the original UVs (kept as 'skinUV' for the bake)
    if nd.type == 'TEX_IMAGE':
        uvn = SKIN.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'skinUV'; SKIN.node_tree.links.new(uvn.outputs['UV'], nd.inputs['Vector'])
M_SHIRT = mat("shirt", flat_noise_build((0.42, 0.40, 0.35, 1), (0.50, 0.48, 0.42, 1), 300, (0.6, 0.58, 0.52, 1)))

import os, json
THUMB_GUN = json.loads(os.environ.get("THUMB", "[[-40, -40], [-30, 0], [-20, 0]]"))
POSES = {
    "gun": H.pose_dict(H.curl(-28, -62, -32), H.curl(-82, -96, -48), H.curl(-86, -96, -48), H.curl(-90, -94, -45), THUMB_GUN),
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
gtop = Vector((0, -0.050, BORE - 0.036)); gbot = Vector((0, -0.068, BORE - 0.112))
a_g = gtop - gbot; ax = a_g.normalized(); fw = Vector((0, ax.z, -ax.y)).normalized()
if fw.y < 0: fw = -fw
GRIP_T, PALM_BACK, PALM_RIGHT, SHIFT = 0.52, 0.55, 0.85, 0.004
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
cbase = (mi + mm) / 2 + Vector((0, 0, -0.022)); cdir = Vector((0.0, 0.45, 1.0)).normalized()
cig = cyl("cig", 0.0045, 0.0045, 0.080, 12, 'Z')
cig.data.transform(Matrix.Translation(cbase + cdir * 0.040) @ Vector((0, 0, 1)).rotation_difference(cdir).to_matrix().to_4x4())
ash = cyl("ash", 0.0046, 0.0044, 0.006, 12, 'Z')
ash.data.transform(Matrix.Translation(cbase + cdir * 0.083) @ Vector((0, 0, 1)).rotation_difference(cdir).to_matrix().to_4x4())
give(cig, M_PAPER); give(ash, M_EMBER)
cig = join([cig, ash], "cig"); smooth(cig, 50)
CIG_TIP = cbase + cdir * 0.088
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
bakeables = [revolver, cylo, crane, hand_r, sleeve_r, hand_l, hand_l_cup, hand_l_relax, sleeve_l, cig]
for o in bakeables:
    for uv in list(o.data.uv_layers):
        if uv.name != 'skinUV': o.data.uv_layers.remove(uv)
    u = o.data.uv_layers.new(name="UVMap"); o.data.uv_layers.active = u
    if 'skinUV' in o.data.uv_layers: o.data.uv_layers['skinUV'].active_render = True
bpy.ops.object.select_all(action='DESELECT')
for o in bakeables: o.select_set(True)
bpy.context.view_layer.objects.active = revolver
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
WEIGHT = {revolver: 1.5, cylo: 1.5, crane: 1.3, hand_r: 1.25, hand_l: 1.1, hand_l_cup: 0.8, hand_l_relax: 0.8, cig: 1.0, sleeve_r: 0.35, sleeve_l: 0.3}
for o, wgt in WEIGHT.items():
    uv = o.data.uv_layers['UVMap'].data
    for d in uv: d.uv = d.uv * wgt
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.pack_islands(margin=0.004, rotate=True, scale=True)
bpy.ops.object.mode_set(mode='OBJECT')
# give the gun more texels: scale the revolver/cylinder islands up before the final pack is not trivial; atlas is 1k for all.

img_c = bpy.data.images.new("vm_col", RES, RES, float_buffer=True); img_a = bpy.data.images.new("vm_ao", RES, RES, float_buffer=True)
def target(img):
    for m in (M_STEEL, M_WOOD, M_GLOVE, M_COAT, M_PAPER, M_EMBER, SKIN, M_SHIRT, M_SKINP):
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
EX = {M_STEEL: emat("steel", 0.55, 0.34), M_WOOD: emat("walnut", 0.0, 0.42), M_GLOVE: emat("glove", 0.0, 0.45), M_COAT: emat("coat", 0.0, 0.9),
      M_PAPER: emat("paper", 0.0, 0.8), SKIN: emat("skin", 0.0, 0.55), M_SKINP: emat("skin", 0.0, 0.5), M_SHIRT: emat("shirt", 0.0, 0.85), M_EMBER: emat("ember", 0.0, 0.6, (1.0, 0.28, 0.04, 1))}
for o in bakeables:
    for i, s in enumerate(o.material_slots):
        if s.material in EX: o.material_slots[i].material = EX[s.material]

# ================================================================ hierarchy
def empty(name, loc, parent=None):
    e = link(bpy.data.objects.new(name, None)); e.location = loc; e.empty_display_size = 0.01
    if parent: e.parent = parent
    return e

rig_r = empty("rig_r", (0, 0, 0)); rig_l = empty("rig_l", (0, 0, 0))
revolver.name = "revolver"; revolver.parent = rig_r
PIV = Vector((0, 0, BORE - 0.022))  # crane hinge axis (parallel to the bore, below the cylinder)
cr = empty("crane", PIV, revolver)
set_origin(crane, PIV); crane.location = (0, 0, 0); crane.name = "crane_m"; crane.parent = cr
set_origin(cylo, (0, CYL_Y, BORE)); cylo.location = Vector((0, CYL_Y, BORE)) - PIV; cylo.parent = cr
# the cylinder node as an empty, so `cylinder` spins about its axis
cylo.name = "cylinder_m"; cy = empty("cylinder", Vector((0, CYL_Y, BORE)) - PIV, cr); cylo.parent = cy; cylo.location = (0, 0, 0)
empty("muzzle", (0, BAR_Y0 + BAR_L + 0.004, BORE), revolver)
for o in (hand_r, sleeve_r): o.parent = rig_r
for o in (hand_l, hand_l_cup, hand_l_relax, sleeve_l, cig): o.parent = rig_l
for o in HANDS:
    if 'skinUV' in o.data.uv_layers: o.data.uv_layers.remove(o.data.uv_layers['skinUV'])
empty("cig_tip", CIG_TIP, cig)

tot = {}
for o in bakeables:
    o.data.calc_loop_triangles(); tot[o.name] = len(o.data.loop_triangles)
print("VMTRIS", tot, "right", sum(v for k, v in tot.items() if k in ("revolver", "cylinder_m", "crane_m", "hand_r", "sleeve_r")), "left", sum(v for k, v in tot.items() if k in ("hand_l", "sleeve_l", "cig", "hand_l_cup", "hand_l_relax")))
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', export_yup=True, export_apply=True, export_materials='EXPORT',
                          export_image_format='JPEG', export_jpeg_quality=90, export_extras=False, export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "art" / "vm_revolver.blend"))
print("VMOK", OUT, OUT.stat().st_size)
