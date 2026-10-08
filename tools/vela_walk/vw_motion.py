"""Vela walk motion: retarget a Bandai Namco feminine walk onto the MPFB Vela rig, then build
  vw_walk  16-frame seamless in-place loop (shorter pencil-skirt steps, feet toward the midline, hip sway,
           right hand up with the cigarette holder, left arm swing)
  vw_stop  24-frame decelerate + turn-to-her-left + settle into the idle pose (root motion exported)
  vw_idle  32-frame idle loop (sampled from the rig's 4 s idle)
Usage: blender -b vela_anim.blend -P vw_motion.py -- BVH OUT.blend OUT.json [key=value ...]"""
import bpy, sys, math, json
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
BVH, OUT, OUTJ = argv[0], argv[1], argv[2]
PR = dict(stride=0.78, cross=0.55, sway=1.5, lat=1.3, larm=0.85, abd=6.0, nf=16, turn=42.0, idle_n=32, s0=0.4,
          clip_fps=16.0, decel=0.45, bob=2.5, ib_shift=0.035, ib_drop=0.012, ib_roll=3.5, ib_fx=0.055, ib_fy=0.08, ib_straight=0.985)
for a in argv[3:]:
    k, v = a.split('='); PR[k] = float(v)
NF16 = int(PR['nf'])
sc = bpy.context.scene; ctx = bpy.context
tgt = bpy.data.objects['Vela']
bones = tgt.data.bones
order = []
def _walk(b):
    order.append(b.name); [_walk(c) for c in b.children]
_walk(bones['Root'])
RH = {b.name: b.head_local.copy() for b in bones}
RT = {b.name: b.tail_local.copy() for b in bones}
RR = {b.name: b.matrix_local.to_3x3().normalized() for b in bones}
REL = {b.name: b.parent.matrix_local.inverted() @ b.matrix_local for b in bones if b.parent}
for pb in tgt.pose.bones: pb.rotation_mode = 'QUATERNION'

# ------------------------------------------------------------------ pose representations
def M_to_B(M):
    B = {}
    for n in order:
        b = bones[n]
        bm = (b.matrix_local.inverted() @ M[n]) if b.parent is None else (REL[n].inverted() @ M[b.parent.name].inverted() @ M[n])
        l, q, _ = bm.decompose(); B[n] = (l, q.normalized())
    return B
def B_to_M(B):
    M = {}
    for n in order:
        b = bones[n]; l, q = B[n]
        bm = Matrix.Translation(l) @ q.to_matrix().to_4x4()
        M[n] = (b.matrix_local @ bm) if b.parent is None else (M[b.parent.name] @ REL[n] @ bm)
    return M
def qs(a, b, w):
    if a.dot(b) < 0: b = -b
    return a.slerp(b, w)
def blend_B(A, Bb, w, names=None):
    return {n: ((A[n][0].lerp(Bb[n][0], w), qs(A[n][1], Bb[n][1], w)) if (names is None or n in names) else A[n]) for n in A}
def use_action(act):
    tgt.animation_data.action = act
    if tgt.animation_data.action_slot is None and len(act.slots): tgt.animation_data.action_slot = act.slots[0]
def read_B(frame):
    sc.frame_set(frame)
    return {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy().normalized()) for pb in tgt.pose.bones}
def key_B(B, frame):
    for pb in tgt.pose.bones:
        l, q = B[pb.name]; pb.location = l; pb.rotation_quaternion = q
        pb.keyframe_insert('location', frame=frame); pb.keyframe_insert('rotation_quaternion', frame=frame)
def new_action(name):
    if name in bpy.data.actions: bpy.data.actions.remove(bpy.data.actions[name])
    a = bpy.data.actions.new(name); a.use_fake_user = True; use_action(a); return a

shoes = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith(('Vela.shoe', 'Vela.heel'))]
def lowest():
    dg = ctx.evaluated_depsgraph_get(); mz = 9
    for o in shoes:
        ev = o.evaluated_get(dg); m = ev.to_mesh(); mw = o.matrix_world
        mz = min(mz, min((mw @ v.co).z for v in m.vertices)); ev.to_mesh_clear()
    return mz
pel_rest_inv = bones['pelvis'].matrix_local.to_3x3().inverted()
def plant_Bs(Bs):
    """drop or lift the pelvis so the lowest shoe point touches z=0, per pose"""
    act = new_action('_tmp'); out = []
    for i, B in enumerate(Bs): key_B(B, i + 1)
    for i, B in enumerate(Bs):
        sc.frame_set(i + 1); dz = -lowest()
        B2 = dict(B); l, q = B['pelvis']; B2['pelvis'] = (l + pel_rest_inv @ Vector((0, 0, dz)), q); out.append(B2)
    bpy.data.actions.remove(act); return out

# ------------------------------------------------------------------ idle reference (rig's own idle, already planted)
tgt.animation_data_create()
use_action(bpy.data.actions['idle'])
IDLE_B = [read_B(f) for f in range(1, 98)]
IDLE_M0 = B_to_M(IDLE_B[0])

# ------------------------------------------------------------------ BVH retarget (after Frazetta retarget.py)
sc.render.fps = 30
bpy.ops.import_anim.bvh(filepath=BVH, global_scale=0.01, use_fps_scale=False, update_scene_fps=False,
                        update_scene_duration=False, rotate_mode='NATIVE')
src = ctx.object
sfr = [int(x) for x in src.animation_data.action.frame_range]
print('VW src range', sfr, flush=True)
S_MAP = {"pelvis": "Hips", "spine_01": "Spine", "spine_02": "Spine", "spine_03": "Chest", "neck_01": "Neck", "head": "Head",
         "clavicle_l": "Shoulder_L", "upperarm_l": "UpperArm_L", "lowerarm_l": "LowerArm_L",
         "clavicle_r": "Shoulder_R", "upperarm_r": "UpperArm_R", "lowerarm_r": "LowerArm_R",
         "thigh_l": "UpperLeg_L", "calf_l": "LowerLeg_L", "foot_l": "Foot_L",
         "thigh_r": "UpperLeg_R", "calf_r": "LowerLeg_R", "foot_r": "Foot_R"}
def basis(primary, secondary):
    y = primary.normalized(); x = (secondary - y * secondary.dot(y)).normalized(); z = x.cross(y)
    return Matrix((x, y, z)).transposed()
SRC = {}
def src_state(f):
    if f not in SRC:
        sc.frame_set(f); mw = src.matrix_world; P, R, T = {}, {}, {}
        for pb in src.pose.bones:
            m = mw @ pb.matrix; P[pb.name] = m.to_translation(); R[pb.name] = m.to_3x3().normalized(); T[pb.name] = mw @ pb.tail
        SRC[f] = (P, R, T)
    return SRC[f]
def src_anat(P, R, T):
    lp = P["UpperLeg_L"] - P["UpperLeg_R"]; lc = P["UpperArm_L"] - P["UpperArm_R"]
    mh = (P["UpperLeg_L"] + P["UpperLeg_R"]) * 0.5; uc = P["Neck"] - P["Chest"]
    A = {"Hips": basis(P["Spine"] - mh, lp), "Spine": basis(P["Chest"] - P["Spine"], lp), "Chest": basis(P["Neck"] - P["Chest"], lc),
         "Neck": basis(P["Head"] - P["Neck"], lc), "Head": basis(T["Head"] - P["Head"], lc)}
    for s in "LR":
        A["Shoulder_" + s] = basis(P["UpperArm_" + s] - P["Shoulder_" + s], uc)
        A["UpperArm_" + s] = basis(P["LowerArm_" + s] - P["UpperArm_" + s], lc)
        A["LowerArm_" + s] = basis(P["Hand_" + s] - P["LowerArm_" + s], lc)
        A["UpperLeg_" + s] = basis(P["LowerLeg_" + s] - P["UpperLeg_" + s], lp)
        A["LowerLeg_" + s] = basis(P["Foot_" + s] - P["LowerLeg_" + s], lp)
        A["Foot_" + s] = basis(P["Toes_" + s] - P["Foot_" + s], lp)
    return A
def tgt_anat():
    lp = RH["thigh_l"] - RH["thigh_r"]; lc = RH["upperarm_l"] - RH["upperarm_r"]
    mh = (RH["thigh_l"] + RH["thigh_r"]) * 0.5; uc = RH["neck_01"] - RH["spine_03"]
    A = {"pelvis": basis(RH["spine_01"] - mh, lp), "spine_01": basis(RH["spine_03"] - RH["spine_01"], lp)}
    A["spine_02"] = A["spine_01"]
    A["spine_03"] = basis(RH["neck_01"] - RH["spine_03"], lc); A["neck_01"] = basis(RH["head"] - RH["neck_01"], lc)
    A["head"] = basis(RT["head"] - RH["head"], lc)
    for s in "lr":
        A["clavicle_" + s] = basis(RH["upperarm_" + s] - RH["clavicle_" + s], uc)
        A["upperarm_" + s] = basis(RH["lowerarm_" + s] - RH["upperarm_" + s], lc)
        A["lowerarm_" + s] = basis(RH["hand_" + s] - RH["lowerarm_" + s], lc)
        A["thigh_" + s] = basis(RH["calf_" + s] - RH["thigh_" + s], lp)
        A["calf_" + s] = basis(RH["foot_" + s] - RH["calf_" + s], lp)
        A["foot_" + s] = basis(RH["ball_" + s] - RH["foot_" + s], lp)
    return A
AT = tgt_anat()
P0, R0, T0 = src_state(sfr[0] + 2); A0 = src_anat(P0, R0, T0)
K = {sb: R0[sb].inverted() @ A0[sb] for sb in A0}
src_leg = (P0["LowerLeg_L"] - P0["UpperLeg_L"]).length + (P0["Foot_L"] - P0["LowerLeg_L"]).length
tgt_leg = (RH["calf_l"] - RH["thigh_l"]).length + (RH["foot_l"] - RH["calf_l"]).length
SCALE = tgt_leg / src_leg
LEGA = {s: (RH["calf_" + s] - RH["thigh_" + s]).length for s in "lr"}
LEGB = {s: (RH["foot_" + s] - RH["calf_" + s]).length for s in "lr"}
print('VW scale', round(SCALE, 3), flush=True)

def rot_between(a, b): return a.normalized().rotation_difference(b.normalized()).to_matrix()
def two_bone(H, A, a, b, Kfk):
    d = (A - H).length; d = min(d, (a + b) * 0.9995); d = max(d, abs(a - b) * 1.001)
    u = (A - H).normalized(); A2 = H + u * d
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(a * a - x * x, 0.0))
    pole = Kfk - H; pole = pole - u * pole.dot(u)
    if pole.length < 1e-6: pole = Vector((0, -1, 0))
    return H + u * x + pole.normalized() * h, A2

def ss(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def herm(p0, v0, p1, u):
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2
    return p0 * h00 + v0 * h10 + p1 * h01
def leg_ik(M, s, ankle, frot):
    th, ca, fo, ba = "thigh_" + s, "calf_" + s, "foot_" + s, "ball_" + s
    H = M[th].translation.copy()
    fwd = frot @ (REL[ba].translation); fwd.z = 0; fwd = fwd.normalized() if fwd.length > 1e-6 else Vector((0, -1, 0))
    pole = (H + ankle) * 0.5 + fwd * 0.4; Kfk = M[ca].translation.copy()
    Kn, A2 = two_bone(H, ankle, LEGA[s], LEGB[s], pole)
    R1 = rot_between(Kfk - H, Kn - H) @ M[th].to_3x3(); m = R1.to_4x4(); m.translation = H; M[th] = m
    cdir = R1 @ (M[th].to_3x3().inverted() @ M[th].to_3x3()) @ Vector((0, 1, 0))
    Rc = M[ca].to_3x3(); R2 = rot_between(Rc @ Vector((0, 1, 0)), A2 - Kn) @ Rc; m = R2.to_4x4(); m.translation = Kn; M[ca] = m
    m = frot.to_4x4(); m.translation = A2; M[fo] = m
    M[ba] = M[fo] @ REL[ba]

# pre-pass: travel line, hip roll, arm means
frames = list(range(sfr[0] + 1, sfr[1] + 1))
mids = [((src_state(f)[0]["UpperLeg_L"] + src_state(f)[0]["UpperLeg_R"]) * 0.5) * SCALE for f in frames]
n = len(frames); fm = sum(frames) / n
mx = sum(m.x for m in mids) / n; my = sum(m.y for m in mids) / n
sxx = sum((f - fm) ** 2 for f in frames)
bx = sum((f - fm) * (m.x - mx) for f, m in zip(frames, mids)) / sxx; by = sum((f - fm) * (m.y - my) for f, m in zip(frames, mids)) / sxx
def LP(f): return Vector((mx + bx * (f - fm), my + by * (f - fm), 0.0))
DIR = Vector((bx, by, 0)).normalized(); LEFT = Vector((0, 0, 1)).cross(DIR)
print('VW speed m/frame', round(math.hypot(bx, by), 4), 'dir', [round(x, 3) for x in DIR], flush=True)
def roll_of(P):
    hv = P["UpperLeg_L"] - P["UpperLeg_R"]; return math.atan2(hv.z, hv.dot(LEFT))
ROLL_MEAN = sum(roll_of(src_state(f)[0]) for f in frames) / n
ARM_MEAN = {}
for s in "lr":
    acc = Vector()
    for f in frames:
        P, R, T = src_state(f)
        Wc = R["Chest"] @ K["Chest"] @ AT["spine_03"].inverted() @ RR["spine_03"]
        Wu = R["UpperArm_" + s.upper()] @ K["UpperArm_" + s.upper()] @ AT["upperarm_" + s].inverted() @ RR["upperarm_" + s]
        acc += Wc.inverted() @ (Wu @ Vector((0, 1, 0)))
    ARM_MEAN[s] = acc.normalized()
def remap(p, f, ka, kl):
    lp = LP(f); r = p - lp; r.z = 0
    return lp + DIR * (r.dot(DIR) * ka) + LEFT * (r.dot(LEFT) * kl) + Vector((0, 0, p.z))

FINGER_CURL = {"01": 14, "02": 24, "03": 16}
ZOFF = 0.0
def solve(f, lift=0.0, want_lift=False):
    P, R, T = src_state(f)
    Wd = {tb: R[sb] @ K[sb] @ AT[tb].inverted() @ RR[tb] for tb, sb in S_MAP.items()}
    Rc = Wd["spine_03"]; lat = (Wd["spine_03"] @ RR["spine_03"].inverted() @ AT["spine_03"]).col[0]
    for s, sg in (("l", 1), ("r", -1)):
        ua, la = "upperarm_" + s, "lowerarm_" + s; d = Wd[ua] @ Vector((0, 1, 0))
        m = Rc @ ARM_MEAN[s]; q = m.rotation_difference(d); ax, an = q.to_axis_angle()
        extra = Quaternion(ax, an * PR['larm']) @ q.inverted(); d2 = extra @ d
        d3 = (d2 + lat * sg * math.tan(math.radians(PR['abd']))).normalized()
        tot = (d2.rotation_difference(d3) @ extra).to_matrix(); Wd[ua] = tot @ Wd[ua]; Wd[la] = tot @ Wd[la]
    # hip sway: amplify pelvis roll about the travel axis and the sideways hip shift
    Wd["pelvis"] = Matrix.Rotation((PR['sway'] - 1) * (roll_of(P) - ROLL_MEAN), 3, DIR) @ Wd["pelvis"]
    mid_src = (P["UpperLeg_L"] + P["UpperLeg_R"]) * 0.5 * SCALE
    mid_des = remap(mid_src, f, PR['stride'], PR['lat']) + Vector((0, 0, ZOFF + lift))
    dP = Wd["pelvis"] @ RR["pelvis"].inverted()
    mid_rest = (RH["thigh_l"] + RH["thigh_r"]) * 0.5
    pelvis_head = mid_des - dP @ (mid_rest - RH["pelvis"])
    feet = {}
    for s, S in (("l", "L"), ("r", "R")):
        A = P["Foot_" + S] * SCALE + Vector((0, 0, ZOFF))
        feet[s] = (A, remap(A, f, PR['stride'], PR['cross']))
    if want_lift:  # stance leg keeps its source extension
        lifts = []
        for s in "lr":
            A, A2 = feet[s]
            H0 = mid_src + Vector((0, 0, ZOFF)) - dP @ (mid_rest - RH["pelvis"]) + dP @ (RH["thigh_" + s] - RH["pelvis"])
            H1 = pelvis_head + dP @ (RH["thigh_" + s] - RH["pelvis"])
            d0 = min((H0 - A).length, (LEGA[s] + LEGB[s]) * 0.999); hz = (H1 - A2); hh = Vector((hz.x, hz.y, 0)).length
            need = math.sqrt(max(d0 * d0 - hh * hh, 0)); lifts.append((A.z, need - hz.z))
        lifts.sort(); low = lifts[0]
        grounded = [l for z, l in lifts if z < low[0] + 0.03]
        return min(grounded)
    M = {}
    def fk(name, rot, head=None):
        b = bones[name]
        if head is None: head = (M[b.parent.name] @ REL[name]).to_translation()
        m = rot.to_4x4(); m.translation = head; M[name] = m; return m
    for name in order:
        b = bones[name]
        if name.startswith(("thigh_", "calf_", "foot_", "ball_")): continue
        if name == "Root": M[name] = b.matrix_local.copy(); continue
        if name == "pelvis": fk(name, Wd[name], pelvis_head); continue
        if name in Wd: rot = Wd[name]
        else:
            rot = M[b.parent.name].to_3x3() @ REL[name].to_3x3()
            if name in ("hand_l", "hand_r"):
                sg = 1 if name == "hand_l" else -1
                rot = rot @ Matrix.Rotation(math.radians(-20 * sg), 3, "Y") @ Matrix.Rotation(math.radians(10), 3, "X")
            for sid, ang in FINGER_CURL.items():
                if name.endswith("_" + sid + "_l") or name.endswith("_" + sid + "_r"):
                    rot = rot @ Matrix.Rotation(math.radians(ang * (0.4 if name.startswith("thumb") else 1)), 3, "X")
        fk(name, rot)
    for s in "lr":
        th, ca, fo, ba = "thigh_" + s, "calf_" + s, "foot_" + s, "ball_" + s
        mt = fk(th, Wd[th]); H = mt.translation.copy()
        Kfk = H + Wd[th] @ Vector((0, LEGA[s], 0))
        Kn, A2 = two_bone(H, feet[s][1], LEGA[s], LEGB[s], Kfk)
        fk(th, rot_between(Kfk - H, Kn - H) @ Wd[th], H)
        fk(ca, rot_between(Wd[ca] @ Vector((0, 1, 0)), A2 - Kn) @ Wd[ca], Kn)
        fk(fo, Wd[fo], A2)
        fk(ba, M[fo].to_3x3() @ REL[ba].to_3x3())
    return M

lifts = {f: solve(f, want_lift=True) for f in frames}
sl = {f: sum(lifts[min(max(g, frames[0]), frames[-1])] for g in (f - 2, f - 1, f, f + 1, f + 2)) / 5 for f in frames}
print('VW lift cm min/max', round(min(sl.values()) * 100, 1), round(max(sl.values()) * 100, 1), flush=True)
ang = math.atan2(DIR.x, -DIR.y)  # rotate travel direction onto -Y
RZ = Matrix.Rotation(ang, 4, 'Z')
def inplace(f, M):
    G = RZ @ Matrix.Translation(-LP(f))
    return {k: (v.copy() if k == 'Root' else G @ v) for k, v in M.items()}
MS = {f: inplace(f, solve(f, sl[f])) for f in frames}
bpy.data.objects.remove(src, do_unlink=True)
print('VW heading check', [round(x, 3) for x in (MS[frames[n // 2]]['pelvis'].to_3x3() @ RR['pelvis'].inverted() @ Vector((0, -1, 0)))], flush=True)

# ------------------------------------------------------------------ cycle
def legsig(M): return [x for nm in ('thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'foot_l', 'foot_r') for x in M[nm].to_3x3().col[1]]
S0 = frames[int(n * PR['s0'])]; s0 = legsig(MS[S0])
errs = {lag: sum((a - b) ** 2 for a, b in zip(legsig(MS[S0 + lag]), s0)) for lag in range(22, 56) if S0 + lag in MS}
NF = min(errs, key=errs.get)
print('VW cycle', NF, 'frames err', round(errs[NF], 4), 'from', S0, flush=True)
seq = [M_to_B(MS[S0 + i]) for i in range(NF + 1)]
# pelvis drift left in the cycle -> remove linearly; then spread the seam residual over the loop
d_end = seq[NF]['pelvis'][0] - seq[0]['pelvis'][0]
for i in range(NF + 1):
    l, q = seq[i]['pelvis']; dl = d_end * (i / NF); seq[i]['pelvis'] = (l - Vector((dl.x, dl.y, 0)) if False else l, q)
# drift in world space: correct through M
Mseq = [B_to_M(B) for B in seq]
pw0, pw1 = Mseq[0]['pelvis'].translation, Mseq[NF]['pelvis'].translation
dr = pw1 - pw0; dr.z = 0
Mseq = [{k: (v.copy() if k == 'Root' else Matrix.Translation(-dr * (i / NF)) @ v) for k, v in M.items()} for i, M in enumerate(Mseq)]
print('VW residual drift cm', round(dr.length * 100, 2), flush=True)
seq = [M_to_B(M) for M in Mseq]
for nme in seq[0]:
    l0, q0 = seq[0][nme]; lN, qN = seq[NF][nme]
    if q0.dot(qN) < 0: qN = -qN
    dq = qN.inverted() @ q0; dl = l0 - lN
    for i in range(NF + 1):
        l, q = seq[i][nme]; w = i / NF
        seq[i][nme] = (l + dl * w, (q @ Quaternion().slerp(dq, w)).normalized())
# right arm: cigarette holder up by the shoulder, as in the idle; small counter-bob each step
RARM = [b for b in order if b.endswith('_r') and b not in ('thigh_r', 'calf_r', 'foot_r', 'ball_r')]
for i in range(NF + 1):
    for b in RARM: seq[i][b] = IDLE_B[0][b]
    l, q = seq[i]['upperarm_r']
    seq[i]['upperarm_r'] = (l, (q @ Quaternion(Vector((1, 0, 0)), math.radians(PR['bob'] * math.sin(4 * math.pi * i / NF)))).normalized())
seq = plant_Bs(seq)
seq[NF] = seq[0]

def pose_at(t):
    t = t % NF; i = int(math.floor(t)); w = t - i
    return blend_B(seq[i], seq[min(i + 1, NF)], w)

# stance-foot speed (m per source frame) and right-foot plant time
def fpos(B, nm): return B_to_M(B)[nm].translation.copy()
balls = [(fpos(B, 'ball_l'), fpos(B, 'ball_r')) for B in seq]
dys = []
for i in range(NF):
    for k in (0, 1):
        a, b = balls[i][k], balls[i + 1][k]
        if max(a.z, b.z) < min(balls[i][0].z, balls[i][1].z) + 0.02 and b.y - a.y > 0: dys.append(b.y - a.y)
V = sorted(dys)[len(dys) // 2]
cycle_len = V * NF
t_land = min(range(NF), key=lambda i: balls[i][1].y)
t_land_l = min(range(NF), key=lambda i: balls[i][0].y)
print('VW stance speed m/f', round(V, 4), 'cycle len m', round(cycle_len, 3), 'natural speed m/s', round(cycle_len / (NF / 30), 3), 'right plant t', t_land, flush=True)

# ------------------------------------------------------------------ vw_walk: 16 keys (frame 17 = frame 1)
walk = new_action('vw_walk')
WALK16 = [pose_at(k * NF / NF16) for k in range(NF16)]
for k, B in enumerate(WALK16 + [WALK16[0]]): key_B(B, k + 1)

# ------------------------------------------------------------------ idle stance: contrapposto, feet close
# weight on the right leg (hip up and out), left foot a little forward and turned out, knee soft
def idle_base():
    M = {k: v.copy() for k, v in IDLE_M0.items()}
    ph = M['pelvis'].translation.copy()
    G = Matrix.Translation(ph + Vector((-PR['ib_shift'], 0, -PR['ib_drop']))) @ Matrix.Rotation(math.radians(PR['ib_roll']), 4, 'Y') @ Matrix.Translation(-ph)
    M = {nm: (v.copy() if nm == 'Root' else G @ v) for nm, v in M.items()}
    B = M_to_B(M)
    l, q = B['spine_01']; B['spine_01'] = (l, (q @ Quaternion(Vector((0, 0, 1)), math.radians(-PR['ib_roll'] * 0.8))).normalized())
    M = B_to_M(B)
    # raise or lower the hips so the weight (right) leg is nearly straight over its foot
    fr0 = IDLE_M0['foot_r'].translation.copy(); fr0.x = -abs(PR['ib_fx'])
    H = M['thigh_r'].translation; hz = H - fr0; hh = Vector((hz.x, hz.y, 0)).length
    L = (LEGA['r'] + LEGB['r']) * PR['ib_straight']
    dz = math.sqrt(max(L * L - hh * hh, 0)) - hz.z
    M = {nm: (v.copy() if nm == 'Root' else Matrix.Translation((0, 0, dz)) @ v) for nm, v in M.items()}
    print('VW idle base hip lift cm', round(dz * 100, 2), flush=True)
    for sd, dx, dy, turn in (('r', -PR['ib_fx'], 0.0, -8.0), ('l', PR['ib_fx'] * 0.6, -PR['ib_fy'], 16.0)):
        f0 = IDLE_M0['foot_' + sd]; R0 = f0.to_3x3()
        Rf = Matrix.Rotation(math.radians(turn), 3, 'Z') @ R0
        a0 = f0.translation.copy(); a0.x = (1 if sd == 'l' else -1) * abs(dx); a0.y += dy
        leg_ik(M, sd, a0, Rf)
    return M
IDLE_M0 = idle_base(); IDLE_B[0] = M_to_B(IDLE_M0)
IDLE_B[0] = plant_Bs([IDLE_B[0]])[0]; IDLE_M0 = B_to_M(IDLE_B[0])

# ------------------------------------------------------------------ vw_stop
FPS = PR['clip_fps']; inc0 = 30.0 / FPS
incs = [inc0 * (1 - PR['decel'] * (k / 8.0)) for k in range(8)]
t0 = t_land - sum(incs[:7])
step = NF / NF16; q0 = round(t0 / step); t0q = q0 * step  # start on a walk-loop key so the loop and the clip join
incs = [x * (t_land - t0q) / sum(incs[:7]) for x in incs]; t0 = t0q; q0 = q0 % NF16
ts = [t0]
for k in range(7): ts.append(ts[-1] + incs[k])
CM = []; roots = []
for k in range(8):
    tt = ts[k] - t0; tr = Matrix.Translation((0, -V * tt, 0))
    M = B_to_M(pose_at(ts[k])); CM.append({nm: (v.copy() if nm == 'Root' else tr @ v) for nm, v in M.items()})
    roots.append(Vector((0, -V * tt, 0)))
MA = CM[7]; BA = M_to_B(MA)
TURN = math.radians(PR['turn']); RT3 = Matrix.Rotation(TURN, 3, 'Z'); RT4 = Matrix.Rotation(TURN, 4, 'Z')
off_r = REL['ball_r'].translation
B_R = MA['ball_r'].translation.copy()
ball_idle = IDLE_M0['ball_r'].translation
Tfin = B_R - RT3 @ ball_idle; Tfin.z = 0
X = Matrix.Translation(Tfin) @ RT4
MF = {nm: (v.copy() if nm == 'Root' else X @ v) for nm, v in IDLE_M0.items()}
pA, pA_prev = MA['pelvis'].translation.copy(), CM[6]['pelvis'].translation.copy()
vA = (pA - pA_prev) * 16
qA = MA['pelvis'].to_quaternion(); qF = MF['pelvis'].to_quaternion()
rA, rA_prev = roots[7], roots[6]; vR = (rA - rA_prev) * 16
LEGB_N = {'thigh_l', 'calf_l', 'foot_l', 'ball_l', 'thigh_r', 'calf_r', 'foot_r', 'ball_r'}
fl0 = MA['foot_l'].copy(); flF = MF['foot_l'].copy()
frR0 = MA['foot_r'].to_quaternion(); frRF = MF['foot_r'].to_quaternion()
for k in range(8, 24):
    u = (k - 7) / 16.0
    wb = ss(u / 0.75); wp = min(1.0, u / 0.85)
    B = blend_B(BA, IDLE_B[0], wb)
    pp = herm(pA, vA * 0.85, MF['pelvis'].translation, ss(wp) if False else wp) if wp < 1 else MF['pelvis'].translation.copy()
    # pelvis: momentum carried in, settles on the idle stance
    pq = qs(qA, qF, ss(wp))
    M = B_to_M(B)
    Pm = pq.to_matrix().to_4x4(); Pm.translation = pp
    G = Pm @ M['pelvis'].inverted()
    M = {nm: (v.copy() if nm == 'Root' else G @ v) for nm, v in M.items()}
    # right foot pivots on the ball, left foot steps round beside it
    rq = qs(frR0, frRF, wb).to_matrix()
    leg_ik(M, 'r', B_R - rq @ off_r, rq)
    wl = ss((k - 8) / 9.0)
    al = fl0.translation.lerp(flF.translation, wl) + Vector((0, 0, 0.055 * math.sin(math.pi * wl)))
    leg_ik(M, 'l', al, qs(fl0.to_quaternion(), flF.to_quaternion(), wl).to_matrix())
    CM.append(M)
    roots.append(herm(rA, vR * 0.85, Tfin, wp) if wp < 1 else Tfin.copy())
stop = new_action('vw_stop')
STOP_B = [M_to_B(M) for M in CM]
for k, B in enumerate(STOP_B): key_B(B, k + 1)
# heading at clip start is -Y; export root in (forward, left) of the start heading
root_fl = [[round(-r.y, 4), round(r.x, 4)] for r in roots]
print('VW stop root', root_fl[0], root_fl[7], root_fl[-1], flush=True)

# ------------------------------------------------------------------ vw_idle
# matches the approved AI idle clip: slow weight shift and hip sway, soft breathing, gentle head tilt and turn,
# feet planted (IK), cigarette hand up; blinks are painted in later
IN = int(PR['idle_n'])
def rq(axis, deg): return Quaternion(Vector(axis), math.radians(deg))
def mulb(B, n, q):
    l, q0 = B[n]; B[n] = (l, (q0 @ q).normalized())
NEW_IDLE = []
for k in range(IN):
    t = 2 * math.pi * k / IN
    B = dict(IDLE_B[0])
    mulb(B, 'spine_01', rq((0, 0, 1), -1.2 * math.sin(t)))
    mulb(B, 'spine_02', rq((1, 0, 0), 0.6 * math.sin(2 * t)))
    mulb(B, 'spine_03', rq((1, 0, 0), 1.0 * math.sin(2 * t)))
    mulb(B, 'neck_01', rq((0, 0, 1), 1.0 * math.sin(t)))
    mulb(B, 'head', rq((0, 0, 1), 2.5 * math.sin(t)) @ rq((0, 1, 0), 3.0 * math.sin(t)) @ rq((1, 0, 0), -1.2 * math.sin(2 * t)))
    mulb(B, 'upperarm_l', rq((1, 0, 0), 1.5 * math.sin(t)))
    mulb(B, 'upperarm_r', rq((1, 0, 0), 1.0 * math.sin(2 * t)))
    M = B_to_M(B)
    ph = M['pelvis'].translation.copy()
    G = Matrix.Translation(Vector((0.016 * math.sin(t), 0, -0.004 * (1 - math.cos(2 * t)) / 2)) + ph) @         (Matrix.Rotation(math.radians(1.8 * math.sin(t)), 4, 'Y') @ Matrix.Rotation(math.radians(1.5 * math.sin(t)), 4, 'Z')) @ Matrix.Translation(-ph)
    M = {nm: (v.copy() if nm == 'Root' else G @ v) for nm, v in M.items()}
    for sd in 'lr':
        f0 = IDLE_M0['foot_' + sd]; leg_ik(M, sd, f0.translation.copy(), f0.to_3x3())
    NEW_IDLE.append(M_to_B(M))
idle = new_action('vw_idle')
for k in range(IN): key_B(NEW_IDLE[k], k + 1)
key_B(NEW_IDLE[0], IN + 1)

# ------------------------------------------------------------------ vw_sim: one continuous 16 fps timeline for the cloth
# settle (rest -> walk pose) | 5 walk cycles travelling -Y | stop clip | idle x2 (each idle sample held 2 frames)
NC = 5; SETTLE = 12
sim = new_action('vw_sim'); sc.render.fps = 16
tgt.keyframe_insert('location', frame=1); tgt.keyframe_insert('rotation_euler', frame=1)
REST_B = {pb.name: (Vector(), Quaternion()) for pb in tgt.pose.bones}
fr = 1; sets = {'walk': [None] * NF16, 'stop': [], 'idle': [], 'pose': []}
first = pose_at(t0 - NC * NF)
for j in range(SETTLE):
    key_B(blend_B(REST_B, first, ss(j / (SETTLE - 1))), fr); tgt.location = (0, 0, 0); tgt.keyframe_insert('location', frame=fr); fr += 1
for j in range(NC * NF16):
    key_B(pose_at(t0 + (j - NC * NF16) * step), fr)
    tgt.location = (0, -V * step * j, 0); tgt.keyframe_insert('location', frame=fr)
    if j >= (NC - 1) * NF16: sets['walk'][(q0 + j) % NF16] = [fr, 0.0, -V * step * j, 0.0]
    fr += 1
LOC = Vector((0, -V * step * NC * NF16, 0))
for k, B in enumerate(STOP_B):
    key_B(B, fr); tgt.location = LOC; tgt.rotation_euler = (0, 0, 0)
    tgt.keyframe_insert('location', frame=fr); tgt.keyframe_insert('rotation_euler', frame=fr)
    sets['stop'].append([fr, LOC.x + roots[k].x, LOC.y + roots[k].y, TURN]); fr += 1
IL = LOC + Tfin
tgt.rotation_euler = (0, 0, TURN); tgt.location = IL
for k in range(2 * IN):
    key_B(NEW_IDLE[k % IN], fr)
    tgt.keyframe_insert('location', frame=fr); tgt.keyframe_insert('rotation_euler', frame=fr)
    if k >= IN: sets['idle'].append([fr, IL.x, IL.y, TURN])
    fr += 2
tgt.rotation_euler = (0, 0, 0)
sets['pose'] = [sets['idle'][0]]
for fc in sim.fcurves if hasattr(sim, 'fcurves') else []:
    pass
sc.frame_start, sc.frame_end = 1, fr
print('VW sim frames', fr, 'walk loop keys from', sets['walk'][0][0], 'stop from', sets['stop'][0][0], 'idle from', sets['idle'][0][0], flush=True)
sc['vw'] = json.dumps({'nf': NF16, 'stop': 24, 'idle': IN, 'turn': PR['turn'], 'stop_root': [[r.x, r.y] for r in roots], 'sets': sets})
use_action(sim)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
json.dump({'bvh': BVH.replace('\\', '/').split('/')[-1], 'params': PR, 'src_cycle_frames': NF, 'src_fps': 30,
           'walk_frames': NF16, 'cycle_len': round(cycle_len, 4), 'natural_speed': round(cycle_len / (NF / 30), 4),
           'plants': [round(t_land / NF, 4), round(t_land_l / NF, 4)], 'stop_heels': sorted(set([k for k in range(1, 8) if any(int((ts[k - 1]) // (NF / 1.0) * 0) == 0 and ((ts[k - 1] - tl) % NF) > ((ts[k] - tl) % NF) for tl in (t_land, t_land_l))] + [7, 17])),
           'stop_frames': 24, 'stop_fps': FPS, 'stop_start_phase': round((t0 % NF) / NF, 4), 'turn_deg': PR['turn'],
           'stop_root_fwd_left': root_fl, 'idle_frames': IN, 'idle_fps': IN / 4.0, 'idle_blink': [10, 11, 12]}, open(OUTJ, 'w'), indent=1)
mx = 0.0
for k in range(1, fr):
    sc.frame_set(k)
    for pb in tgt.pose.bones:
        if pb.name not in ('Root', 'pelvis'): mx = max(mx, pb.location.length)
print('VW bone-length audit: max non-root bone offset mm', round(mx * 1000, 3), flush=True)
print('VW saved', flush=True)
