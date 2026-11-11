"""Export Vela's motion (walk loop, stop-and-turn, clip1-style idle) as clean clips on a standard Mixamo skeleton.
Source: the vw_walk / vw_stop / vw_idle actions on the MPFB game_engine rig (vw_v1.blend, built by vw_motion.py).
Target: a Mixamo-named armature in T-pose with Vela's bone lengths. Each target bone takes the world rotation of its source bone
(the same Y = bone direction and X axis), so the pose is exact; the T rest pose is only the reference that retargeters compare against.
Output: OUTDIR/vela_<clip>.fbx, .glb, .bvh per clip, all clips in vela_clips.glb, vela_mixamo_clips.blend.
Usage: blender -b vw_v1.blend -P vw_export_clips.py -- OUTDIR"""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; src = bpy.data.objects['Vela']
VW = json.loads(sc['vw'])
SB = src.data.bones
# ------------------------------------------------------------------ bone map: mixamo name, source bone, source joint that ends it (None = tail)
MAP = [('Hips', 'pelvis', 'spine_01'), ('Spine', 'spine_01', 'spine_02'), ('Spine1', 'spine_02', 'spine_03'), ('Spine2', 'spine_03', 'neck_01'),
       ('Neck', 'neck_01', 'head'), ('Head', 'head', None)]
for S, s in (('Left', 'l'), ('Right', 'r')):
    MAP += [(S + 'Shoulder', 'clavicle_' + s, 'upperarm_' + s), (S + 'Arm', 'upperarm_' + s, 'lowerarm_' + s), (S + 'ForeArm', 'lowerarm_' + s, 'hand_' + s),
            (S + 'Hand', 'hand_' + s, 'middle_01_' + s)]
    for F, f in (('Thumb', 'thumb'), ('Index', 'index'), ('Middle', 'middle'), ('Ring', 'ring'), ('Pinky', 'pinky')):
        for k in (1, 2, 3):
            MAP.append((f'{S}Hand{F}{k}', f'{f}_0{k}_{s}', f'{f}_0{k + 1}_{s}' if k < 3 else None))
    MAP += [(S + 'UpLeg', 'thigh_' + s, 'calf_' + s), (S + 'Leg', 'calf_' + s, 'foot_' + s), (S + 'Foot', 'foot_' + s, 'ball_' + s), (S + 'ToeBase', 'ball_' + s, None)]
PARENT = {'Hips': None, 'Spine': 'Hips', 'Spine1': 'Spine', 'Spine2': 'Spine1', 'Neck': 'Spine2', 'Head': 'Neck'}
for S in ('Left', 'Right'):
    PARENT.update({S + 'Shoulder': 'Spine2', S + 'Arm': S + 'Shoulder', S + 'ForeArm': S + 'Arm', S + 'Hand': S + 'ForeArm',
                   S + 'UpLeg': 'Hips', S + 'Leg': S + 'UpLeg', S + 'Foot': S + 'Leg', S + 'ToeBase': S + 'Foot'})
    for F in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        PARENT.update({f'{S}Hand{F}1': S + 'Hand', f'{S}Hand{F}2': f'{S}Hand{F}1', f'{S}Hand{F}3': f'{S}Hand{F}2'})
SRC = {t: (b, e) for t, b, e in MAP}
ORDER = [t for t, _, _ in MAP]

def sdir(heads, tails, b, e):  # source bone direction and length from joint positions
    v = (heads[e] - heads[b]) if e else (tails[b] - heads[b]); return v
def rot_from(y, xh):
    y = y.normalized(); x = (xh - y * xh.dot(y)); x = x.normalized() if x.length > 1e-8 else y.orthogonal().normalized(); z = x.cross(y)
    return Matrix((x, y, z)).transposed()

# ------------------------------------------------------------------ target rest: T-pose (arms out along +-X, legs straight down)
RH = {b.name: b.head_local.copy() for b in SB}; RT = {b.name: b.tail_local.copy() for b in SB}; RX = {b.name: b.matrix_local.to_3x3().col[0].copy() for b in SB}
joint = {}; tdir = {}; tx = {}; carry = {}
for t, b, e in MAP:
    d = sdir(RH, RT, b, e); joint[t] = RH[b].copy(); tdir[t] = d.copy(); carry[t] = Quaternion()
def straighten(chain, axis):
    """re-aim a chain of target bones along axis from the first joint, carrying the descendants rigidly"""
    for t in chain:
        q = tdir[t].normalized().rotation_difference(axis); kids = [c for c in ORDER if is_desc(c, t)]
        for c in kids: joint[c] = joint[t] + q @ (joint[c] - joint[t]); tdir[c] = q @ tdir[c]; carry[c] = q @ carry[c]
        tdir[t] = axis * tdir[t].length; carry[t] = q @ carry[t]
def is_desc(c, t):
    p = PARENT.get(c)
    while p:
        if p == t: return True
        p = PARENT.get(p)
    return False
for S, sg in (('Left', 1), ('Right', -1)):
    straighten([S + 'Arm', S + 'ForeArm', S + 'Hand'], Vector((sg, 0, 0)))
    straighten([S + 'UpLeg', S + 'Leg'], Vector((0, 0, -1)))
# target rest X axis: the source rest X carried by the minimal rotation from the source direction to the target direction
for t, b, e in MAP:
    tx[t] = carry[t] @ RX[b]

# ------------------------------------------------------------------ build the Mixamo armature
for o in list(sc.objects): o.select_set(False)
ad = bpy.data.armatures.new('VelaMixamo'); arm = bpy.data.objects.new('Armature', ad); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
EB = {}
for t in ORDER:
    eb = ad.edit_bones.new('mixamorig:' + t); eb.head = joint[t]; eb.tail = joint[t] + tdir[t]
    eb.align_roll(tx[t].cross(tdir[t].normalized())); EB[t] = eb
for t in ORDER:
    if PARENT[t]: EB[t].parent = EB[PARENT[t]]; EB[t].use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
TB = {t: ad.bones['mixamorig:' + t] for t in ORDER}
TR = {t: TB[t].matrix_local.to_3x3() for t in ORDER}
C0 = {t: rot_from(sdir(RH, RT, SRC[t][0], SRC[t][1]), RX[SRC[t][0]]) for t in ORDER}
K = {t: C0[t].inverted() @ carry[t].to_matrix().inverted() @ TR[t] for t in ORDER}
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
print('VX built', len(ORDER), 'bones; rest X check',
      round(max((TR[t].col[0] - tx[t].normalized()).length for t in ORDER), 4), flush=True)

# ------------------------------------------------------------------ bake
def use(name):
    a = bpy.data.actions[name]; src.animation_data.action = a
    if src.animation_data.action_slot is None and len(a.slots): src.animation_data.action_slot = a.slots[0]
def source_pose(f):
    sc.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    P = {pb.name: pb.matrix.copy() for pb in src.pose.bones}
    heads = {n: m.translation.copy() for n, m in P.items()}; tails = {pb.name: pb.tail.copy() for pb in src.pose.bones}
    return P, heads, tails
def bake(clip, samples, root_step=None):
    act = bpy.data.actions.new('vela_' + clip); act.use_fake_user = True
    arm.animation_data_create(); arm.animation_data.action = act
    src.location = (0, 0, 0); src.rotation_euler = (0, 0, 0)
    prevq = {}
    for i, f in enumerate(samples):
        P, H, T = source_pose(f)
        W = {}
        for t in ORDER:
            b, e = SRC[t]; W[t] = rot_from(sdir(H, T, b, e), P[b].to_3x3().col[0]) @ K[t]
        for t in ORDER:
            pb = arm.pose.bones['mixamorig:' + t]
            if PARENT[t] is None:
                Rb = TR[t].inverted() @ W[t]; p = H[SRC[t][0]].copy()
                if root_step: p += root_step * i
                pb.location = TR[t].inverted() @ (p - TB[t].head_local); pb.keyframe_insert('location', frame=i + 1)
            else:
                rel = (TB[PARENT[t]].matrix_local.inverted() @ TB[t].matrix_local).to_3x3()
                Rb = rel.inverted() @ W[PARENT[t]].inverted() @ W[t]
            q = Rb.to_quaternion()
            if t in prevq and prevq[t].dot(q) < 0: q.negate()
            prevq[t] = q; pb.rotation_quaternion = q; pb.keyframe_insert('rotation_quaternion', frame=i + 1)
    # check: joint positions of the baked target against the source at a few frames
    err = 0.0
    for i in range(0, len(samples), max(1, len(samples) // 6)):
        sc.frame_set(i + 1); _, H, _ = source_pose(samples[i]); sc.frame_set(i + 1)
        for t in ORDER:
            p = (arm.matrix_world @ arm.pose.bones['mixamorig:' + t].head) - ((root_step * i) if root_step else Vector())
            err = max(err, (p - H[SRC[t][0]]).length)
    print('VX', clip, len(samples), 'frames, max joint error vs source mm', round(err * 1000, 2), flush=True)
    return act, err

J = json.load(open(os.path.join(os.path.dirname(bpy.data.filepath), 'vw_v1.json')))
clips = {}
use('vw_walk'); NFsrc = J['src_cycle_frames']  # one gait cycle = NFsrc frames at 30 fps in the mocap; vw_walk holds it in 16 keys (17 = 1)
walk_s = [1 + k * 16.0 / NFsrc for k in range(NFsrc + 1)]
clips['walk_inplace'] = bake('walk_inplace', walk_s)
use('vw_walk'); clips['walk_root'] = bake('walk_root', walk_s, root_step=Vector((0, -J['cycle_len'] / NFsrc, 0)))
use('vw_stop'); n_stop = int(math.floor((VW['stop'] - 1) / J['stop_fps'] * 30)) + 1
clips['stop_turn'] = bake('stop_turn', [1 + k * J['stop_fps'] / 30.0 for k in range(n_stop)])
use('vw_idle'); IN = VW['idle']; idle_s = [1 + k * IN / 120.0 for k in range(121)]  # vw_idle: IN keys over 4 s, key IN+1 = key 1
clips['idle'] = bake('idle', idle_s)
sc.render.fps = 30
# ------------------------------------------------------------------ export
src.hide_viewport = False
def only(o):
    for x in sc.objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o
meta = {'skeleton': 'Mixamo (mixamorig:*), T-pose rest, metres, Z up in Blender / Y up in FBX and glTF, she faces -Y in Blender (+Z in glTF)', 'fps': 30, 'clips': {}}
for name, (act, err) in clips.items():
    arm.animation_data.action = act; n = int(act.frame_range[1]); sc.frame_start, sc.frame_end = 1, n
    only(arm)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f'vela_{name}.fbx'), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                             bake_anim_simplify_factor=0.0, armature_nodetype='NULL')
    bpy.ops.export_anim.bvh(filepath=os.path.join(OUT, f'vela_{name}.bvh'), frame_start=1, frame_end=n, rotate_mode='NATIVE', root_transform_only=False)
    meta['clips'][name] = {'frames': n, 'seconds': round((n - 1) / 30, 4), 'max_joint_error_mm': round(err * 1000, 2)}
# one GLB with all four clips as animations
arm.animation_data.action = None
for name, (act, _) in clips.items():
    tr = arm.animation_data.nla_tracks.new(); tr.name = act.name; tr.strips.new(act.name, 1, act); tr.mute = False
only(arm)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'vela_clips.glb'), use_selection=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                          export_force_sampling=True, export_frame_range=False, export_def_bones=False)
bpy.data.objects.remove(src, do_unlink=True)
for o in list(sc.objects):
    if o != arm: bpy.data.objects.remove(o, do_unlink=True)
meta['walk'] = {'cycle_m': J['cycle_len'], 'natural_speed_mps': J['natural_speed'], 'foot_plants_phase': J['plants'], 'stop_starts_at_walk_phase': J['stop_start_phase'],
                'stop_turn_deg_to_her_left': J['turn_deg'], 'stop_root_end_m': J['stop_root_fwd_left'][-1]}
json.dump(meta, open(os.path.join(OUT, 'clips.json'), 'w'), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'vela_mixamo_clips.blend'))
print('VX done', json.dumps(meta['clips']), flush=True)
