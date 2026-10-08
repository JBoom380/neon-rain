// NEON RAIN fx: prop models (revolver, fedora), cigarette smoke and haze, rain, blood (spray, wall + floor decals, wounds;
// pale milky fluid for artificial humans), tracers, muzzle flash.
(function () {
  const T = THREE, V3 = (x, y, z) => new T.Vector3(x, y, z);
  const U = { time: { value: 0 } };
  const DPR = () => Math.min(devicePixelRatio || 1, 2);
  const BLOOD = { human: 0x4c0303, artificial: 0xe4e0d0 }; // dark arterial red (the noir grade lifts reds; keep the base deep)

  function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; return t; }

  // ---------------------------------------------------------------- models
  function revolverModel(lying) {
    const g = new T.Group(), inner = new T.Group(); g.add(inner);
    const blued = new T.MeshStandardMaterial({ color: 0x4a4f58, roughness: 0.42, metalness: 0.35 });
    const wood = new T.MeshStandardMaterial({ color: 0x6a4028, roughness: 0.55 });
    const part = (geo, m, x, y, z, rx, ry, rz) => { const p = new T.Mesh(geo, m); p.position.set(x, y, z); p.rotation.set(rx || 0, ry || 0, rz || 0); p.castShadow = true; inner.add(p); return p; };
    // built along -Z (muzzle forward), y up; units metres
    part(new T.CylinderGeometry(0.011, 0.011, 0.16, 10), blued, 0, 0.028, -0.12, Math.PI / 2);   // barrel
    part(new T.BoxGeometry(0.012, 0.012, 0.16), blued, 0, 0.042, -0.12);                         // rib
    part(new T.BoxGeometry(0.006, 0.01, 0.008), blued, 0, 0.052, -0.195);                        // front sight
    const drum = part(new T.CylinderGeometry(0.024, 0.024, 0.048, 12), new T.MeshStandardMaterial({ color: 0x5a5f68, roughness: 0.35, metalness: 0.4 }), 0, 0.02, -0.02, Math.PI / 2);
    part(new T.BoxGeometry(0.028, 0.05, 0.06), blued, 0, 0.012, 0.02);                            // frame
    part(new T.BoxGeometry(0.008, 0.02, 0.012), blued, 0, 0.05, 0.05, -0.4);                     // hammer
    part(new T.BoxGeometry(0.03, 0.085, 0.034), wood, 0, -0.045, 0.065, 0.35);                    // grip
    const tg = part(new T.TorusGeometry(0.015, 0.003, 5, 10, Math.PI), blued, 0, -0.012, 0.012, 0, Math.PI / 2, Math.PI); void tg;
    g.userData.drum = drum; g.userData.inner = inner;
    if (lying) { inner.rotation.x = 0; if (revAsset) swapRevolver(g); else lyingGuns.push(g); }
    return g;
  }
  // the modelled revolver (assets/models/vm_revolver.glb, loaded by player.js) replaces the code model on desks/props
  let revAsset = null; const lyingGuns = [];
  function swapRevolver(g) { const m = revAsset.clone(true); m.position.set(0, 0, 0); m.rotation.set(0, 0, 0); g.userData.inner.visible = false; g.add(m); }
  function useRevolverAsset(node) { revAsset = node; for (const g of lyingGuns.splice(0)) swapRevolver(g); }
  function hatModel(color) {
    const hat = new T.Group(); const m = new T.MeshLambertMaterial({ color });
    const brimPts = []; for (let i = 0; i <= 6; i++) { const r = 0.11 + i * 0.0165; brimPts.push(new T.Vector2(r, 0.008 + 0.012 * Math.pow(i / 6, 2))); }
    const brim = new T.Mesh(new T.LatheGeometry(brimPts, 20), new T.MeshLambertMaterial({ color, side: T.DoubleSide })); hat.add(brim);
    const crown = new T.Mesh(new T.LatheGeometry([V3(0.105, 0, 0), V3(0.105, 0.03, 0), V3(0.1, 0.09, 0), V3(0.09, 0.12, 0), V3(0.05, 0.115, 0), V3(0, 0.105, 0)].map(v => new T.Vector2(v.x, v.y)), 20), m);
    crown.scale.set(1, 1, 0.86); crown.position.y = 0.008; hat.add(crown);
    const band = new T.Mesh(new T.CylinderGeometry(0.107, 0.107, 0.025, 20, 1, true), new T.MeshLambertMaterial({ color: 0x0e0d0c })); band.scale.set(1, 1, 0.86); band.position.y = 0.022; hat.add(band);
    hat.traverse(o => { if (o.isMesh) o.castShadow = true; });
    return hat;
  }

  // ---------------------------------------------------------------- smoke (GPU points; lit by the scene's cookie light)
  const blackTex = new T.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1); blackTex.needsUpdate = true;
  function smoke(N, origin, opts, shaft) {
    const geo = new T.BufferGeometry(), pos = new Float32Array(N * 3), seed = new Float32Array(N);
    for (let i = 0; i < N; i++) { seed[i] = Math.random(); pos[i * 3] = origin.x; pos[i * 3 + 1] = origin.y; pos[i * 3 + 2] = origin.z; }
    geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('seed', new T.BufferAttribute(seed, 1));
    const mat = new T.ShaderMaterial({ transparent: true, depthWrite: false, depthTest: opts.depthTest !== false,
      uniforms: { time: opts.time || U.time, rise: { value: opts.rise }, spread: { value: opts.spread }, size: { value: opts.size * DPR() }, alpha: { value: opts.alpha }, on: { value: 1 },
        cookie: { value: shaft ? shaft.cookie : blackTex }, lightVP: { value: shaft ? shaft.lightVP : new T.Matrix4() }, lit: { value: shaft ? 1 : 0 }, tint: { value: new T.Color(opts.tint || 0xc8d0d8) }, life: { value: opts.life || 4 } },
      vertexShader: `attribute float seed; uniform float time, rise, spread, size, life, lit; uniform sampler2D cookie; uniform mat4 lightVP; varying float vA, vL, vS;
        void main(){ float t=fract(time/life + seed); vA=t; vS=seed; float hgt=t*rise; vec3 p=position;
          p.x += sin(hgt*9.+seed*6.)*spread*t + sin(time*0.7+seed*20.)*0.01*t; p.z += cos(hgt*7.+seed*3.)*spread*0.6*t; p.y += hgt;
          vL = 0.; if (lit > 0.5) { vec4 lp=lightVP*modelMatrix*vec4(p,1.); vec2 luv=lp.xy/lp.w*0.5+0.5; vL = (lp.w>0.&&luv.x>0.&&luv.x<1.&&luv.y>0.&&luv.y<1.)? texture2D(cookie,luv).r : 0.; }
          vec4 mv=modelViewMatrix*vec4(p,1.); gl_Position=projectionMatrix*mv; gl_PointSize = size*(0.45+t*1.6)/max(0.05,-mv.z); }`,
      fragmentShader: `uniform float alpha, on; uniform vec3 tint; varying float vA, vL, vS;
        float h(vec2 p){ return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
        float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
        void main(){ vec2 q=gl_PointCoord-0.5; float r=length(q); float wisp = n(q*5.+vS*30.)*0.6+n(q*11.-vS*17.)*0.4; float a = smoothstep(0.5,0.05,r)*smoothstep(0.25,0.8,wisp);
          a *= smoothstep(0.0,0.03,vA)*(1.-vA)*alpha*on; if (a < 0.003) discard; vec3 c=tint*(0.35+1.6*vL); gl_FragColor=vec4(c, a); }` });
    const pts = new T.Points(geo, mat); pts.frustumCulled = false; return pts;
  }

  // ---------------------------------------------------------------- rain (streaks wrapped in a box around the camera)
  function rain(N) {
    const geo = new T.BufferGeometry(), pos = new Float32Array(N * 6), sd = new Float32Array(N * 2);
    for (let i = 0; i < N; i++) { const x = Math.random(), y = Math.random(), z = Math.random(); for (let k = 0; k < 2; k++) { pos[i * 6 + k * 3] = x; pos[i * 6 + k * 3 + 1] = y; pos[i * 6 + k * 3 + 2] = z; sd[i * 2 + k] = k; } }
    geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('tail', new T.BufferAttribute(sd, 1));
    const mat = new T.ShaderMaterial({ transparent: true, depthWrite: false,
      uniforms: { time: { value: 0 }, box: { value: V3(14, 12, 18) } },
      vertexShader: `attribute float tail; uniform float time; uniform vec3 box; varying float vT, vD;
        void main(){ vec3 c = cameraPosition; vec3 p = position*box;
          p.y = mod(p.y - time*11.0, box.y);
          p.x = mod(p.x - c.x + box.x*0.5, box.x) + c.x - box.x*0.5; p.z = mod(p.z - c.z + box.z*0.5, box.z) + c.z - box.z*0.5; p.y += c.y - box.y*0.45;
          p.y += tail*0.32; p.x += tail*0.04; vT = tail; vec4 mv = viewMatrix*vec4(p,1.); vD = -mv.z; gl_Position = projectionMatrix*mv; }`,
      fragmentShader: `varying float vT, vD; void main(){ float a = mix(0.42, 0.0, vT) * smoothstep(0.3, 1.5, vD) * smoothstep(16., 6., vD); gl_FragColor = vec4(0.72,0.8,0.86, a); }` });
    const l = new T.LineSegments(geo, mat); l.frustumCulled = false; return l;
  }

  // ---------------------------------------------------------------- per-level dynamic fx: decals, spray, tracers, flash light
  const splatTex = canvasTex(128, 128, (g, w, h) => {
    g.clearRect(0, 0, w, h); g.fillStyle = '#fff'; g.filter = 'blur(1.5px)';
    g.beginPath(); g.arc(64, 64, 22, 0, 7); g.fill();
    for (let i = 0; i < 22; i++) { const a = Math.random() * 6.28, d = 18 + Math.random() * 38, r = 2 + Math.random() * 8; g.beginPath(); g.arc(64 + Math.cos(a) * d, 64 + Math.sin(a) * d, r * (1 - d / 70), 0, 7); g.fill(); }
    for (let i = 0; i < 6; i++) { const a = Math.random() * 6.28; g.lineWidth = 3 + Math.random() * 4; g.strokeStyle = '#fff'; g.beginPath(); g.moveTo(64, 64); g.lineTo(64 + Math.cos(a) * 50, 64 + Math.sin(a) * 50); g.stroke(); }
  });
  const poolTex = canvasTex(128, 128, (g) => { g.fillStyle = '#fff'; g.filter = 'blur(3px)'; g.beginPath(); for (let i = 0; i < 7; i++) { const a = Math.random() * 6.28, d = Math.random() * 18; g.moveTo(64 + Math.cos(a) * d + 30, 64 + Math.sin(a) * d); g.arc(64 + Math.cos(a) * d, 64 + Math.sin(a) * d, 26 + Math.random() * 12, 0, 7); } g.fill(); });
  let L = null, decals = {}, pools = {}, spray = null, tracers = [], flashLight = null, wounds = [];
  const MAXD = 72, MAXP = 24, MAXS = 220;
  function decalMesh(tex, color, n, lit) {
    // wet blood: dark, glossy, soft-edged (lit by the scene, never flat)
    const m = new T.InstancedMesh(new T.PlaneGeometry(1, 1), new T.MeshStandardMaterial({ color, map: tex, transparent: true, depthWrite: false, alphaTest: 0.04, roughness: lit ? 0.6 : 0.18, metalness: 0, polygonOffset: true, polygonOffsetFactor: -4, emissive: lit ? color : 0, emissiveIntensity: lit ? 0.12 : 0 }), n);
    m.count = 0; m.frustumCulled = false; m.renderOrder = 2; m.userData.next = 0; m.userData.grow = []; return m;
  }
  function attach(level) {
    L = level; const S = level.scene;
    if (!level.fxReady) {
      level.fx = {
        decals: { human: decalMesh(splatTex, BLOOD.human, MAXD), artificial: decalMesh(splatTex, BLOOD.artificial, MAXD, true) },
        pools: { human: decalMesh(poolTex, 0x2a0202, MAXP), artificial: decalMesh(poolTex, 0xd8d4c4, MAXP, true) },
      };
      for (const k in level.fx.decals) S.add(level.fx.decals[k]); for (const k in level.fx.pools) S.add(level.fx.pools[k]);
      // spray particles
      const geo = new T.BufferGeometry(); const pos = new Float32Array(MAXS * 3), col = new Float32Array(MAXS * 3);
      geo.setAttribute('position', new T.BufferAttribute(pos, 3)); geo.setAttribute('color', new T.BufferAttribute(col, 3));
      const pm = new T.PointsMaterial({ size: 0.045, vertexColors: true, sizeAttenuation: true, transparent: true, depthWrite: false, map: NR.world && NR.world.glowTex, alphaTest: 0.03 }); // soft round droplets
      const pts = new T.Points(geo, pm); pts.frustumCulled = false; S.add(pts);
      level.fx.spray = { pts, pos, col, vel: new Float32Array(MAXS * 3), life: new Float32Array(MAXS), next: 0 };
      // tracers
      level.fx.tracers = [];
      for (let i = 0; i < 6; i++) { const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(6), 3)); const l = new T.Line(g, new T.LineBasicMaterial({ color: 0xffd8a0, transparent: true, opacity: 0, depthWrite: false })); l.frustumCulled = false; S.add(l); level.fx.tracers.push({ l, t: 0 }); }
      flashLight = new T.PointLight(0xffc070, 0, 7, 1.8); S.add(flashLight); level.fx.flash = flashLight;
      level.fxReady = true;
    }
    decals = level.fx.decals; pools = level.fx.pools; spray = level.fx.spray; tracers = level.fx.tracers; flashLight = level.fx.flash;
  }
  const _m = new T.Matrix4(), _q = new T.Quaternion(), _s = new T.Vector3(), _z = V3(0, 0, 1), _q2 = new T.Quaternion();
  function putDecal(mesh, p, n, size, grow) {
    const i = mesh.userData.next; mesh.userData.next = (i + 1) % mesh.instanceMatrix.count; mesh.count = Math.max(mesh.count, i + 1);
    _q.setFromUnitVectors(_z, n); _q2.setFromAxisAngle(_z, Math.random() * 6.28); _q.multiply(_q2);
    _s.set(size, size, size); _m.compose(p.clone().addScaledVector(n, 0.012), _q, _s); mesh.setMatrixAt(i, _m); mesh.instanceMatrix.needsUpdate = true;
    if (grow) mesh.userData.grow.push({ i, p: p.clone().addScaledVector(n, 0.012), q: _q.clone(), s: size * 0.2, to: size, rate: size * 0.25 });
  }
  // a bullet wound: spray toward the exit, splat on the wall behind (ray along the shot), wound mark on the body
  function blood(point, dir, kind, amount, bodyMesh) {
    if (!L) return; kind = kind === 'artificial' ? 'artificial' : 'human';
    const c = new T.Color(BLOOD[kind]); const sp = spray;
    const n = Math.round(14 * amount);
    for (let k = 0; k < n; k++) {
      const i = sp.next; sp.next = (i + 1) % MAXS;
      sp.pos[i * 3] = point.x; sp.pos[i * 3 + 1] = point.y; sp.pos[i * 3 + 2] = point.z;
      const s = 1.5 + Math.random() * 3.5;
      sp.vel[i * 3] = dir.x * s + (Math.random() - 0.5) * 1.6; sp.vel[i * 3 + 1] = dir.y * s + Math.random() * 1.5; sp.vel[i * 3 + 2] = dir.z * s + (Math.random() - 0.5) * 1.6;
      sp.life[i] = 0.5 + Math.random() * 0.5; const v = 0.75 + Math.random() * 0.4; sp.col[i * 3] = c.r * v; sp.col[i * 3 + 1] = c.g * v; sp.col[i * 3 + 2] = c.b * v;
    }
    sp.pts.geometry.attributes.color.needsUpdate = true;
    const hit = L.ray(point, dir, 3.5);
    if (hit) putDecal(decals[kind], hit.point, hit.normal, 0.35 + amount * 0.35);
    // floor drops under the wound
    const down = L.ray(point.clone().addScaledVector(dir, 0.4), V3(0, -1, 0), 3);
    putDecal(decals[kind], down ? down.point : V3(point.x + dir.x * 0.4, 0, point.z + dir.z * 0.4), V3(0, 1, 0), 0.25 + Math.random() * 0.2);
    if (bodyMesh) wound(bodyMesh, point, kind);
  }
  const woundGeo = new T.CircleGeometry(0.035, 8), woundMats = { human: new T.MeshLambertMaterial({ color: 0x3a0202 }), artificial: new T.MeshLambertMaterial({ color: 0xd8d4c4, emissive: 0x2a2a26 }) };
  function wound(mesh, worldPoint, kind) {
    if ((mesh.userData.wounds || 0) >= 4) return; mesh.userData.wounds = (mesh.userData.wounds || 0) + 1;
    const w = new T.Mesh(woundGeo, woundMats[kind]); const lp = mesh.worldToLocal(worldPoint.clone());
    const out = lp.clone().setY(0); if (out.lengthSq() < 1e-6) out.set(0, 0, 1); out.normalize();
    w.position.copy(lp).addScaledVector(out, 0.015); w.quaternion.setFromUnitVectors(_z, out); mesh.add(w);
    wounds.push(w);
  }
  function impact(p, n) { // dust + sparks where a bullet hits a wall
    if (!L) return; const sp = spray;
    for (let k = 0; k < 8; k++) { const i = sp.next; sp.next = (i + 1) % MAXS; sp.pos[i * 3] = p.x; sp.pos[i * 3 + 1] = p.y; sp.pos[i * 3 + 2] = p.z;
      const s = 1 + Math.random() * 2.5; sp.vel[i * 3] = n.x * s + (Math.random() - 0.5) * 2; sp.vel[i * 3 + 1] = n.y * s + Math.random() * 1.5; sp.vel[i * 3 + 2] = n.z * s + (Math.random() - 0.5) * 2;
      sp.life[i] = 0.25 + Math.random() * 0.3; const v = k < 2 ? [1, 0.8, 0.4] : [0.5, 0.48, 0.45]; sp.col[i * 3] = v[0]; sp.col[i * 3 + 1] = v[1]; sp.col[i * 3 + 2] = v[2]; }
    sp.pts.geometry.attributes.color.needsUpdate = true;
  }
  function pool(p, kind) { kind = kind === 'artificial' ? 'artificial' : 'human'; putDecal(pools[kind], V3(p.x, 0.003, p.z), V3(0, 1, 0), 1.2 + Math.random() * 0.5, true); }
  function tracer(a, b) {
    if (!tracers.length) return; const tr = tracers.find(t => t.t <= 0) || tracers[0];
    const p = tr.l.geometry.attributes.position; p.setXYZ(0, a.x, a.y, a.z); p.setXYZ(1, b.x, b.y, b.z); p.needsUpdate = true; tr.t = 0.08; tr.l.material.opacity = 0.9;
  }
  function muzzle(p, power = 1) { if (!flashLight) return; flashLight.position.copy(p); flashLight.intensity = 12 * power; flashT = 0.06; }
  let flashT = 0;
  function update(dt, rdt) {
    U.time.value += rdt * (0.4 + 0.6 * (NR.core ? NR.core.timeScale : 1));
    if (!L) return;
    const sp = spray, g = 9.8;
    let any = false;
    for (let i = 0; i < MAXS; i++) {
      if (sp.life[i] <= 0) continue; any = true; sp.life[i] -= dt;
      sp.vel[i * 3 + 1] -= g * dt; sp.pos[i * 3] += sp.vel[i * 3] * dt; sp.pos[i * 3 + 1] += sp.vel[i * 3 + 1] * dt; sp.pos[i * 3 + 2] += sp.vel[i * 3 + 2] * dt;
      if (sp.pos[i * 3 + 1] < 0.01) { sp.pos[i * 3 + 1] = 0.01; sp.vel[i * 3] = sp.vel[i * 3 + 1] = sp.vel[i * 3 + 2] = 0; }
      if (sp.life[i] <= 0) sp.pos[i * 3 + 1] = -100;
    }
    if (any) sp.pts.geometry.attributes.position.needsUpdate = true;
    for (const k in pools) { const m = pools[k]; const gl = m.userData.grow; for (let j = gl.length - 1; j >= 0; j--) { const e = gl[j]; e.s = Math.min(e.to, e.s + e.rate * dt); _s.set(e.s, e.s, e.s); _m.compose(e.p, e.q, _s); m.setMatrixAt(e.i, _m); m.instanceMatrix.needsUpdate = true; if (e.s >= e.to) gl.splice(j, 1); } }
    for (const t of tracers) if (t.t > 0) { t.t -= rdt; t.l.material.opacity = Math.max(0, t.t / 0.08) * 0.9; }
    if (flashT > 0) { flashT -= rdt; if (flashT <= 0) flashLight.intensity = 0; }
  }

  NR.fx = { U, revolverModel, useRevolverAsset, hatModel, smoke, rain, attach, blood, impact, pool, tracer, muzzle, update, BLOOD, canvasTex };
})();
