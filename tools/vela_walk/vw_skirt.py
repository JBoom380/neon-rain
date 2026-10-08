"""Reshape Vela's skirt into a pencil skirt that walks as one tube.
Usage: blender -b vela_anim.blend -P vw_skirt.py -- OUT.blend [taper=0.8] [ramp=0.26] [pel=0.35]"""
import bpy, sys, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; PR = dict(taper=0.92, ramp=0.10, pel=0.0, inset=0.012, legs=0.0)
for a in argv[1:]:
    k, v = a.split('='); PR[k] = float(v)
sk = bpy.data.objects['Vela.skirt']; arm = bpy.data.objects['Vela']; me = sk.data
B = arm.data.bones
hip_z = B['thigh_l'].head_local.z
vs = me.vertices
zs = [v.co.z for v in vs]; top, hem = max(zs), min(zs)
# horizontal extent per height band
def band(z0, z1):
    p = [v.co for v in vs if z0 <= v.co.z < z1]
    return (min(c.x for c in p), max(c.x for c in p), min(c.y for c in p), max(c.y for c in p)) if p else None
prof = []
z = hem
while z < top:
    b = band(z, z + 0.02)
    if b: prof.append((round(z, 3), round(b[1] - b[0], 3), round(b[3] - b[2], 3)))
    z += 0.04
print('SK before z,width,depth', prof, flush=True)
wide = max([r for r in prof if r[0] > hip_z - 0.16], key=lambda r: r[1])
z_w = wide[0] + 0.01
print('SK top', round(top, 3), 'hem', round(hem, 3), 'hip_z', round(hip_z, 3), 'widest at', z_w, flush=True)
def ss(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
# centre line per height (x mid, y mid)
cent = {}
for v in vs:
    k = round(v.co.z / 0.01); c = cent.setdefault(k, [0, 0, 0]); c[0] += v.co.x; c[1] += v.co.y; c[2] += 1
def cxy(z):
    k = round(z / 0.01)
    for d in (0, 1, -1, 2, -2, 3, -3):
        if k + d in cent: c = cent[k + d]; return c[0] / c[2], c[1] / c[2]
    return 0, 0
for v in vs:
    if v.co.z < z_w:
        t = ss((z_w - v.co.z) / (z_w - hem))
        f = 1 - (1 - PR['taper']) * t
        cx, cy = cxy(v.co.z)
        v.co.x = cx + (v.co.x - cx) * f
        v.co.y = cy + (v.co.y - cy) * (1 - (1 - PR['taper']) * 0.4 * t)
me.update()
prof2 = []
z = hem
while z < top:
    b = band(z, z + 0.02)
    if b: prof2.append((round(z, 3), round(b[1] - b[0], 3), round(b[3] - b[2], 3)))
    z += 0.04
print('SK after', prof2, flush=True)
# skinning: one tube; thighs blended over a wide ramp, a share of pelvis to the hem
for g in list(sk.vertex_groups): sk.vertex_groups.remove(g)
G = {n: sk.vertex_groups.new(name=n) for n in ('spine_01', 'pelvis', 'thigh_l', 'thigh_r')}
for v in vs:
    z = v.co.z
    w_sp = ss((z - (top - 0.06)) / 0.06) * 0.6
    down = ss((hip_z + 0.02 - z) / (hip_z + 0.02 - hem))  # 0 at the hips, 1 at the hem
    w_pel = (1 - w_sp) * (1 - down * (1 - PR['pel']))
    rest = max(0.0, 1 - w_sp - w_pel)
    side = ss(0.5 + v.co.x / PR['ramp'])
    for n, w in (('spine_01', w_sp), ('pelvis', w_pel), ('thigh_l', rest * side), ('thigh_r', rest * (1 - side))):
        if w > 1e-4: G[n].add([v.index], w, 'REPLACE')
# level the hem
import bmesh
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
hv = [v for v in bm.verts if v.is_boundary and v.co.z < hem + 0.05]
for v in hv: v.co.z = hem
bm.to_mesh(me); bm.free(); me.update()
print('SK hem verts levelled', len(hv), flush=True)
# thighs under the skirt: the dressed body had them deleted; bring them back from the undressed body
if PR['legs']:
  HUMAN = r'E:\claude\Tools\hunyuan3d\v4\vela_human.blend'
  with bpy.data.libraries.load(HUMAN) as (src, dst): dst.objects = ['Vela.body']
  lg = dst.objects[0]; lg.name = 'Vela.legs_under'; bpy.context.scene.collection.objects.link(lg)
  lm = lg.data.copy(); lg.data = lm
  if lm.shape_keys:
      lg.shape_key_add(name='mix', from_mix=True)
      kb = lm.shape_keys.key_blocks; mixco = [v.co.copy() for v in kb['mix'].data]
      lg.shape_key_clear()
      for v, c in zip(lm.vertices, mixco): v.co = c
  for m in list(lg.modifiers):
      if m.type != 'ARMATURE': lg.modifiers.remove(m)
      else: m.object = arm
  lg.parent = arm
  hg = lg.vertex_groups.get('HelperGeometry')
  body = bpy.data.objects['Vela.body']
  lo_z, hi_z = hem - 0.005, hip_z - 0.02
  bm = bmesh.new(); bm.from_mesh(lm); bm.normal_update(); dl = bm.verts.layers.deform.verify()
  kill = [v for v in bm.verts if not (lo_z < v.co.z < hi_z and abs(v.co.x) > 0.015) or (hg and v[dl].get(hg.index, 0) > 0.5)]
  bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.normal_update()
  for v in bm.verts:
      v.co -= v.normal * PR['inset']
  bm.to_mesh(lm); bm.free(); lm.update()
  lm.materials.clear(); lm.materials.append(body.data.materials[0])
  for p in lm.polygons: p.use_smooth = True
  from mathutils.kdtree import KDTree
  kd = KDTree(len(body.data.vertices))
  for i, v in enumerate(body.data.vertices): kd.insert(v.co, i)
  kd.balance()
  ds = sorted(kd.find(v.co)[2] for v in lm.vertices if v.co.z < hem + 0.04)
  print('SK legs_under verts', len(lm.vertices), 'fit to body at the knee mm: median', round(ds[len(ds) // 2] * 1000, 2) if ds else None, flush=True)
# lining: the inside of the skirt, dark, so a gap between the panels never shows the void
ln = sk.copy(); ln.data = sk.data.copy(); ln.name = 'Vela.skirt_lining'; bpy.context.scene.collection.objects.link(ln)
for m in list(ln.modifiers):
    if m.type == 'SOLIDIFY': ln.modifiers.remove(m)
bm = bmesh.new(); bm.from_mesh(ln.data); bm.normal_update()
for v in bm.verts: v.co -= v.normal * 0.008
bm.to_mesh(ln.data); bm.free()
lmat = bpy.data.materials.new('lining'); lmat.use_nodes = True
lmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.05, 0.004, 0.004, 1)
lmat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
ln.data.materials.clear(); ln.data.materials.append(lmat)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('SK saved', flush=True)
