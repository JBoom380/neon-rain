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

  // noir character shading: a two-tone neon rim (teal from screen-right, red-magenta from screen-left) cuts the silhouettes
  // out of the dark without flattening the key light and shadows; deep reds (ties, blood) keep colour through the grade
  // (alpha < 1 marks them for the post pass, as on Vela)
  function charMaterial(m) {
    m.side = T.DoubleSide; m.shadowSide = T.BackSide; // cloth shells are open (hems, cuffs, coat skirts): show their insides too; back faces cast (no acne)
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uRimA = { value: new T.Color(0x38d6ff).multiplyScalar(0.26) };
      sh.uniforms.uRimB = { value: new T.Color(0xff2a5a).multiplyScalar(0.22) };
      // matte, never blown out: cap albedo luminance (white shirts and the ivory suit stay cloth under the work lights)
      sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', '#include <map_fragment>\n float lumA = dot(diffuseColor.rgb, vec3(0.2126, 0.7152, 0.0722)); diffuseColor.rgb *= min(1.0, 0.55 / max(lumA, 1e-4));\n#ifdef USE_ROUGHNESSMAP\n float skinM = 1.0 - smoothstep(0.02, 0.045, abs(texture2D(roughnessMap, vRoughnessMapUv).r - 0.45)); diffuseColor.rgb = mix(diffuseColor.rgb, vec3(dot(diffuseColor.rgb, vec3(0.3, 0.55, 0.15))) * vec3(1.02, 0.97, 0.95), 0.35 * skinM);\n#endif')
        .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\n#ifdef USE_ROUGHNESSMAP\n float specK = texture2D(roughnessMap, vRoughnessMapUv).r; reflectedLight.directSpecular *= specK; reflectedLight.indirectSpecular *= specK;\n float skinK = 1.0 - smoothstep(0.02, 0.045, abs(specK - 0.45));\n reflectedLight.directSpecular *= 1.0 - 0.75 * skinK;\n reflectedLight.directDiffuse = mix(reflectedLight.directDiffuse, reflectedLight.directDiffuse * vec3(1.06, 0.94, 0.9), skinK);\n reflectedLight.indirectDiffuse += diffuseColor.rgb * vec3(0.30, 0.07, 0.05) * skinK * 0.6;\n#endif');
      sh.fragmentShader = 'uniform vec3 uRimA, uRimB;\n' + sh.fragmentShader.replace('#include <opaque_fragment>',
        'float nv = 1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0); float rimk = nv * nv * nv;\n' +
        'outgoingLight += mix(uRimB, uRimA, smoothstep(-0.35, 0.35, normal.x)) * rimk * (1.0 - 0.85 * smoothstep(0.25, 0.85, normal.y));\n' +
        'float pk = max(max(outgoingLight.r, outgoingLight.g), outgoingLight.b); float pkk = pk < 0.3 ? pk : 0.3 + (pk - 0.3) / (1.0 + (pk - 0.3) / 0.5); outgoingLight *= pkk / max(pk, 1e-4);\n#include <opaque_fragment>\n' + // soft shoulder: hot work lights never blow skin and cloth out
        ' float rq = diffuseColor.r / max(0.004, max(diffuseColor.g, diffuseColor.b)); gl_FragColor.a = 1.0 - smoothstep(4.0, 7.0, rq) * smoothstep(0.02, 0.05, diffuseColor.r) * 0.95;');
    };
    m.customProgramCacheKey = () => 'nrCast6'; m.needsUpdate = true;
  }

  // alpha hair cards: alpha-tested strands tinted per character, with a Kajiya-style anisotropic highlight running across
  // the strands (strand direction from screen-space derivatives of the card UVs)
  function hairCards(m, tint) {
    m.alphaTest = 0.4; m.transparent = false; m.depthWrite = true; m.side = T.DoubleSide; m.metalness = 0; m.roughness = 0.5;
    m.color.setRGB(Math.min(1, tint[0] * 1.6), Math.min(1, tint[1] * 1.6), Math.min(1, tint[2] * 1.6), T.LinearSRGBColorSpace);
    m.onBeforeCompile = (sh) => {
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `
        vec3 dp1 = dFdx(-vViewPosition), dp2 = dFdy(-vViewPosition); vec2 du1 = dFdx(vMapUv), du2 = dFdy(vMapUv);
        vec3 Ts = normalize(dp1 * du2.y - dp2 * du1.y + 1e-6);
        vec3 Vv = normalize(vViewPosition); vec3 Lk = normalize(vec3(-0.35, 0.75, 0.55));
        vec3 Hh = normalize(Lk + Vv); float th = dot(Ts, Hh); float aniso = pow(sqrt(max(0.0, 1.0 - th * th)), 70.0);
        float th2 = dot(Ts, normalize(vec3(0.5, 0.3, 0.6) + Vv)); float aniso2 = pow(sqrt(max(0.0, 1.0 - th2 * th2)), 24.0);
        outgoingLight += diffuseColor.rgb * (aniso * 0.22 + aniso2 * 0.08);
        #include <opaque_fragment>`);
    };
    m.customProgramCacheKey = () => 'nrHair'; m.needsUpdate = true;
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
      // PBR with a baked specular-intensity map (R of the roughness/metal texture): cloth stays matte, skin, satin,
      // leather and gun metal catch the light
      const m = new T.MeshStandardMaterial({ name: md.name, color: new T.Color().setRGB(f[0], f[1], f[2], T.LinearSRGBColorSpace), map: tex(pb.baseColorTexture, true),
        roughness: pb.roughnessFactor == null ? 1 : pb.roughnessFactor, metalness: pb.metallicFactor == null ? 1 : pb.metallicFactor });
      if (pb.metallicRoughnessTexture) { m.roughnessMap = m.metalnessMap = tex(pb.metallicRoughnessTexture, false); }
      if (md.extras && md.extras.cards) { hairCards(m, md.extras.tint || [0.4, 0.3, 0.2]); return m; }
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

  const URL = { thugs: 'models/cast/thugs.glb', gale: 'models/cast/gale.glb', synth: 'models/cast/synth.glb', miles: 'models/cast/miles.glb',
    kastor: 'models/cast/kastor.glb', dane: 'models/cast/dane.glb', vela: 'models/cast/vela.glb', dolores: 'models/cast/dolores.glb', harrow: 'models/cast/harrow.glb' };
  const FAMILY = { thug_a: 'thugs', thug_b: 'thugs', thug_c: 'thugs', gale_a: 'gale', gale_b: 'gale', gale_c: 'gale', synth: 'synth', miles: 'miles',
    kastor: 'kastor', dane: 'dane', vela: 'vela', dolores: 'dolores', harrow: 'harrow' };
  const VARIANTS = Object.keys(FAMILY);
  function preload(fams) { for (const f of fams || ['thugs', 'gale', 'synth', 'miles']) family(NR.ASSET + URL[f]); }
  function ready(variant) { const p = tplCache[NR.ASSET + URL[FAMILY[variant]]]; return p && p.done ? p.done : null; }

  const WEAPONS = ['pistol', 'revolver', 'tommy', 'knife', 'flashlight'];
  class Rig {
    constructor(tpl, variant) {
      this.variant = variant; this.tpl = tpl;
      const own = (n) => VARIANTS.some(v => n === v || n.startsWith(v + '_'));
      const inst = instance(tpl, n => !own(n) || n === variant || n.startsWith(variant + '_'));
      this.root = inst.root; this.nodes = inst.nodes;
      this.lod0 = this.nodes[variant]; this.lod1 = this.nodes[variant + '_lod1']; if (this.lod1) this.lod1.visible = false;
      this.weapons = WEAPONS.filter(w => this.nodes[variant + '_' + w]);
      const main = this.weapons.find(w => w !== 'flashlight') || null;
      this.kind = main === 'knife' ? (this.weapons.includes('flashlight') ? 'knife_lamp' : 'knife') : main === 'revolver' ? 'pistol' : main || 'none';
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
      this.root.updateMatrixWorld(true); const r0 = this.root.getWorldPosition(new T.Vector3());
      this.ankle0 = Math.min(this.nodes.foot_L.getWorldPosition(new T.Vector3()).y, this.nodes.foot_R.getWorldPosition(new T.Vector3()).y) - r0.y;
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
    // ---- foot locking: a foot that touches down is pinned to its world spot until it lifts (two-bone leg IK keeps the
    // knee bending toward where it already points; the foot keeps its animated orientation)
    rotateTo(bone, from, to) {
      if (from.lengthSq() < 1e-10 || to.lengthSq() < 1e-10) return;
      const q = new T.Quaternion().setFromUnitVectors(from.normalize(), to.normalize());
      const bw = bone.getWorldQuaternion(new T.Quaternion()), pw = bone.parent.getWorldQuaternion(new T.Quaternion());
      bone.quaternion.copy(pw.invert().multiply(q.multiply(bw))); bone.updateMatrixWorld(true);
    }
    legIK(s, Tgt) {
      const th = this.nodes['thigh_' + s], sh = this.nodes['shin_' + s], ft = this.nodes['foot_' + s];
      const H = th.getWorldPosition(new T.Vector3()), K = sh.getWorldPosition(new T.Vector3()), A = ft.getWorldPosition(new T.Vector3());
      const fq = ft.getWorldQuaternion(new T.Quaternion());
      const a = H.distanceTo(K), b = K.distanceTo(A);
      const dv = Tgt.clone().sub(H); let d = dv.length(); if (d < 1e-5) return; dv.divideScalar(d);
      d = Math.min(Math.max(d, Math.abs(a - b) + 1e-3), a + b - 1e-3);
      const pole = K.clone().sub(H); pole.addScaledVector(dv, -pole.dot(dv)); if (pole.lengthSq() < 1e-8) pole.set(0, 0, 1); pole.normalize();
      const ca = (a * a + d * d - b * b) / (2 * a * d), sa = Math.sqrt(Math.max(0, 1 - ca * ca));
      const K2 = H.clone().addScaledVector(dv, a * ca).addScaledVector(pole, a * sa);
      this.rotateTo(th, K.clone().sub(H), K2.clone().sub(H));
      const A1 = ft.getWorldPosition(new T.Vector3()), K1 = sh.getWorldPosition(new T.Vector3());
      this.rotateTo(sh, A1.sub(K1), H.clone().addScaledVector(dv, d).sub(K1));
      const sw = sh.getWorldQuaternion(new T.Quaternion()); ft.quaternion.copy(sw.invert().multiply(fq)); ft.updateMatrixWorld(true);
    }
    footLock(dt, on, groundY, release = 0.28) {
      if (this.ankle0 == null) return;
      this.fl = this.fl || { L: { lock: null, w: 0 }, R: { lock: null, w: 0 } };
      if (this.flClip !== this.layerName.L) { this.flClip = this.layerName.L; this.fl.L.h = []; this.fl.R.h = []; } // new gait, new contact heights
      for (const s of ['L', 'R']) {
        const st = this.fl[s], A = this.nodes['foot_' + s].getWorldPosition(new T.Vector3());
        // contact height = this foot's lowest point over the last stride (mocap feet land at different heights)
        this.t_ = (this.t_ || 0) + (s === 'L' ? dt : 0);
        st.h = st.h || []; st.h.push([this.t_, A.y]); while (st.h.length && st.h[0][0] < this.t_ - 0.8) st.h.shift();
        st.lo = Math.min(...st.h.map(q => q[1]));
        const vy = st.py == null ? 0 : (A.y - st.py) / Math.max(dt, 1e-3); st.py = A.y;
        const down = on && A.y < st.lo + 0.022 && (st.lock || Math.abs(vy) < 0.5);
        if (down && !st.lock) { st.lock = A.clone(); st.w = 1; }               // pin at once: zero offset at touch-down
        if ((!down || Math.hypot(st.lock.x - A.x, st.lock.z - A.z) > release) && st.lock) { st.out = st.lock; st.lock = null; }
        if (!st.lock) st.w = Math.max(0, st.w - dt * 12);                       // ease the leg back to the clip as it lifts
        const tgt = st.lock || st.out; if (!tgt || st.w < 0.01) continue;
        const Tg = A.clone(); Tg.x += (tgt.x - A.x) * st.w; Tg.z += (tgt.z - A.z) * st.w;
        this.legIK(s, Tg); 
      }
    }
    update(dt) { this.mixer.update(dt); this.root.updateMatrixWorld(true); }
  }

  NR.gltf = NR.gltf || {}; NR.gltf.template = template; NR.gltf.instance = instance;
  NR.cast = { Rig, family, preload, ready, URL, FAMILY, LOWER };
})();
