// NEON RAIN cast: rigged, animated 3D people (alley thugs, Gale's men, the artificial man, Miles Corran).
// Extends NR.gltf with a parse-once / instance-many loader for the skinned family GLBs (shared skeleton, shared
// geometry, materials and clips; one Skeleton + AnimationMixer per instance), and NR.cast.Rig: two animation layers
// (lower body / upper body) with crossfades, one-shot full-body clips, additive recoil and hit reactions, aim pitch, LOD.
(function () {
  const T = THREE;
  const TA = { 5126: Float32Array, 5125: Uint32Array, 5123: Uint16Array, 5121: Uint8Array, 5122: Int16Array, 5120: Int8Array };
  const NC = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
  const clean = (n) => T.PropertyBinding.sanitizeNodeName(n || '');
  const LOWER = new Set(['spine', 'thigh_L', 'shin_L', 'foot_L', 'toe_L', 'thigh_R', 'shin_R', 'foot_R', 'toe_R']);

  // noir character shading: a faint amber rim keeps silhouettes off the black, and deep reds (ties, blood) keep colour
  // through the B&W grade (alpha < 1 marks them for the post pass, as on Vela)
  function charMaterial(m) {
    m.side = T.DoubleSide; m.shadowSide = T.BackSide; // cloth shells are open (hems, cuffs, coat skirts): show their insides too; back faces cast (no acne)
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uRim = { value: new T.Color(0xffa24a).multiplyScalar(0.16) };
      sh.fragmentShader = 'uniform vec3 uRim;\n' + sh.fragmentShader.replace('#include <opaque_fragment>',
        'outgoingLight += uRim * pow(1.0 - clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), 3.0);\n#include <opaque_fragment>\n' +
        ' float rq = diffuseColor.r / max(0.004, max(diffuseColor.g, diffuseColor.b)); gl_FragColor.a = 1.0 - smoothstep(4.0, 7.0, rq) * smoothstep(0.02, 0.05, diffuseColor.r) * 0.95;');
    };
    m.customProgramCacheKey = () => 'nrCast'; m.needsUpdate = true;
  }

  async function template(url) {
    const buf = await (await fetch(url)).arrayBuffer();
    const dv = new DataView(buf); let off = 12, json = null, bin = null;
    while (off < buf.byteLength) { const len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true); const chunk = buf.slice(off + 8, off + 8 + len); if (type === 0x4E4F534A) json = JSON.parse(new TextDecoder().decode(chunk)); else bin = chunk; off += 8 + len; }
    const arr = (i) => { const a = json.accessors[i], bv = json.bufferViews[a.bufferView], C = TA[a.componentType], n = NC[a.type]; const start = (bv.byteOffset || 0) + (a.byteOffset || 0); return { array: new C(bin.slice(start, start + a.count * n * C.BYTES_PER_ELEMENT)), n, norm: !!a.normalized }; };
    const attr = (i) => { const r = arr(i); return new T.BufferAttribute(r.array, r.n, r.norm); };
    const images = await Promise.all((json.images || []).map(async (im) => { const bv = json.bufferViews[im.bufferView]; return createImageBitmap(new Blob([bin.slice(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength)], { type: im.mimeType }), { imageOrientation: 'none' }); }));
    const texCache = {};
    const tex = (info, srgb) => { if (!info) return null; const src = json.textures[info.index].source, k = src + (srgb ? 's' : 'l'); if (!texCache[k]) { const t = new T.Texture(images[src]); t.flipY = false; t.colorSpace = srgb ? T.SRGBColorSpace : T.NoColorSpace; t.anisotropy = 4; t.needsUpdate = true; texCache[k] = t; } return texCache[k]; };
    const mats = (json.materials || []).map(md => {
      const pb = md.pbrMetallicRoughness || {}, f = pb.baseColorFactor || [1, 1, 1, 1];
      const m = new T.MeshStandardMaterial({ name: md.name, color: new T.Color().setRGB(f[0], f[1], f[2], T.LinearSRGBColorSpace),
        metalness: pb.metallicFactor == null ? 1 : pb.metallicFactor, roughness: pb.roughnessFactor == null ? 1 : pb.roughnessFactor, map: tex(pb.baseColorTexture, true) });
      if (pb.metallicRoughnessTexture) { m.roughnessMap = m.metalnessMap = tex(pb.metallicRoughnessTexture, false); }
      if (md.normalTexture) { m.normalMap = tex(md.normalTexture, false); const s = md.normalTexture.scale || 1; m.normalScale.set(s, -s); }
      charMaterial(m);
      return m;
    });
    const geos = {};
    const geo = (mi, pi) => {
      const k = mi + ':' + pi; if (geos[k]) return geos[k];
      const p = json.meshes[mi].primitives[pi], g = new T.BufferGeometry(), A = p.attributes;
      g.setAttribute('position', attr(A.POSITION)); if (A.NORMAL !== undefined) g.setAttribute('normal', attr(A.NORMAL)); if (A.TEXCOORD_0 !== undefined) g.setAttribute('uv', attr(A.TEXCOORD_0));
      if (A.JOINTS_0 !== undefined) g.setAttribute('skinIndex', attr(A.JOINTS_0)); if (A.WEIGHTS_0 !== undefined) g.setAttribute('skinWeight', attr(A.WEIGHTS_0));
      if (p.indices !== undefined) g.setIndex(attr(p.indices));
      if (A.NORMAL === undefined) g.computeVertexNormals();
      g.computeBoundingSphere();
      return (geos[k] = { g, mat: p.material });
    };
    const names = json.nodes.map(n => clean(n.name));
    const joints = new Set(); (json.skins || []).forEach(s => s.joints.forEach(j => joints.add(j)));
    const inv = (json.skins || []).map(s => { const ib = arr(s.inverseBindMatrices).array; return s.joints.map((_, k) => new T.Matrix4().fromArray(ib, k * 16)); });
    const clips = {};
    for (const a of json.animations || []) {
      const tracks = [];
      for (const ch of a.channels) {
        const s = a.samplers[ch.sampler], path = { translation: 'position', rotation: 'quaternion', scale: 'scale' }[ch.target.path];
        if (!path || s.interpolation === 'CUBICSPLINE') continue;
        const TT = path === 'quaternion' ? T.QuaternionKeyframeTrack : T.VectorKeyframeTrack;
        tracks.push(new TT(names[ch.target.node] + '.' + path, Array.from(arr(s.input).array), Array.from(arr(s.output).array)));
      }
      clips[a.name] = new T.AnimationClip(a.name, -1, tracks);
    }
    const rigNode = json.nodes.find(n => n.extras && n.extras.nr_anims);
    const meta = rigNode ? { anims: JSON.parse(rigNode.extras.nr_anims), cast: JSON.parse(rigNode.extras.nr_cast) } : { anims: {}, cast: {} };
    // layer splits and additive versions, made once per family
    const sub = {};
    for (const [n, c] of Object.entries(clips)) {
      const bone = (tr) => tr.name.split('.')[0];
      const ex = meta.anims[n] || {};
      if (ex.additive) { const add = T.AnimationUtils.makeClipAdditive(c.clone()); add.tracks = add.tracks.filter(tr => tr.name.indexOf('.position') < 0); sub[n] = { A: add }; continue; }
      if (/^die_/.test(n)) { // keep half of the slide in the falls so bodies stay near where they dropped
        const tr = c.tracks.find(t => t.name === 'spine.position');
        if (tr) { const v = tr.values, x0 = v[0], z0 = v[2]; for (let i = 0; i < v.length; i += 3) { v[i] = x0 + (v[i] - x0) * 0.55; v[i + 2] = z0 + (v[i + 2] - z0) * 0.55; } }
      }
      sub[n] = { L: new T.AnimationClip(n + '_L', c.duration, c.tracks.filter(t => LOWER.has(bone(t)))),
                 U: new T.AnimationClip(n + '_U', c.duration, c.tracks.filter(t => !LOWER.has(bone(t)))) };
    }
    return { json, names, joints, inv, mats, geo, clips, sub, meta };
  }

  function instance(tpl, keep) {
    const { json, names } = tpl;
    const nodes = json.nodes.map((n, i) => { const o = tpl.joints.has(i) ? new T.Bone() : new T.Group(); o.name = names[i]; if (n.matrix) new T.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale); if (n.translation) o.position.fromArray(n.translation); if (n.rotation) o.quaternion.fromArray(n.rotation); if (n.scale) o.scale.fromArray(n.scale); return o; });
    json.nodes.forEach((n, i) => { for (const c of n.children || []) if (keep(names[c])) nodes[i].add(nodes[c]); });
    const byName = {}; nodes.forEach(o => { byName[o.name] = o; });
    const skinned = [];
    json.nodes.forEach((n, i) => {
      if (n.mesh === undefined || !keep(names[i])) return;
      json.meshes[n.mesh].primitives.forEach((p, pi) => {
        const { g, mat } = tpl.geo(n.mesh, pi), material = tpl.mats[mat] || new T.MeshStandardMaterial();
        const m = n.skin !== undefined && g.attributes.skinIndex ? new T.SkinnedMesh(g, material) : new T.Mesh(g, material);
        m.name = names[i] + '_mesh'; m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false; nodes[i].add(m);
        if (m.isSkinnedMesh) skinned.push([m, n.skin]);
      });
    });
    const root = new T.Group(); for (const i of json.scenes[json.scene || 0].nodes) if (keep(names[i])) root.add(nodes[i]);
    root.updateMatrixWorld(true);
    const skels = {};
    for (const [m, si] of skinned) {
      if (!skels[si]) skels[si] = new T.Skeleton(json.skins[si].joints.map(j => nodes[j]), tpl.inv[si]);
      m.bind(skels[si], new T.Matrix4());
    }
    return { root, nodes: byName };
  }

  const tplCache = {};
  function family(url) { if (!tplCache[url]) { tplCache[url] = template(url); tplCache[url].then(t => { tplCache[url].done = t; }, e => { console.warn('[cast] ' + url + ' failed', e); }); } return tplCache[url]; }

  const URL = { thugs: 'models/cast/thugs.glb', gale: 'models/cast/gale.glb', synth: 'models/cast/synth.glb', miles: 'models/cast/miles.glb' };
  const FAMILY = { thug_a: 'thugs', thug_b: 'thugs', thug_c: 'thugs', gale_a: 'gale', gale_b: 'gale', gale_c: 'gale', synth: 'synth', miles: 'miles' };
  const VARIANTS = Object.keys(FAMILY);
  function preload(fams) { for (const f of fams || Object.keys(URL)) family(NR.ASSET + URL[f]); }
  function ready(variant) { const p = tplCache[NR.ASSET + URL[FAMILY[variant]]]; return p && p.done ? p.done : null; }

  const WEAPONS = ['pistol', 'tommy', 'knife', 'flashlight'];
  class Rig {
    constructor(tpl, variant) {
      this.variant = variant; this.tpl = tpl;
      const own = (n) => VARIANTS.some(v => n === v || n.startsWith(v + '_'));
      const inst = instance(tpl, n => !own(n) || n === variant || n.startsWith(variant + '_'));
      this.root = inst.root; this.nodes = inst.nodes;
      this.lod0 = this.nodes[variant]; this.lod1 = this.nodes[variant + '_lod1']; if (this.lod1) this.lod1.visible = false;
      this.weapons = WEAPONS.filter(w => this.nodes[variant + '_' + w]);
      const main = this.weapons.find(w => w !== 'flashlight') || null;
      this.kind = main === 'knife' ? (this.weapons.includes('flashlight') ? 'knife_lamp' : 'knife') : main || 'none';
      this.muzzle = main ? this.nodes[variant + '_' + main + '_muzzle'] : null;
      this.lampTip = this.nodes[variant + '_flashlight_muzzle'] || null;
      this.hat = this.nodes[variant + '_hat'] || null;
      const B = (n) => this.nodes[n];
      this.bones = { hips: B('spine'), spine2: B('spine_002'), chest: B('spine_003'), head: B('spine_006'), handR: B('hand_R'), handL: B('hand_L'), thighL: B('thigh_L'), thighR: B('thigh_R') };
      this.mixer = new T.AnimationMixer(this.root);
      this.acts = {}; this.layer = { L: null, U: null }; this.layerName = { L: '', U: '' };
      this.speedOf = (n) => ((tpl.meta.anims[n] || {}).speed) || 1;
      this.play('L', 'idle', 0); this.play('U', 'idle', 0);
      this.mixer.update(Math.random() * 3);
    }
    has(n) { return !!this.tpl.sub[n]; }
    action(n, part) {
      const k = n + '|' + part; if (this.acts[k]) return this.acts[k];
      const s = this.tpl.sub[n]; if (!s || !s[part]) return null;
      const a = this.mixer.clipAction(s[part]);
      if (part === 'A') a.blendMode = T.AdditiveAnimationBlendMode;
      return (this.acts[k] = a);
    }
    play(part, n, fade = 0.25, once = false, timeScale = 1) {
      if (this.layerName[part] === n && !once) { if (this.layer[part]) this.layer[part].timeScale = timeScale; return; }
      const a = this.action(n, part); if (!a) return;
      a.reset(); a.enabled = true; a.setEffectiveTimeScale(timeScale); a.setEffectiveWeight(1);
      if (once) { a.setLoop(T.LoopOnce, 1); a.clampWhenFinished = true; } else a.setLoop(T.LoopRepeat, Infinity);
      if (this.layer[part] && this.layer[part] !== a && fade > 0) { a.crossFadeFrom(this.layer[part], fade, false); } else if (this.layer[part] && this.layer[part] !== a) this.layer[part].stop();
      a.play(); this.layer[part] = a; this.layerName[part] = n;
    }
    full(n, fade = 0.15, once = true, timeScale = 1) { this.play('L', n, fade, once, timeScale); this.play('U', n, fade, once, timeScale); }
    additive(n, weight = 1) { const a = this.action(n, 'A'); if (!a) return; a.reset(); a.setLoop(T.LoopOnce, 1); a.clampWhenFinished = false; a.setEffectiveWeight(weight); a.play(); }
    // rotate a bone in world space after the mixer (aim pitch)
    bend(bone, axis, ang) {
      if (!bone || !ang) return;
      const pw = new T.Quaternion(), bw = new T.Quaternion();
      bone.parent.getWorldQuaternion(pw); bone.getWorldQuaternion(bw);
      const q = new T.Quaternion().setFromAxisAngle(axis, ang).multiply(bw);
      bone.quaternion.copy(pw.invert().multiply(q)); bone.updateMatrixWorld(true);
    }
    lod(far) { if (!this.lod1) return; this.lod0.visible = !far; this.lod1.visible = far; }
    update(dt) { this.mixer.update(dt); this.root.updateMatrixWorld(true); }
  }

  NR.gltf = NR.gltf || {}; NR.gltf.template = template; NR.gltf.instance = instance;
  NR.cast = { Rig, family, preload, ready, URL, FAMILY, LOWER };
})();
