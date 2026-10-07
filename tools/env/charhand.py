"""Real human hands for the NEON RAIN viewmodel, cut from the CharMorph MB-Lab male base mesh (AGPL3 data, local copy at
E:/claude/Tools/charmorph/CharMorph/data/characters/mb_male): joints + skin weights rebuild a hand armature, the fingers
are posed per variant, the posed hand + 15 cm of forearm is cut out and moved into a hand frame:
origin at the wrist, +Y toward the middle knuckle, +Z out of the back of the hand. Used by tools/env/viewmodel.py."""
import bpy, bmesh, math
import numpy as np
from mathutils import Vector, Matrix

CM = "E:/claude/Tools/charmorph/CharMorph/data/characters/mb_male/"
FINGERS = ("f_index", "f_middle", "f_ring", "f_pinky")
PALM = {"f_index": "palm.01", "f_middle": "palm.02", "f_ring": "palm.03", "f_pinky": "palm.04"}

_base = {}


def _npz_groups(path):
    z = np.load(path); names = bytes(z['names']).decode().split('\0')
    off = np.concatenate([[0], np.cumsum(z['cnt'].astype(np.int64))]).astype(np.int64)
    return {n: (z['idx'][off[i]:off[i + 1]].astype(np.int64), z['weights'][off[i]:off[i + 1]]) for i, n in enumerate(names) if n}


def base():
    if not _base:
        with bpy.data.libraries.load(CM + "char.blend") as (src, dst):
            dst.objects = ["mb_male"]
        o = dst.objects[0]
        _base['obj'] = o
        _base['co'] = np.array([v.co[:] for v in o.data.vertices])
        _base['joints'] = _npz_groups(CM + "joints/regular.npz")
        _base['weights'] = _npz_groups(CM + "weights/gaming.npz")
        img = bpy.data.images.load(CM + "textures/albedo.png", check_existing=True)
        m = bpy.data.materials.new("skin"); m.use_nodes = True; nt = m.node_tree
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
        hsv = nt.nodes.new('ShaderNodeHueSaturation'); hsv.inputs['Saturation'].default_value = 0.85; hsv.inputs['Value'].default_value = 0.8
        nt.links.new(t.outputs['Color'], hsv.inputs['Color']); nt.links.new(hsv.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
        _base['skin'] = m
    return _base


def J(name):
    b = base(); idx, w = b['joints']['joint_' + name]
    return Vector((b['co'][idx] * w[:, None]).sum(0) / w.sum())


def make_hand(side, pose, name):
    """side 'R' or 'L'; pose: {bone: (curl_deg, spread_deg)}; returns (mesh object in hand frame, dict of joint points in hand frame)."""
    b = base(); s = "." + side
    src = b['obj']; me = src.data.copy(); o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.data.materials.clear(); o.data.materials.append(b['skin'])
    wrist = J("forearm" + s + "_tail"); htail = J("hand" + s + "_tail")
    mk = J("f_middle.01" + s + "_head"); ik = J("f_index.01" + s + "_head"); pk = J("f_pinky.01" + s + "_head")
    Y = (mk - wrist).normalized()
    X = (pk - ik) if side == 'R' else (ik - pk); X = (X - Y * X.dot(Y)).normalized()
    Z = X.cross(Y).normalized()
    # armature
    arm = bpy.data.armatures.new(name + "_arm"); ao = bpy.data.objects.new(name + "_rig", arm); bpy.context.scene.collection.objects.link(ao)
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ao; ao.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); eb = arm.edit_bones
    def bone(bn, h, t, parent=None):
        e = eb.new(bn + s); e.head = h; e.tail = t; e.align_roll(Z)
        if parent: e.parent = eb[parent + s]
        return e
    bone("forearm", wrist - Y * 0.25, wrist); bone("hand", wrist, htail, "forearm")
    for f in FINGERS:
        p = PALM[f]; bone(p, J(p + s + "_head"), J(p + s + "_tail"), "hand")
        h0 = J(f + ".01" + s + "_head"); t1 = J(f + ".01" + s + "_tail"); t2 = J(f + ".02" + s + "_tail"); t3 = J(f + ".03" + s + "_tail")
        bone(f + ".01", h0, t1, p); bone(f + ".02", t1, t2, f + ".01"); bone(f + ".03", t2, t3, f + ".02")
    th0 = J("thumb.01" + s + "_head"); th1 = J("thumb.01" + s + "_tail"); th2 = J("thumb.02" + s + "_tail"); th3 = J("thumb.03" + s + "_tail")
    bone("thumb.01", th0, th1, "palm.01"); bone("thumb.02", th1, th2, "thumb.01"); bone("thumb.03", th2, th3, "thumb.02")
    bpy.ops.object.mode_set(mode='OBJECT')
    # skin weights
    names = [bb.name for bb in arm.bones]
    for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
    for bn in names:
        if bn not in b['weights']: continue
        idx, w = b['weights'][bn]; vg = o.vertex_groups.new(name=bn)
        for i, ww in zip(idx.tolist(), w.tolist()): vg.add([i], ww, 'REPLACE')
    md = o.modifiers.new("arm", 'ARMATURE'); md.object = ao
    # pose: curl about the bone X axis (negative = flex toward the palm), spread about Z
    for bn, (curl, spread) in pose.items():
        pb = ao.pose.bones[bn + s]; pb.rotation_mode = 'XYZ'
        sg = 1 if side == 'R' else -1
        pb.rotation_euler = (math.radians(curl), 0, math.radians(spread) * sg)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier="arm")
    # posed joint points (for gun / cigarette placement)
    pts = {}
    for bn in names:
        mw = ao.matrix_world @ ao.pose.bones[bn].matrix
        pts[bn[:-2]] = (Vector(ao.pose.bones[bn].head), Vector(ao.pose.bones[bn].tail))
    # keep the hand + the forearm within 15 cm of the wrist
    keep_groups = {o.vertex_groups[n].index for n in names if n in o.vertex_groups and not n.startswith("forearm")}
    fa = o.vertex_groups.get("forearm" + s)
    bm = bmesh.new(); bm.from_mesh(o.data); dl = bm.verts.layers.deform.active
    kill = []
    for v in bm.verts:
        d = v[dl] if dl else {}
        hw = sum(w for g, w in d.items() if g in keep_groups); fw = d.get(fa.index, 0) if fa else 0
        along = (v.co - wrist).dot(Y)
        if hw > 0.02: continue
        if fw > 0.02 and along > -0.15 and (v.co - wrist).length < 0.2: continue
        kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    # hand frame: wrist origin, X/Y/Z as above
    R = Matrix((X, Y, Z)).to_4x4()  # rows = new axes -> world to local rotation
    T = R @ Matrix.Translation(-wrist)
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    bm.to_mesh(o.data); bm.free()
    for vg in list(o.vertex_groups): o.vertex_groups.remove(vg)
    for uv in [u for u in o.data.uv_layers if u.name != 'UVMap']: o.data.uv_layers.remove(uv)
    bpy.data.objects.remove(ao)
    pts = {k: (T @ h, T @ t) for k, (h, t) in pts.items()}
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    return o, pts


def decimate(o, target):
    o.data.calc_loop_triangles(); n = len(o.data.loop_triangles)
    if n > target:
        d = o.modifiers.new("dec", 'DECIMATE'); d.ratio = target / n
        bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.modifier_apply(modifier="dec")
    return o


def curl(c1, c2, c3, spread=0.0):
    return [(c1, spread), (c2, 0), (c3, 0)]


def pose_dict(index, middle, ring, pinky, thumb):
    d = {}
    for f, v in (("f_index", index), ("f_middle", middle), ("f_ring", ring), ("f_pinky", pinky), ("thumb", thumb)):
        for k, (c, sp) in enumerate(v):
            d[f"{f}.0{k + 1}"] = (c, sp)
    return d
