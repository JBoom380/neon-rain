// NEON RAIN minimal GLB loader (the three r186 global build has no GLTFLoader): node tree, meshes, PBR materials
// (base colour, textures, alpha blend), skins (SkinnedMesh + Skeleton) and animations (AnimationClip). Enough for the
// character GLBs exported from Blender, plus the baked environment GLBs (TEXCOORD_1, emissive maps, material and scene
// extras); no sparse accessors, no byte strides, no Draco.
(function () {
  const T = THREE;
  const TA = { 5126: Float32Array, 5125: Uint32Array, 5123: Uint16Array, 5121: Uint8Array, 5122: Int16Array, 5120: Int8Array };
  const NC = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
  async function load(url) {
    const buf = await (await fetch(url)).arrayBuffer();
    const dv = new DataView(buf); let off = 12, json = null, bin = null;
    while (off < buf.byteLength) { const len = dv.getUint32(off, true), type = dv.getUint32(off + 4, true); const chunk = buf.slice(off + 8, off + 8 + len); if (type === 0x4E4F534A) json = JSON.parse(new TextDecoder().decode(chunk)); else bin = chunk; off += 8 + len; }
    const arr = (i) => { const a = json.accessors[i], bv = json.bufferViews[a.bufferView], C = TA[a.componentType], n = NC[a.type]; const start = (bv.byteOffset || 0) + (a.byteOffset || 0); return { array: new C(bin.slice(start, start + a.count * n * C.BYTES_PER_ELEMENT)), n, norm: !!a.normalized }; };
    const attr = (i) => { const r = arr(i); return new T.BufferAttribute(r.array, r.n, r.norm); };
    const images = await Promise.all((json.images || []).map(async (im) => { const bv = json.bufferViews[im.bufferView]; const blob = new Blob([bin.slice(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength)], { type: im.mimeType }); return createImageBitmap(blob, { imageOrientation: 'none' }); }));
    const texCache = {};
    const tex = (info, srgb) => { if (!info) return null; const src = json.textures[info.index].source, k = src + (srgb ? 's' : 'l'); if (!texCache[k]) { const t = new T.Texture(images[src]); t.flipY = false; t.colorSpace = srgb ? T.SRGBColorSpace : T.NoColorSpace; t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 4; t.needsUpdate = true; texCache[k] = t; } return texCache[k]; };
    const mats = (json.materials || []).map(md => {
      const pb = md.pbrMetallicRoughness || {}, f = pb.baseColorFactor || [1, 1, 1, 1];
      const m = new T.MeshStandardMaterial({ name: md.name, color: new T.Color().setRGB(f[0], f[1], f[2], T.LinearSRGBColorSpace), opacity: f[3],
        metalness: pb.metallicFactor == null ? 1 : pb.metallicFactor, roughness: pb.roughnessFactor == null ? 1 : pb.roughnessFactor,
        map: tex(pb.baseColorTexture, true), side: md.doubleSided ? T.DoubleSide : T.FrontSide });
      if (md.emissiveFactor) m.emissive.setRGB(...md.emissiveFactor, T.LinearSRGBColorSpace);
      if (md.emissiveTexture) { m.emissiveMap = tex(md.emissiveTexture, true); m.userData.emissiveTexCoord = md.emissiveTexture.texCoord || 0; } // env GLBs: texCoord 1 = baked lightmap
      m.userData.extras = md.extras || {}; if (pb.baseColorTexture) m.userData.mapTexCoord = pb.baseColorTexture.texCoord || 0;
      if (md.extensions && md.extensions.KHR_materials_emissive_strength) m.emissiveIntensity = md.extensions.KHR_materials_emissive_strength.emissiveStrength;
      if (md.alphaMode === 'BLEND') { m.transparent = true; m.depthWrite = false; m.alphaTest = 0.08; }
      if (md.alphaMode === 'MASK') m.alphaTest = md.alphaCutoff == null ? 0.5 : md.alphaCutoff;
      return m;
    });
    const nodes = json.nodes.map((n) => { const o = new T.Group(); o.name = n.name || ''; if (n.matrix) new T.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale); if (n.translation) o.position.fromArray(n.translation); if (n.rotation) o.quaternion.fromArray(n.rotation); if (n.scale) o.scale.fromArray(n.scale); return o; });
    json.nodes.forEach((n, i) => { for (const c of n.children || []) nodes[i].add(nodes[c]); });
    const skins = (json.skins || []).map(s => { const ib = arr(s.inverseBindMatrices).array; const bones = s.joints.map(j => nodes[j]); const inv = s.joints.map((_, k) => new T.Matrix4().fromArray(ib, k * 16)); return { bones, inv }; });
    const skinned = [];
    json.nodes.forEach((n, i) => {
      if (n.mesh === undefined) return;
      for (const p of json.meshes[n.mesh].primitives) {
        const g = new T.BufferGeometry(), A = p.attributes;
        g.setAttribute('position', attr(A.POSITION)); if (A.NORMAL !== undefined) g.setAttribute('normal', attr(A.NORMAL)); if (A.TEXCOORD_0 !== undefined) g.setAttribute('uv', attr(A.TEXCOORD_0)); if (A.TEXCOORD_1 !== undefined) g.setAttribute('uv1', attr(A.TEXCOORD_1));
        if (A.JOINTS_0 !== undefined) g.setAttribute('skinIndex', attr(A.JOINTS_0)); if (A.WEIGHTS_0 !== undefined) g.setAttribute('skinWeight', attr(A.WEIGHTS_0));
        if (p.indices !== undefined) g.setIndex(attr(p.indices));
        if (A.NORMAL === undefined) g.computeVertexNormals();
        const mat = mats[p.material] || new T.MeshStandardMaterial();
        let m;
        if (n.skin !== undefined && A.JOINTS_0 !== undefined) { m = new T.SkinnedMesh(g, mat); skinned.push([m, n.skin]); } else m = new T.Mesh(g, mat);
        m.name = n.name || ''; m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false; nodes[i].add(m);
      }
    });
    const root = new T.Group(); for (const i of json.scenes[json.scene || 0].nodes) root.add(nodes[i]);
    root.updateMatrixWorld(true);
    for (const [m, si] of skinned) { const s = skins[si]; m.bind(new T.Skeleton(s.bones, s.inv), m.matrixWorld); }
    const clips = (json.animations || []).map(a => {
      const tracks = [];
      for (const ch of a.channels) {
        const s = a.samplers[ch.sampler], node = nodes[ch.target.node]; if (!node) continue;
        const times = arr(s.input).array, vals = arr(s.output).array, name = node.uuid + '.' + ({ translation: 'position', rotation: 'quaternion', scale: 'scale' })[ch.target.path];
        if (!name.endsWith('undefined') && s.interpolation !== 'CUBICSPLINE') {
          const TT = ch.target.path === 'rotation' ? T.QuaternionKeyframeTrack : T.VectorKeyframeTrack;
          tracks.push(new TT(name, Array.from(times), Array.from(vals), s.interpolation === 'STEP' ? T.InterpolateDiscrete : undefined));
        }
      }
      return new T.AnimationClip(a.name, -1, tracks);
    });
    return { scene: root, animations: clips, materials: mats, extras: json.scenes[json.scene || 0].extras || {} };
  }
  NR.gltf = { load };
})();
