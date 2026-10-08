"""Cloth-simulate Vela's pencil skirt over the vw_sim timeline and bake it to a disk cache next to the blend.
Usage: blender -b vw_X.blend -P vw_cloth.py -- [key=value ...]   (saves in place)"""
import bpy, sys, math, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PR = dict(mass=0.18, tension=30.0, compression=30.0, shear=12.0, bending=0.6, quality=12, dist=0.005, shrink=0.0, pin_hi=0.06, pin_lo=0.18, inset=0.004)
for a in argv:
    k, v = a.split('='); PR[k] = float(v)
sc = bpy.context.scene; arm = bpy.data.objects['Vela']
sk = bpy.data.objects['Vela.skirt']; lg = bpy.data.objects.get('Vela.legs_under')
hip_z = arm.data.bones['thigh_l'].head_local.z
sc.frame_set(1)
def ss(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
# pin group: waistband and hips follow the rig, the rest hangs
pg = sk.vertex_groups.get('pin') or sk.vertex_groups.new(name='pin')
for v in sk.data.vertices:
    w = ss((v.co.z - (hip_z - PR['pin_lo'])) / (PR['pin_lo'] - PR['pin_hi']))
    pg.add([v.index], w, 'REPLACE')
# legs under the skirt must start inside it
if lg:
    sm = sk.data  # rest shell, no solidify
    bvh = BVHTree.FromPolygons([v.co.copy() for v in sm.vertices], [p.vertices[:] for p in sm.polygons])
    cen = {}
    for v in sm.vertices:
        c = cen.setdefault(round(v.co.z / 0.02), [Vector(), 0]); c[0] += v.co; c[1] += 1
    def axis(z):
        k = round(z / 0.02)
        for d in (0, 1, -1, 2, -2, 3, -3, 4, -4):
            if k + d in cen: c = cen[k + d]; return c[0] / c[1]
        return Vector()
    moved = 0
    for v in lg.data.vertices:
        loc, nrm, idx, d = bvh.find_nearest(v.co)
        if loc is None: continue
        out = loc - axis(loc.z); out.z = 0
        if nrm.dot(out) < 0: nrm = -nrm
        s = (v.co - loc).dot(nrm)
        if s > -PR['inset']:
            v.co = loc - nrm * PR['inset'] * 1.5; moved += 1
    lg.data.update()
    print('VWC legs pushed inside the skirt', moved, 'of', len(lg.data.vertices), flush=True)
    for m in [m for m in lg.modifiers if m.type == 'COLLISION']: lg.modifiers.remove(m)
    col = lg.modifiers.new('collision', 'COLLISION')
    cs = lg.collision; cs.thickness_outer = 0.002; cs.thickness_inner = 0.02; cs.cloth_friction = 2.0
for m in [m for m in sk.modifiers if m.type == 'CLOTH']: sk.modifiers.remove(m)
cl = sk.modifiers.new('cloth', 'CLOTH')
names = [m.name for m in sk.modifiers]
bpy.context.view_layer.objects.active = sk
with bpy.context.temp_override(object=sk):
    while sk.modifiers.find('cloth') > 1: bpy.ops.object.modifier_move_up(modifier='cloth')
print('VWC skirt stack', [m.type for m in sk.modifiers], flush=True)
st = cl.settings
st.quality = int(PR['quality']); st.mass = PR['mass']; st.air_damping = 1.0
st.tension_stiffness = PR['tension']; st.compression_stiffness = PR['compression']; st.shear_stiffness = PR['shear']; st.bending_stiffness = PR['bending']
st.tension_damping = 5; st.compression_damping = 5; st.shear_damping = 5
st.vertex_group_mass = 'pin'; st.pin_stiffness = 3.0
st.shrink_min = PR['shrink']
cc = cl.collision_settings; cc.use_collision = True; cc.distance_min = PR['dist']; cc.collision_quality = 4; cc.use_self_collision = False
pc = cl.point_cache; pc.frame_start = sc.frame_start; pc.frame_end = sc.frame_end
bpy.ops.wm.save_mainfile()
pc.use_disk_cache = True; pc.name = 'skirt'
bpy.ops.wm.save_mainfile()
import time; t = time.time()
with bpy.context.temp_override(scene=sc, point_cache=pc):
    bpy.ops.ptcache.bake(bake=True)
print('VWC baked', pc.is_baked, round(time.time() - t), 's frames', sc.frame_start, sc.frame_end, flush=True)
bpy.ops.wm.save_mainfile()
