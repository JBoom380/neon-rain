"""NEON RAIN environment pass: shared Blender helpers (run inside Blender 5.2, headless).
Game coordinates (three.js: x right, y up, z toward the camera) are used everywhere in the level scripts; G() maps them
to Blender (z up). The glTF exporter maps Blender back to y-up, so positions round-trip unchanged.

Pipeline per level: build the static set (SHELL = tiled PBR surfaces, PROPS = Poly Haven models + modelled props),
light it with practical lights only (sodium, incandescent, neon), then
  * PROPS (and each DYNAMIC object): Cycles COMBINED bake into a unique-UV atlas (albedo x light): unlit on the phone.
  * SHELL: Cycles DIFFUSE (direct + indirect, no colour) bake into a lightmap on UV2; the phone multiplies the tiled
    albedo by it.
Export: one GLB. SHELL materials carry baseColor (UV0) + emissiveTexture (UV1 lightmap) and extras.lm = scale;
PROPS / DYNAMIC materials carry baseColor (baked) and extras.baked = scale; NEON_* materials are emissive tubes.
"""
import bpy, bmesh, math, pathlib, os, sys, time
import numpy as np
from mathutils import Vector, Matrix, Euler

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "art" / "env_src"
TEX = SRC / "tex"
WORK = SRC / "work"
WORK.mkdir(parents=True, exist_ok=True)


def G(x, y, z):
    return Vector((x, -z, y))


# ---------------------------------------------------------------- scene
def reset(samples=256):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev_type in ('CUDA', 'OPTIX'):
            try:
                prefs.compute_device_type = dev_type
                prefs.get_devices()
                if any(d.type == dev_type for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == dev_type
                    sc.cycles.device = 'GPU'
                    print('[env] cycles device', dev_type)
                    break
            except Exception as e:
                print('[env] device', dev_type, e)
    except Exception as e:
        print('[env] no GPU prefs', e)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 2
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 1.5
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('World'); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1)
    bg.inputs[1].default_value = 0.0
    return sc


def world_color(rgb, strength=1.0):
    bg = bpy.context.scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength


def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def apply_xform(o):
    select_only([o])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tris(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)


# ---------------------------------------------------------------- colour
def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    return tuple(srgb2lin(((h >> s) & 255) / 255) for s in (16, 8, 0))


def kelvin(k):
    """Blackbody colour (Tanner Helland fit), normalised to max 1."""
    t = k / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = [max(0, min(255, v)) / 255 for v in (r, g, b)]  # display-referred: a camera white-balanced part way toward tungsten (amber, not red)
    m = max(c)
    return tuple(v / m for v in c)


SODIUM = (1.0, 0.46, 0.12)  # sodium street light, deep orange-amber
SODIUM_HP = (1.0, 0.6, 0.27)  # high-pressure sodium glow, amber
INCAND = kelvin(2700)
NEON_RED = (1.0, 0.045, 0.02)
NEON_ORANGE = (1.0, 0.28, 0.03)
NEON_TEAL = (0.02, 0.85, 0.65)
NEON_GREEN = (0.15, 1.0, 0.2)
NEON_BLUE = (0.05, 0.35, 1.0)


# ---------------------------------------------------------------- materials
def _img(path, colorspace='sRGB'):
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def pbr(name, tex_id, tint=(1, 1, 1), rough=None, metal=0.0, normal=0.6):
    """Principled material from a Poly Haven texture set (UV0, UVs are already scaled to metres/tile)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
    d = TEX / f"{tex_id}_diff_1k.jpg"
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = _img(d)
    if tint != (1, 1, 1):
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1.0
        nt.links.new(t.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    else:
        nt.links.new(t.outputs[0], bsdf.inputs['Base Color'])
    r = TEX / f"{tex_id}_rough_1k.jpg"
    if rough is None and r.exists():
        tr = nt.nodes.new('ShaderNodeTexImage'); tr.image = _img(r, 'Non-Color'); nt.links.new(tr.outputs[0], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = 0.6 if rough is None else rough
    n = TEX / f"{tex_id}_nor_gl_1k.jpg"
    if normal and n.exists():
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = _img(n, 'Non-Color')
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal
        nt.links.new(tn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Metallic'].default_value = metal
    m['tex_id'] = tex_id; m['tint'] = list(tint)
    return m


def flat(name, rgb, rough=0.5, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    return m


def imgmat(name, path, rough=0.5, emit_strength=0.0, alpha=False):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = _img(path)
    nt.links.new(t.outputs[0], b.inputs['Base Color'])
    if emit_strength:
        nt.links.new(t.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit_strength
    if alpha:
        nt.links.new(t.outputs[1], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = rough
    return m


# ---------------------------------------------------------------- geometry
def mesh_obj(name, bm, mat=None):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); link(o)
    if mat:
        me.materials.append(mat)
    return o


def box_uv(o, tile=1.0, rot90=False):
    """World-space box projection, 1 UV unit = `tile` metres (Blender units)."""
    me = o.data; mw = o.matrix_world
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    uv = me.uv_layers[0].data
    nmat = mw.to_3x3().inverted().transposed()
    for p in me.polygons:
        n = (nmat @ p.normal).normalized(); ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            v = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 2:
                u, w = v.x, v.y
            elif ax == 0:
                u, w = v.y * (1 if n.x > 0 else -1), v.z
            else:
                u, w = v.x * (-1 if n.y > 0 else 1), v.z
            if rot90:
                u, w = w, u
            uv[li].uv = (u / tile, w / tile)


GDIR = {'+x': Vector((1, 0, 0)), '-x': Vector((-1, 0, 0)), '+y': Vector((0, 0, 1)), '-y': Vector((0, 0, -1)), '+z': Vector((0, -1, 0)), '-z': Vector((0, 1, 0))}


def box(name, gmin, gmax, mat=None, tile=1.0, bevel=0.0, rot90=False, faces=None):
    """Axis-aligned box from game-space min/max corners. faces: keep only these game-space sides ('+x', '-z', ...)."""
    a, b = G(*gmin), G(*gmax)
    lo = Vector(map(min, a, b)); hi = Vector(map(max, a, b))
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((lo.x + (v.co.x + 0.5) * (hi.x - lo.x), lo.y + (v.co.y + 0.5) * (hi.y - lo.y), lo.z + (v.co.z + 0.5) * (hi.z - lo.z)))
    if faces:
        keep = [GDIR[f] for f in faces]
        bm.normal_update()
        dead = [f for f in bm.faces if not any(f.normal.dot(k) > 0.9 for k in keep)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    elif bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=0.5)
    o = mesh_obj(name, bm, mat)
    box_uv(o, tile, rot90)
    return o


def box_rot(name, gcenter, gsize, rx_deg=0.0, ry_deg=0.0, mat=None, tile=1.0, bevel=0.0):
    """Box of game size (sx, sy, sz) rotated about game X then game Y, centred at gcenter."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = gsize
    bmesh.ops.scale(bm, vec=(sx, sz, sy), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect='EDGES', profile=0.5)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rx_deg), 3, 'X'))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(ry_deg), 3, 'Z'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=G(*gcenter))
    o = mesh_obj(name, bm, mat); box_uv(o, tile); return o


def fit_uv(o, axis_game='z'):
    """Planar 0..1 UV over the object's bounding box, seen along the game axis (for decals like the door glass)."""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    lo, hi = bbox(o)
    for p in me.polygons:
        for li in p.loop_indices:
            v = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            if axis_game == 'z':
                u = (v.x - lo.x) / max(1e-6, hi.x - lo.x); w = (v.z - lo.z) / max(1e-6, hi.z - lo.z)
            else:
                u = (v.y - lo.y) / max(1e-6, hi.y - lo.y); w = (v.z - lo.z) / max(1e-6, hi.z - lo.z)
            me.uv_layers[0].data[li].uv = (u, w)


def set_origin(o, gpos):
    sc = bpy.context.scene; sc.cursor.location = G(*gpos)
    select_only([o]); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def cyl(name, gpos, r, h, mat=None, seg=16, r2=None, axis='Y', tile=0.5, cap=True):
    """Cylinder/cone standing on gpos (game coords), along game axis (Y = up)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    if axis == 'X':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif axis == 'Z':
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=G(*gpos))
    o = mesh_obj(name, bm, mat); box_uv(o, tile); return o


def lathe(name, profile, gpos, mat=None, seg=24, tile=0.3, smooth=True):
    """Revolve [(radius, height), ...] around the vertical axis at gpos (game coords)."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), h)))
        rings.append(ring)
    for k in range(len(rings) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            try:
                bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
            except ValueError:
                pass
    if profile[0][0] > 1e-4:
        bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 1e-4:
        bm.faces.new(rings[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.translate(bm, verts=bm.verts, vec=G(*gpos))
    o = mesh_obj(name, bm, mat)
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    box_uv(o, tile)
    return o


def tube_path(name, gpts, r, mat=None, seg=8):
    """A pipe through game-space points."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = max(1, seg // 4)
    sp = cu.splines.new('POLY'); sp.points.add(len(gpts) - 1)
    for i, p in enumerate(gpts):
        sp.points[i].co = (*G(*p), 1)
    o = bpy.data.objects.new(name, cu); link(o)
    if mat:
        cu.materials.append(mat)
    select_only([o]); bpy.ops.object.convert(target='MESH')
    o = bpy.context.view_layer.objects.active
    box_uv(o, 0.3)
    return o


def neon_text(name, text, gpos, ry_deg, size, mat, depth=0.007, font=None, align='CENTER', backing=None, res=4):
    """Glass-tube neon lettering: the outline of each glyph becomes a round tube (two-line neon, like 1940s signage).
    gpos = centre of the text in game coords; ry_deg = rotation about game Y (0 = faces +Z)."""
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = text; cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'
    if font:
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    o = bpy.data.objects.new(name, cu); link(o)
    select_only([o]); bpy.ops.object.convert(target='CURVE')
    o = bpy.context.view_layer.objects.active
    o.data.dimensions = '3D'; o.data.fill_mode = 'FULL'; o.data.bevel_depth = depth; o.data.bevel_resolution = 1; o.data.extrude = 0
    o.data.resolution_u = res
    o.data.materials.clear(); o.data.materials.append(mat)
    o.rotation_euler = Euler((math.pi / 2, 0, math.radians(ry_deg)))
    o.location = G(*gpos)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.view_layer.objects.active
    apply_xform(o)
    return o


# ---------------------------------------------------------------- Poly Haven import
def ph(asset, gpos, ry_deg=0.0, scale=1.0, target=None, keep=None, drop=(), name=None, exact=None):
    """Import a Poly Haven glTF, join its meshes, decimate to `target` triangles, place at game coords
    (ry_deg = rotation about the up axis; 0 keeps the model's own front, which faces Blender -Y = game +Z)."""
    f = next((SRC / "models" / asset).glob("*.gltf"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(f))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH' and (keep is None or any(k in o.name for k in keep)) and not any(d in o.name for d in drop) and (exact is None or o.name.split('.')[0] in exact)]
    bpy.context.view_layer.update()
    mws = {o.name: o.matrix_world.copy() for o in meshes}
    for o in meshes:
        o.parent = None; o.matrix_world = mws[o.name]
    for o in new:
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    select_only(meshes)
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name or asset
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for uv in list(o.data.uv_layers)[1:]:
        o.data.uv_layers.remove(uv)
    if o.data.uv_layers:
        o.data.uv_layers[0].name = 'UVMap'
    if target and tris(o) > target:
        dm = o.modifiers.new('dec', 'DECIMATE'); dm.ratio = target / tris(o); dm.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    o.scale = (scale, scale, scale)
    o.rotation_euler = (0, 0, math.radians(ry_deg))
    o.location = G(*gpos)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def dup(o, gpos, ry_deg=0.0, name=None):
    n = o.copy(); n.data = o.data.copy(); link(n); n.name = name or (o.name + '_dup')
    c = sum((Vector(v) for v in o.bound_box), Vector()) / 8
    n.matrix_world = Matrix.Translation(G(*gpos)) @ Matrix.Rotation(math.radians(ry_deg), 4, 'Z') @ Matrix.Translation(-Vector((c.x, c.y, 0))) @ o.matrix_world
    apply_xform(n)
    return n


def place_bottom(o, gx, gy, gz, side=None):
    """Move o so its bbox bottom-centre sits at game (gx, gy, gz); side='+x'/'-x' puts its back flush on a wall at gx."""
    lo, hi = bbox(o)
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    t = Vector((gx - cx, -gz - cy, gy - lo.z))
    if side == '+x':
        t.x = gx - lo.x
    elif side == '-x':
        t.x = gx - hi.x
    o.location += t; apply_xform(o)
    return o


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector(map(min, *pts)); hi = Vector(map(max, *pts))
    return lo, hi


def game_bbox(o):
    lo, hi = bbox(o)
    return (round(lo.x, 3), round(lo.z, 3), round(-hi.y, 3)), (round(hi.x, 3), round(hi.z, 3), round(-lo.y, 3))


# ---------------------------------------------------------------- lights
def light(kind, gpos, color, energy, radius=0.05, gaim=None, spot_deg=60, blend=0.2, size=(1, 1), name='L'):
    ld = bpy.data.lights.new(name, kind); ld.color = color; ld.energy = energy
    if kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = radius
    if kind == 'SPOT':
        ld.spot_size = math.radians(spot_deg); ld.spot_blend = blend
    if kind == 'AREA':
        ld.shape = 'RECTANGLE'; ld.size, ld.size_y = size
    if kind == 'SUN':
        ld.angle = math.radians(radius)
    o = bpy.data.objects.new(name, ld); link(o)
    o.visible_camera = False
    o.location = G(*gpos)
    if gaim is not None:
        d = (G(*gaim) - o.location).normalized()
        o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o


# ---------------------------------------------------------------- join / UV / bake
def join(objs, name):
    objs = [o for o in objs if o and o.type == 'MESH']
    for o in objs:
        if not o.data.uv_layers:
            o.data.uv_layers.new(name='UVMap')
        while len(o.data.uv_layers) > 1:
            o.data.uv_layers.remove(o.data.uv_layers[-1])
        o.data.uv_layers[0].name = 'UVMap'
    select_only(objs)
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def unwrap(o, layer, method='smart', margin=0.004):
    me = o.data
    uv = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    me.uv_layers.active = uv
    for l in me.uv_layers:
        l.active_render = (l.name == 'UVMap')
    select_only([o]); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    if method == 'lightmap':
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT='ALL_FACES', PREF_PACK_IN_ONE=True, PREF_NEW_UVLAYER=False, PREF_BOX_DIV=48, PREF_MARGIN_DIV=0.25)
    else:
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        try:
            bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', rotate=True, margin_method='FRACTION', margin=margin, shape_method='CONCAVE')
        except Exception as e:
            print('[env] pack_islands', e)
            bpy.ops.uv.pack_islands(rotate=True, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    return uv


def _target_nodes(o, img, layer):
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.get('bake_target')]:
            nt.nodes.remove(n)
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t['bake_target'] = 1
        u = nt.nodes.new('ShaderNodeUVMap'); u.uv_map = layer; u['bake_target'] = 1
        nt.links.new(u.outputs[0], t.inputs[0])
        for n in nt.nodes:
            n.select = False
        t.select = True; nt.nodes.active = t


def bake(objs, imgs, layer, kind, samples=None, margin=8):
    """Bake `kind` ('COMBINED' or 'DIFFUSE' lighting-only) for objs into imgs[i] (float images) using UV layer `layer`."""
    sc = bpy.context.scene
    if samples:
        sc.cycles.samples = samples
    for o, img in zip(objs, imgs):
        o.data.uv_layers.active = o.data.uv_layers[layer]
        _target_nodes(o, img, layer)
    select_only(objs)
    t0 = time.time()
    if kind == 'DIFFUSE':
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=margin, use_clear=True, target='IMAGE_TEXTURES')
    else:
        bpy.ops.object.bake(type='COMBINED', pass_filter={'DIRECT', 'INDIRECT', 'DIFFUSE', 'EMIT', 'GLOSSY'}, margin=margin, use_clear=True, target='IMAGE_TEXTURES')
    print(f'[env] bake {kind} {[o.name for o in objs]} {time.time() - t0:.1f}s')


def new_float_image(name, w, h):
    im = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    im.colorspace_settings.name = 'Linear Rec.709' if 'Linear Rec.709' in [i.name for i in bpy.types.ColorManagedInputColorspaceSettings.bl_rna.properties['name'].enum_items] else 'Non-Color'
    return im


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def denoise(rgb, coverage=None, passes=1):
    """Light edge-preserving smooth for bake noise (3x3 cross bilateral on luminance); keeps the margin dilation."""
    out = rgb.copy()
    # fireflies: a texel much brighter than the median of its 3x3 neighbourhood takes the median
    stack = np.stack([np.roll(np.roll(out, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    med = np.median(stack, axis=0); del stack
    lum, mlum = out.mean(axis=2), med.mean(axis=2)
    ff = lum > mlum * 2.0 + 0.02
    out[ff] = med[ff]; del med
    for _ in range(passes):
        acc = out.copy(); wsum = np.ones(out.shape[:2], np.float32)
        lum = out.mean(axis=2)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sh = np.roll(np.roll(out, dy, 0), dx, 1); sl = np.roll(np.roll(lum, dy, 0), dx, 1)
            w = np.exp(-((sl - lum) ** 2) / (2 * (0.08 * (lum + 0.02)) ** 2)).astype(np.float32) * (0.7 if dx and dy else 1.0)
            acc += sh * w[..., None]; wsum += w
        out = acc / wsum[..., None]
    return out


def save_ldr(img, path, scale=None, pct=99.7, gamma=True, smooth=1, quality=90):
    """Float bake -> 8-bit sRGB file. Returns the multiplier the game applies to get linear light back."""
    a = pixels(img)[..., :3]
    if smooth:
        a = denoise(a, passes=smooth)
    if scale is None:
        lum = a.max(axis=2); v = np.percentile(lum[lum > 1e-5], pct) if (lum > 1e-5).any() else 1.0
        scale = 1.0 / max(v, 1e-4)
    b = np.clip(a * scale, 0, 1)
    if gamma:
        b = np.where(b <= 0.0031308, b * 12.92, 1.055 * np.power(b, 1 / 2.4) - 0.055)
    w, h = img.size
    out = bpy.data.images.new(pathlib.Path(path).stem, w, h, alpha=False)
    out.colorspace_settings.name = 'Non-Color'
    px = np.ones((h, w, 4), np.float32); px[..., :3] = b
    out.pixels.foreach_set(px.ravel())
    out.filepath_raw = str(path); out.file_format = 'JPEG' if str(path).endswith('.jpg') else 'PNG'
    sc = bpy.context.scene; sc.render.image_settings.quality = quality
    out.save()
    out.colorspace_settings.name = 'sRGB'
    out.reload()
    print(f'[env] saved {path} scale {1 / scale:.4f}')
    return 1.0 / scale, out


# ---------------------------------------------------------------- export materials
def export_mat_baked(name, img, layer, mult):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    u = nt.nodes.new('ShaderNodeUVMap'); u.uv_map = layer; nt.links.new(u.outputs[0], t.inputs[0])
    nt.links.new(t.outputs[0], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 1.0; b.inputs['Metallic'].default_value = 0.0
    m['baked'] = float(mult)
    return m


def export_mat_lightmapped(src, lm_img, mult):
    """Shell material for export: tiled albedo (UV0) as base colour, lightmap (UV 'lm') as the emissive texture."""
    m = bpy.data.materials.new('LM_' + src.name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex_id = src.get('tex_id')
    if tex_id:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = _img(TEX / f"{tex_id}_diff_1k.jpg")
        u0 = nt.nodes.new('ShaderNodeUVMap'); u0.uv_map = 'UVMap'; nt.links.new(u0.outputs[0], t.inputs[0])
        nt.links.new(t.outputs[0], b.inputs['Base Color'])
        tint = list(src.get('tint', [1, 1, 1]))
        m['tint'] = tint
    else:
        sb = src.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = sb.inputs['Base Color'].default_value
    l = nt.nodes.new('ShaderNodeTexImage'); l.image = lm_img
    u = nt.nodes.new('ShaderNodeUVMap'); u.uv_map = 'lm'; nt.links.new(u.outputs[0], l.inputs[0])
    nt.links.new(l.outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.0
    b.inputs['Roughness'].default_value = 1.0
    m['lm'] = float(mult)
    return m


def export_glb(objs, path):
    select_only(objs)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_apply=True,
                              export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='JPEG',
                              export_jpeg_quality=88, export_extras=True, export_yup=True, export_animations=False,
                              export_lights=False, export_cameras=False, export_draco_mesh_compression_enable=False,
                              export_tangents=False, export_attributes=False)
    print(f'[env] exported {path} {os.path.getsize(path) / 1e6:.2f} MB')


def strip_uv_except(o, keep):
    for l in list(o.data.uv_layers):
        if l.name not in keep:
            o.data.uv_layers.remove(l)


def single_material(o, mat):
    o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons:
        p.material_index = 0
