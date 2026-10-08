"""Render Vela guide passes for the paint-over pipeline.
Usage: blender -b vw_mX.blend -P vw_render.py -- OUTDIR SETS [engine=eevee|workbench] [passes=color,depth,normal] [frames=..]
SETS: comma list of walk, stop, idle, pose. Angles: camera azimuth about +Z measured from her facing, CCW from above
(a045 = camera toward her left-front). Orthographic 2.0 m tall frame, 512x1024, ground at row ~1009, root at x=256.
Writes OUTDIR/<set>/a<az>/<pass>_<ff>.png and OUTDIR/<set>/a<az>/kp.json (openpose COCO-18 pixel coords)."""
import bpy, sys, os, math, json
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:]
OUTDIR, SETS = argv[0], argv[1].split(',')
OPT = dict(hide='', engine='eevee', passes='color,depth,normal', frames='', angles='0,45,90,135,180,225,270,315')
for a in argv[2:]:
    k, v = a.split('='); OPT[k] = v
PASSES = OPT['passes'].split(',')
for _h in [h for h in OPT['hide'].split('+') if h]: bpy.data.objects[_h].hide_render = True
W, H, OS, CZ, DIST = 512, 1024, 2.0, 0.97, 6.0
sc = bpy.context.scene; arm = bpy.data.objects['Vela']
VW = json.loads(sc['vw'])
for o in list(sc.objects):
    if o.type in ('CAMERA', 'LIGHT'): bpy.data.objects.remove(o)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.film_transparent = True
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
w = bpy.data.worlds.new('vw'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.2, 0.2, 0.22, 1); bg.inputs[1].default_value = 0.7
cam = bpy.data.cameras.new('vwcam'); cam.type = 'ORTHO'; cam.ortho_scale = OS; cam.clip_start = 0.1; cam.clip_end = 20
co = bpy.data.objects.new('vwcam', cam); sc.collection.objects.link(co); sc.camera = co
def light(name, loc, energy, size, col=(1, 1, 1)):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.color = col
    ob = bpy.data.objects.new(name, L); sc.collection.objects.link(ob); ob.parent = co
    ob.location = loc  # camera space: +x right, +y up, -z forward
    ob.rotation_euler = (Vector((0, 0, -DIST)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
light('key', (-2.2, 2.0, -1.0), 420, 3.0, (1, 0.93, 0.85))
light('fill', (2.6, 0.4, -0.6), 160, 4.0, (0.9, 0.93, 1))
light('rim', (1.8, 1.6, -10.5), 520, 1.6, (1, 0.92, 0.82))
light('rim2', (-1.8, 1.0, -10.0), 260, 1.6)

# override materials for depth / normal
def emit_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for nd in list(nt.nodes): nt.nodes.remove(nd)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(em.outputs[0], out.inputs[0])
    return m, nt, em
dm, dnt, dem = emit_mat('vw_depth')
cd = dnt.nodes.new('ShaderNodeCameraData'); mr = dnt.nodes.new('ShaderNodeMapRange')
mr.inputs['From Min'].default_value = DIST - 0.45; mr.inputs['From Max'].default_value = DIST + 0.45
mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0; mr.clamp = True
dnt.links.new(cd.outputs['View Z Depth'], mr.inputs['Value']); dnt.links.new(mr.outputs[0], dem.inputs['Color'])
nm, nnt, nem = emit_mat('vw_normal')
geo = nnt.nodes.new('ShaderNodeNewGeometry'); vt = nnt.nodes.new('ShaderNodeVectorTransform')
vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'CAMERA'
vm = nnt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
vm.inputs[1].default_value = (0.5, 0.5, -0.5); vm.inputs[2].default_value = (0.5, 0.5, 0.5)
nnt.links.new(geo.outputs['Normal'], vt.inputs[0]); nnt.links.new(vt.outputs[0], vm.inputs[0]); nnt.links.new(vm.outputs[0], nem.inputs['Color'])
vl = sc.view_layers[0]
# guide colours closer to her painted look: brighter red satin skirt
for m in bpy.data.materials:
    if m.name.startswith('satin_red') and m.use_nodes:
        b = m.node_tree.nodes.get('Principled BSDF')
        if b and not b.inputs['Base Color'].is_linked: b.inputs['Base Color'].default_value = (0.42, 0.012, 0.016, 1)

def set_engine(p):
    if OPT['engine'] == 'workbench' and p == 'color':
        sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
    else:
        sc.render.engine = 'BLENDER_EEVEE'
        try: sc.eevee.taa_render_samples = 32 if p == 'color' else 1
        except Exception: pass
    if p == 'color':
        vl.material_override = None; sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'; sc.view_settings.exposure = -0.1
    else:
        vl.material_override = dm if p == 'depth' else nm; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0

# face landmarks in head-bone space (from the rest mesh)
body = bpy.data.objects['Vela.body']; eyes = bpy.data.objects['Vela.high-poly']
hb = arm.data.bones['head']; HB = hb.matrix_local
ev = [eyes.matrix_world @ v.co for v in eyes.data.vertices]
eL = sum((p for p in ev if p.x > 0), Vector()) / max(1, sum(1 for p in ev if p.x > 0))
eR = sum((p for p in ev if p.x < 0), Vector()) / max(1, sum(1 for p in ev if p.x < 0))
ez = (eL.z + eR.z) / 2
bv = [body.matrix_world @ v.co for v in body.data.vertices]
nose = min((p for p in bv if abs(p.x) < 0.006 and ez - 0.055 < p.z < ez - 0.015), key=lambda p: p.y)
band = [p for p in bv if ez - 0.05 < p.z < ez + 0.0 and eL.y + 0.04 < p.y < eL.y + 0.14]
earL = max(band, key=lambda p: p.x); earR = min(band, key=lambda p: p.x)
hc = (earL + earR) / 2
LM = {k: HB.inverted() @ v for k, v in dict(nose=nose, eR=eR, eL=eL, earR=earR, earL=earL, hc=hc).items()}
print('VWR landmarks', {k: [round(x, 3) for x in v] for k, v in dict(nose=nose, eL=eL, earL=earL).items()}, flush=True)

def keypoints(view_dir):
    pbs = arm.pose.bones; mw = arm.matrix_world
    J = lambda n: mw @ pbs[n].head
    Hm = mw @ pbs['head'].matrix
    F = {k: Hm @ v for k, v in LM.items()}
    tocam = -view_dir
    def vis(k, thr):
        d = (F[k] - F['hc']).normalized(); return d.dot(tocam) > thr
    pts = [F['nose'] if vis('nose', -0.1) else None, (J('upperarm_r') + J('upperarm_l')) / 2,
           J('upperarm_r'), J('lowerarm_r'), J('hand_r'), J('upperarm_l'), J('lowerarm_l'), J('hand_l'),
           J('thigh_r'), J('calf_r'), J('foot_r'), J('thigh_l'), J('calf_l'), J('foot_l'),
           F['eR'] if vis('eR', 0.05) else None, F['eL'] if vis('eL', 0.05) else None,
           F['earR'] if vis('earR', -0.35) else None, F['earL'] if vis('earL', -0.35) else None]
    out = []
    for p in pts:
        if p is None: out.append(None); continue
        c = world_to_camera_view(sc, co, p); out.append([round(c.x * W, 1), round((1 - c.y) * H, 1)])
    return out

def aim(center, az_deg, base_yaw=0.0):
    t = Matrix.Rotation(math.radians(az_deg) + base_yaw, 3, 'Z') @ Vector((0, -1, 0))
    co.location = Vector((center[0], center[1], CZ)) + t * DIST
    co.rotation_euler = (-t).to_track_quat('-Z', 'Y').to_euler()
    return -t

def use(name):
    a = bpy.data.actions[name]; arm.animation_data.action = a
    if arm.animation_data.action_slot is None and len(a.slots): arm.animation_data.action_slot = a.slots[0]

def render_set(setname, entries, angles):
    use('vw_sim')
    sel = [int(x) for x in OPT['frames'].split(',')] if OPT['frames'] else list(range(len(entries)))
    for az in angles:
        d = os.path.join(OUTDIR, setname, 'a%03d' % az); os.makedirs(d, exist_ok=True)
        kpf = os.path.join(d, 'kp.json'); kp = json.load(open(kpf)) if os.path.exists(kpf) else {}
        for p in PASSES:
            set_engine(p)
            for i in sel:
                if i >= len(entries): continue
                if OPT.get('skip') and os.path.exists(os.path.join(d, '%s_%02d.png' % (p, i))) and ('%02d' % i in kp or p != PASSES[0]): continue
                fr, cx, cy, yaw = entries[i]
                sc.frame_set(fr); vd = aim((cx, cy), az, yaw); bpy.context.view_layer.update()
                if p == PASSES[0]: kp['%02d' % i] = keypoints(vd)
                sc.render.filepath = os.path.join(d, '%s_%02d.png' % (p, i)); bpy.ops.render.render(write_still=True)
        json.dump(kp, open(kpf, 'w'))
        print('VWR', setname, az, 'done', flush=True)

ANG = [int(a) for a in OPT['angles'].split(',')]
S = VW['sets']
for s in SETS:
    render_set(s, S[s], ANG if s in ('walk', 'pose') or (s == 'stop' and OPT.get('stopall')) else [0])
print('VWR all done', flush=True)
