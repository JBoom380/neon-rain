// NEON RAIN environment pass: the three slice sets as baked Blender scenes (assets/models/env_*.glb, built by
// tools/env/*.py). Film lighting is baked: the room shell is tiled albedo x lightmap (UV2), props and dynamic pieces are
// baked albedo x light atlases, all unlit on the phone. Real-time on top: the cookie spot (stripes on the characters,
// half-res light shafts), rain on the glass, smoke, neon flicker, the door and the fan. Colliders come from the GLB.
// Replaces NR.world.build.<level> for every level listed in FILES; the grey-box builders stay as the fallback.
(function () {
  const T = THREE, W = NR.world, V3 = W.V3;
  const FILES = { club: 'models/env_club.glb', office: 'models/env_office.glb', alley: 'models/env_alley.glb' };
  const ON = (new URLSearchParams(location.search).get('env') || 'baked') !== 'grey';
  NR.cfg.EYE = 1.65; // standing eye height (metres)

  // ---------------------------------------------------------------- loading (club first: it is the title backdrop)
  const cache = {}, ready = {};
  function get(name) {
    if (!cache[name]) cache[name] = NR.gltf.load(NR.ASSET + FILES[name]).catch(e => { console.warn('[env] ' + name + ' GLB failed, using the grey-box set', e); return null; });
    return cache[name];
  }
  NR.env = { ready, files: FILES, exposure: 1.0 };

  // baked highlights are soft-clipped near 1.3 so the grade's halation sees a glow, not a hot texel it smears into streaks
  function clampHi(mat) {
    const prev = mat.onBeforeCompile;
    mat.onBeforeCompile = (s, r) => { if (prev) prev(s, r); s.fragmentShader = s.fragmentShader.replace('#include <opaque_fragment>', '{ vec3 kk = max(outgoingLight - vec3(0.8), vec3(0.0)); outgoingLight = min(outgoingLight, vec3(0.8)) + kk / (1.0 + kk / 0.6); }\n#include <opaque_fragment>'); };
    mat.customProgramCacheKey = () => 'clampHi' + (prev ? 'w' : '');
  }
  // GLB materials -> phone materials (unlit, baked)
  function phoneMats(root, opts) {
    const neon = [];
    root.traverse(o => {
      if (!o.isMesh) return;
      o.castShadow = false; o.receiveShadow = false; o.frustumCulled = true; o.matrixAutoUpdate = true;
      const m = o.material, x = (m.userData && m.userData.extras) || {};
      let n = null;
      if (x.lm != null && m.emissiveMap) {
        const lmTex = m.emissiveMap; lmTex.channel = 1;
        const tint = x.tint || [1, 1, 1];
        n = new T.MeshBasicMaterial({ map: m.map, lightMap: lmTex, lightMapIntensity: x.lm * Math.PI * NR.env.exposure * (opts.lm || 1), color: new T.Color(tint[0], tint[1], tint[2]) });
        if (m.map) m.map.channel = 0;
      } else if (x.baked != null) {
        const k = x.baked * NR.env.exposure * (opts.baked || 1);
        n = new T.MeshBasicMaterial({ map: m.map, color: new T.Color(k, k, k) });
      } else if (/^NEON/.test(m.name)) {
        const c = m.emissive.clone().multiplyScalar((m.emissiveIntensity || 1) * (opts.neon || 1));
        n = new T.MeshBasicMaterial({ color: c, fog: false }); n.userData.base = c.clone(); neon.push({ mesh: o, mat: n, ph: Math.random() * 10 });
      } else if (/^GLOW/.test(m.name)) {
        n = new T.MeshBasicMaterial({ color: m.emissive.clone().multiplyScalar(m.emissiveIntensity || 1), map: m.emissiveMap || m.map || null, transparent: true, blending: T.AdditiveBlending, depthWrite: false, fog: false });
      } else if (/^MIRROR|^WET/.test(m.name)) {
        n = m; n.userData.keep = true;
      }
      if (n && (x.lm != null || x.baked != null)) clampHi(n);
      if (n) { n.name = m.name; o.material = n; m.dispose(); }
      if (n && m.map && n.map) { n.map.anisotropy = 8; }
    });
    return neon;
  }
  // colliders from the GLB scene extras, then the level's cover points
  function addColliders(L, extras) {
    let list = []; try { list = JSON.parse(extras.colliders || '[]'); } catch (e) { console.warn('[env] colliders', e); }
    for (const c of list) L.boxes.push({ min: V3(...c.min), max: V3(...c.max), cover: !!c.cover, step: !!c.step, tag: c.tag || '' });
    L.covers = []; L.finish();
  }
  function node(root, name) { let r = null; root.traverse(o => { if (!r && o.name === name) r = o; }); return r; }

  // attach a loaded GLB to a level (now, or when it arrives)
  function attach(L, name, onReady, opts = {}) {
    L.envReady = false;
    ready[name] = get(name).then(g => {
      if (!g) { // network failure: fall back to the grey-box geometry so the beat stays playable
        const F = NR.env.orig && NR.env.orig[name] && NR.env.orig[name](NR.core.settings.quality);
        if (F) { for (const c of [...F.scene.children]) if (c.isMesh) L.scene.add(c); L.boxes.push(...F.boxes.filter(b => b.tag !== 'door')); L.covers = []; L.finish(); }
        return false;
      }
      const neon = phoneMats(g.scene, opts);
      L.scene.add(g.scene); L.env = g.scene; addColliders(L, g.extras);
      L.neon = neon;
      if (neon.length) L.updaters.push((dt, t) => { for (const n of neon) { const f = n.mesh.userData.flicker || 0.05; const k = 1 - f * (0.5 + 0.5 * Math.sin(t * 23 + n.ph)) * (Math.sin(t * 1.7 + n.ph * 3) > 0.92 ? 6 : 1); n.mat.color.copy(n.mat.userData.base).multiplyScalar(Math.max(0.15, k)); } });
      if (onReady) onReady(g.scene);
      L.envReady = true; if (NR.core && NR.core.scene === L.scene) NR.core.renderer.shadowMap.needsUpdate = true;
      return true;
    });
    return ready[name];
  }

  // a sodium-lit city through the window: dark masses, warm windows, a few distant neon signs in the haze
  function cityTex(w, h, seed, opts = {}) {
    const rnd = NR.rng(seed);
    return W.tex(w, h, (g) => {
      const sky = g.createLinearGradient(0, 0, 0, h); sky.addColorStop(0, '#05040a'); sky.addColorStop(0.55, '#1a0d08'); sky.addColorStop(1, '#3a1a08');
      g.fillStyle = sky; g.fillRect(0, 0, w, h);
      for (let layer = 0; layer < 3; layer++) {
        let x = -20; const base = h * (0.32 + layer * 0.12), dark = [16, 10, 5][layer];
        while (x < w) {
          const bw = 40 + rnd() * 110, bh = base + rnd() * h * 0.25; const top = h - bh;
          g.fillStyle = `rgb(${dark + 6},${dark + 2},${dark})`; g.fillRect(x, top, bw, bh);
          const fin = rnd();
          if (fin < 0.45) { // ziggurat finial: stepped tiers, a spire, a warm aviation lamp
            let tw = bw * 0.8, ty = top; const cxb = x + bw / 2, steps = 3 + (rnd() * 3 | 0);
            for (let k = 0; k < steps; k++) { tw *= 0.72; ty -= 8 + rnd() * 6; g.fillRect(cxb - tw / 2, ty, tw, top - ty + 1); }
            g.fillRect(cxb - 1.5, ty - 22 - rnd() * 20, 3, 26); g.fillStyle = 'rgba(255,90,40,0.9)'; g.fillRect(cxb - 2, ty - 26, 4, 4);
            if (layer === 2) { g.strokeStyle = 'rgba(255,170,80,0.35)'; g.lineWidth = 1; for (let k = 0; k < 5; k++) { g.beginPath(); g.moveTo(cxb, ty); g.lineTo(cxb + (k - 2) * tw * 0.4, top); g.stroke(); } }
            g.fillStyle = `rgb(${dark + 6},${dark + 2},${dark})`;
          } else if (fin < 0.6) { g.fillRect(x + bw * 0.4, top - 18 - rnd() * 30, 4, 40); }
          for (let yy = top + 8; yy < h - 6; yy += 13 - layer * 2) for (let xx = x + 5; xx < x + bw - 6; xx += 10 - layer * 2) {
            if (rnd() < 0.2 + layer * 0.08) { const a = (0.25 + rnd() * 0.6) * (0.5 + layer * 0.25); const warm = rnd() < 0.85;
              g.fillStyle = warm ? `rgba(255,${120 + rnd() * 60 | 0},${30 + rnd() * 30 | 0},${a})` : `rgba(255,${190 + rnd() * 40 | 0},${120 + rnd() * 40 | 0},${a * 0.7})`;
              g.fillRect(xx, yy, 5 - layer, 7 - layer); }
          }
          x += bw + rnd() * 8;
        }
      }
      // distant neon in the haze
      const signs = opts.signs || [['HOTEL', '#ff3a1e', 0.2, 0.42], ['BAR', '#ff8a1a', 0.72, 0.5], ['DRUGS', '#2affc8', 0.5, 0.62]];
      for (const [t, c, fx, fy] of signs) {
        g.save(); g.font = 'bold ' + (w * 0.05 | 0) + 'px Georgia'; g.textAlign = 'center'; g.shadowColor = c; g.shadowBlur = 24; g.strokeStyle = c; g.lineWidth = 2.2;
        g.globalAlpha = 0.9; g.strokeText(t, w * fx, h * fy); g.shadowBlur = 6; g.strokeStyle = '#ffe8d0'; g.lineWidth = 0.8; g.strokeText(t, w * fx, h * fy); g.restore();
      }
      const haze = g.createLinearGradient(0, h * 0.5, 0, h); haze.addColorStop(0, 'rgba(120,50,10,0)'); haze.addColorStop(1, 'rgba(150,64,14,0.35)'); g.fillStyle = haze; g.fillRect(0, 0, w, h);
    });
  }
  // a neon sign drawn as glowing glass tubes (canvas): for far signs only; near signs are tube meshes in the GLBs
  function tubeSign(text, color, w, h, font) {
    return W.tex(w, h, (g) => { g.clearRect(0, 0, w, h); g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
      g.shadowColor = color; g.shadowBlur = 40; g.strokeStyle = color; g.lineWidth = 9; g.strokeText(text, w / 2, h / 2);
      g.shadowBlur = 14; g.lineWidth = 6; g.strokeText(text, w / 2, h / 2); g.shadowBlur = 0; g.strokeStyle = '#fff2e0'; g.lineWidth = 2; g.strokeText(text, w / 2, h / 2); });
  }
  NR.env.cityTex = cityTex; NR.env.tubeSign = tubeSign;

  // ---------------------------------------------------------------- haze + light beams (cheap volumetrics for the phone)
  const HZ = { time: { value: 0 } };
  const NOISE = `float hz3(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
    float vn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f*f*(3.-2.*f);
      return mix(mix(mix(hz3(i), hz3(i+vec3(1,0,0)), f.x), mix(hz3(i+vec3(0,1,0)), hz3(i+vec3(1,1,0)), f.x), f.y),
                 mix(mix(hz3(i+vec3(0,0,1)), hz3(i+vec3(1,0,1)), f.x), mix(hz3(i+vec3(0,1,1)), hz3(i+vec3(1,1,1)), f.x), f.y), f.z); }`;
  // a light cone in the haze: soft edges (view-angle falloff), fades along its length, slow drifting density
  function beam(parent, a, b, r0, r1, color, alpha) {
    const len = a.distanceTo(b);
    const geo = new T.CylinderGeometry(r0, r1, len, 20, 6, true); geo.translate(0, -len / 2, 0);
    const mat = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
      uniforms: { color: { value: new T.Color(color) }, alpha: { value: alpha }, len: { value: len }, time: HZ.time },
      vertexShader: `uniform float len; varying float vT; varying vec3 vN, vW; void main(){ vT = -position.y / len; vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz;
        vN = normalize(mat3(modelMatrix) * normal); gl_Position = projectionMatrix * viewMatrix * w; }`,
      fragmentShader: `uniform vec3 color; uniform float alpha, time; varying float vT; varying vec3 vN, vW; ${NOISE}
        void main(){ vec3 v = normalize(cameraPosition - vW); float rim = pow(abs(dot(normalize(vN), v)), 2.2);
          float fall = pow(1.0 - vT, 1.6) * smoothstep(0.0, 0.06, vT); float n = 0.55 + 0.45 * vn(vW * 1.3 + vec3(0.0, -time * 0.12, time * 0.05));
          gl_FragColor = vec4(color * alpha * rim * fall * n, 1.0); }` });
    const m = new T.Mesh(geo, mat); m.position.copy(a); m.quaternion.setFromUnitVectors(V3(0, -1, 0), b.clone().sub(a).normalize()); m.renderOrder = 6; m.frustumCulled = false;
    parent.add(m); return m;
  }
  function aimBeam(m, a, b) { m.position.copy(a); m.quaternion.setFromUnitVectors(V3(0, -1, 0), b.clone().sub(a).normalize()); }
  // a slab of lit haze (camera-facing about Y): drifting noise, soft box edges; gives the air a body behind doorways and over streets
  function hazeSlab(parent, pos, w, h, color, alpha) {
    const mat = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide,
      uniforms: { color: { value: new T.Color(color) }, alpha: { value: alpha }, time: HZ.time },
      vertexShader: 'varying vec2 vUv; varying vec3 vW; void main(){ vUv = uv; vec4 w = modelMatrix * vec4(position, 1.); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }',
      fragmentShader: `uniform vec3 color; uniform float alpha, time; varying vec2 vUv; varying vec3 vW; ${NOISE}
        void main(){ vec2 e = smoothstep(vec2(0.0), vec2(0.3), vUv) * smoothstep(vec2(0.0), vec2(0.3), 1.0 - vUv);
          float n = 0.45 + 0.55 * vn(vW * 0.7 + vec3(time * 0.06, -time * 0.03, 0.0));
          gl_FragColor = vec4(color * alpha * e.x * e.y * n, 1.0); }` });
    const m = new T.Mesh(new T.PlaneGeometry(w, h), mat); m.position.copy(pos); m.renderOrder = 4; parent.add(m);
    m.onBeforeRender = (r, s, cam) => { m.rotation.y = Math.atan2(cam.position.x - m.position.x, cam.position.z - m.position.z); };
    return m;
  }
  // CRT / video screen: scanlines, slight RGB fringing, curvature, flicker; `draw` paints the picture once
  function crtScreen(w, h, draw, tint) {
    const tex = W.tex(256, 192, draw);
    const mat = new T.ShaderMaterial({ uniforms: { map: { value: tex }, time: HZ.time, tint: { value: new T.Color(tint || 0x9fe8ff) } }, fog: false,
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
      fragmentShader: `uniform sampler2D map; uniform float time; uniform vec3 tint; varying vec2 vUv;
        float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
        void main(){ vec2 uv = vUv - 0.5; uv *= 1.0 + dot(uv, uv) * 0.18; uv += 0.5;
          if (uv.x < 0. || uv.x > 1. || uv.y < 0. || uv.y > 1.) { gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0); return; }
          float roll = fract(time * 0.12); float band = smoothstep(0.06, 0.0, abs(uv.y - roll)) * 0.25;
          uv.x += (h(vec2(floor(uv.y * 90.0), floor(time * 14.0))) - 0.5) * 0.004 + band * 0.01;
          vec3 c = vec3(texture2D(map, uv + vec2(0.003, 0.0)).r, texture2D(map, uv).g, texture2D(map, uv - vec2(0.003, 0.0)).b);
          float scan = 0.72 + 0.28 * sin(uv.y * 3.14159 * 150.0); float vig = smoothstep(0.75, 0.25, length(vUv - 0.5));
          float fl = 0.93 + 0.07 * sin(time * 47.0); c = (c * tint * 1.4 + band * tint * 0.4 + h(uv * 300.0 + time) * 0.05) * scan * vig * fl;
          gl_FragColor = vec4(c * 0.85, 1.0); }` });
    return new T.Mesh(new T.PlaneGeometry(w, h), mat);
  }
  // a translucent hologram advert: invented glyphs and a cocktail glass, pink and cyan, banded and glitching
  function hologram(w, h) {
    const tex = W.tex(512, 1024, (g, W_, H_) => {
      g.clearRect(0, 0, W_, H_); g.lineCap = 'round'; g.lineJoin = 'round';
      const rnd = NR.rng(808);
      g.strokeStyle = '#ff4ab8'; g.lineWidth = 14; g.shadowColor = '#ff4ab8'; g.shadowBlur = 30;
      g.beginPath(); g.moveTo(96, 220); g.lineTo(416, 220); g.lineTo(256, 470); g.closePath(); g.stroke();
      g.beginPath(); g.moveTo(256, 470); g.lineTo(256, 640); g.moveTo(170, 650); g.lineTo(342, 650); g.stroke();
      g.fillStyle = 'rgba(255,90,190,0.35)'; g.beginPath(); g.moveTo(150, 300); g.lineTo(362, 300); g.lineTo(256, 450); g.closePath(); g.fill();
      g.strokeStyle = '#3ae8ff'; g.shadowColor = '#3ae8ff'; g.lineWidth = 9;
      g.beginPath(); g.arc(340, 250, 34, 0, 7); g.stroke();
      for (let i = 0; i < 4; i++) { const cy = 740 + i * 66, cx = 256; for (let k = 0; k < 3; k++) { const p = () => [cx + (Math.floor(rnd() * 3) - 1) * 26, cy + (Math.floor(rnd() * 3) - 1) * 24]; const [a1, b1] = p(), [a2, b2] = p(); g.beginPath(); g.moveTo(a1, b1); g.lineTo(a2, b2); g.stroke(); } }
      g.strokeStyle = '#ff4ab8'; g.shadowColor = '#ff4ab8'; g.lineWidth = 6; g.strokeRect(40, 40, W_ - 80, H_ - 80);
    });
    const mat = new T.ShaderMaterial({ transparent: true, depthWrite: false, blending: T.AdditiveBlending, side: T.DoubleSide, fog: false,
      uniforms: { map: { value: tex }, time: HZ.time },
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.); }',
      fragmentShader: `uniform sampler2D map; uniform float time; varying vec2 vUv; float h(float n){ return fract(sin(n) * 43758.5453); }
        void main(){ vec2 uv = vUv; float g = step(0.985, h(floor(time * 9.0))) * (h(floor(uv.y * 30.0) + time) - 0.5) * 0.06; uv.x += g;
          vec4 t = texture2D(map, uv); float bands = 0.65 + 0.35 * sin(uv.y * 260.0 - time * 6.0); float roll = 0.75 + 0.25 * smoothstep(0.1, 0.0, abs(fract(uv.y - time * 0.2) - 0.5));
          float fl = 0.85 + 0.15 * sin(time * 31.0) * sin(time * 7.0);
          gl_FragColor = vec4(t.rgb * t.a * bands * roll * fl * 0.55, 1.0); }` });
    return new T.Mesh(new T.PlaneGeometry(w, h), mat);
  }
  // police hover cruiser: dark hull, head lights, alternating red/blue roof lights, a searchlight on the belly
  function cruiserModel() {
    const g = new T.Group(), hullM = new T.MeshLambertMaterial({ color: 0x1a1c20 }), trimM = new T.MeshLambertMaterial({ color: 0x3a3c40 });
    const hull = new T.Mesh(new T.BoxGeometry(1.7, 0.5, 4.2), hullM); g.add(hull);
    const nose = new T.Mesh(new T.CylinderGeometry(0.2, 0.85, 1.2, 8, 1), hullM); nose.rotation.x = Math.PI / 2; nose.scale.set(1, 1, 0.45); nose.position.set(0, -0.02, -2.6); g.add(nose);
    const cab = new T.Mesh(new T.BoxGeometry(1.4, 0.45, 1.8), new T.MeshLambertMaterial({ color: 0x0a1418, emissive: 0x0a2a30 })); cab.position.set(0, 0.42, -0.4); g.add(cab);
    for (const s of [-1, 1]) { const pod = new T.Mesh(new T.CylinderGeometry(0.32, 0.38, 1.4, 10), trimM); pod.rotation.x = Math.PI / 2; pod.position.set(s * 1.05, -0.15, 1.1); g.add(pod); }
    const bar = new T.Mesh(new T.BoxGeometry(1.0, 0.1, 0.25), trimM); bar.position.set(0, 0.7, -0.1); g.add(bar);
    g.userData.red = W.glow(0xff1a10, 1.2, -0.35, 0.78, -0.1, g, 1); g.userData.blue = W.glow(0x2a5aff, 1.2, 0.35, 0.78, -0.1, g, 1);
    for (const s of [-1, 1]) W.glow(0xd8f0ff, 1.4, s * 0.55, 0.0, -2.75, g, 0.9);
    for (const s of [-1, 1]) W.glow(0xff7a20, 0.9, s * 1.05, -0.15, 1.85, g, 0.8);
    g.userData.belly = V3(0, -0.3, -0.6);
    return g;
  }
  NR.env.beam = beam; NR.env.hazeSlab = hazeSlab;

  // ================================================================ OFFICE
  function buildOffice(q) {
    const L = new W.Level('office', 0x0b1a1d, 0.085), S = L.scene; S.background = new T.Color(0x05090a);
    S.userData.expo = 1.2;
    const BACK = -4.6, DESK_Y = 0.786; L.DESK_Y = DESK_Y;
    const DOOR = { x0: -1.5, x1: -0.5, h: 2.2 }, WIN = { x0: 0.15, x1: 1.55, y0: 0.8, y1: 2.45 };
    // door: GLB node when it arrives; the collider is ours (the slice removes it when the door opens)
    const doorProxy = new T.Group(); doorProxy.position.set(DOOR.x0 + 0.01, 0, BACK - 0.045); S.add(doorProxy); L.door = doorProxy;
    const doorCol = { min: V3(DOOR.x0, 0, BACK - 0.08), max: V3(DOOR.x1, DOOR.h, BACK + 0.02), cover: false, step: false, tag: 'door' }; L.boxes.push(doorCol); L.doorCol = doorCol;
    L.boxes.push({ min: V3(WIN.x0, 0, BACK - 0.2), max: V3(WIN.x1, 2.7, BACK + 0.02), cover: false, step: false, tag: 'window' });
    // rain on the glass (real-time), warm city glow behind
    const U = { time: { value: 0 } }; L.U = U;
    const ww = WIN.x1 - WIN.x0, wh = WIN.y1 - WIN.y0, wcx = (WIN.x0 + WIN.x1) / 2, wcy = (WIN.y0 + WIN.y1) / 2;
    const glass = new T.Mesh(new T.PlaneGeometry(ww, wh), new T.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: U,
      vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
      fragmentShader: `uniform float time; varying vec2 vUv; float h(float n){ return fract(sin(n)*43758.5453); }
        void main(){ vec2 uv=vUv*vec2(46.,1.); float col=floor(uv.x); float fx=fract(uv.x);
          float sp=0.25+h(col)*0.6; float y=fract(vUv.y*(1.5+h(col*3.1)*2.)+time*sp+h(col*7.)); float streak=smoothstep(0.86,1.,y)*smoothstep(0.5,0.0,abs(fx-0.5))*step(0.35,h(col*1.7));
          vec2 d=vUv*vec2(70.,110.); vec2 id=floor(d); float drop=step(0.93,h(dot(id,vec2(12.9,78.2))))*smoothstep(0.45,0.1,length(fract(d)-0.5));
          gl_FragColor=vec4(vec3(0.62,0.85,1.0), streak*0.4+drop*0.3+0.04); }` }));
    glass.position.set(wcx, wcy, BACK - 0.1); S.add(glass);
    const city = new T.Group(); S.add(city);
    const cmat = W.basic(0xffffff, { map: cityTex(1024, 1024, 77), fog: false });
    const cb = new T.Mesh(new T.PlaneGeometry(26, 26), cmat); cb.position.set(1.0, 1.0, -22); city.add(cb);
    const sign = new T.Mesh(new T.PlaneGeometry(4.4, 1.1), W.basic(0xffffff, { map: tubeSign('HOTEL ARCADIA', '#ff3018', 1024, 256, 'italic bold 128px Georgia'), transparent: true, blending: T.AdditiveBlending, depthWrite: false, fog: false }));
    sign.position.set(1.4, 3.2, -11.5); sign.rotation.y = -0.2; city.add(sign);
    W.glow(0xff3018, 3.2, 1.4, 3.2, -11.6, city, 0.25);
    const cruiser = new T.Group(); cruiser.position.set(1.1, 2.6, -8); city.add(cruiser);
    cruiser.add(new T.Mesh(new T.BoxGeometry(1.6, 0.25, 0.6), W.basic(0x050403, { fog: false })));
    W.glow(0xff3a2a, 0.35, -0.8, 0, 0.3, cruiser, 0.6); W.glow(0xffb060, 0.45, 0.8, 0, 0.3, cruiser, 0.5);
    // the revolver on the blotter, the fedora on the coat rack, the cigarette in the ashtray
    const gun = NR.fx ? NR.fx.revolverModel(true) : new T.Group(); gun.position.set(-0.12, DESK_Y + 0.025, -0.35); gun.rotation.set(-Math.PI / 2, 0, -0.9); gun.scale.setScalar(1.1); S.add(gun); L.deskGun = gun;
    const hat = NR.fx ? NR.fx.hatModel(0x2a2420) : new T.Group(); hat.position.set(1.78, 1.83, 1.86); hat.rotation.set(0.12, -0.6, 0.05); S.add(hat);
    L.ashTip = V3(0.25, DESK_Y + 0.03, -0.62);
    // real-time light for the characters and the code props (the set itself is baked)
    S.add(new T.HemisphereLight(0x2a4048, 0x0c0806, 0.9));
    const cookie = W.tex(512, 512, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const x0 = w * 0.12, x1 = w * 0.88, y0 = h * 0.08, y1 = h * 0.92;
      const n = 22, sh = (y1 - y0) / n; for (let i = 0; i < n; i++) { g.fillStyle = '#fff'; g.fillRect(x0, y0 + i * sh + sh * 0.42, x1 - x0, sh * 0.5); }
      g.fillStyle = '#000'; g.fillRect(w * 0.5 - 7, y0, 14, y1 - y0); g.fillRect(x0, y0 + (y1 - y0) * 0.5 - 6, x1 - x0, 12); g.filter = 'blur(3px)'; g.drawImage(g.canvas, 0, 0); }, false);
    const spot = new T.SpotLight(0x9fd8ff, 190, 30, 0.24, 0.25, 1.2);
    spot.position.set(1.6, 4.6, -10.0); spot.target.position.set(-0.8, 0.6, -1.0); S.add(spot, spot.target);
    spot.map = cookie; spot.castShadow = true; spot.shadow.mapSize.set(q === 'high' ? 1024 : 512, q === 'high' ? 1024 : 512); spot.shadow.camera.near = 4; spot.shadow.camera.far = 20; spot.shadow.bias = -0.0008;
    const lc = new T.PerspectiveCamera(T.MathUtils.radToDeg(0.24) * 2, 1, 0.5, 30); lc.position.copy(spot.position); lc.lookAt(spot.target.position); lc.updateMatrixWorld(); lc.updateProjectionMatrix();
    L.shaft = { cookie, lightVP: new T.Matrix4().multiplyMatrices(lc.projectionMatrix, lc.matrixWorldInverse), pos: spot.position.clone(), color: 0x8fd4ff, k: 0.08, maxD: 6, yTop: 2.6, zMin: BACK + 0.15 };
    L.spot = spot;
    const lampLight = new T.PointLight(0xffb36a, 2.2, 3.4, 1.8); lampLight.position.set(-0.52, DESK_Y + 0.29, -0.67); S.add(lampLight);
    const velaRim = new T.PointLight(0xffa050, 3.0, 3.0, 1.6); velaRim.position.set(-0.9, 1.5, -0.2); S.add(velaRim);
    const hallLight = new T.PointLight(0x9fe0ff, 5.0, 5.0, 1.6); hallLight.position.set(-1.0, 2.3, BACK - 1.8); S.add(hallLight);
    // backlight: the hall tube floods the corridor haze, so whoever stands in the open door is a silhouette
    beam(S, V3(-1.0, 2.58, BACK - 1.7), V3(-1.0, 0.0, BACK - 1.2), 0.08, 1.0, 0x6ad0ff, 0.5);
    hazeSlab(S, V3(-1.0, 1.25, BACK - 2.4), 2.0, 2.5, 0x3aa8c8, 0.55); hazeSlab(S, V3(-1.0, 1.3, BACK - 1.1), 1.6, 2.4, 0x2a90b0, 0.3);
    W.glow(0xa8e8ff, 1.6, -1.0, 2.56, BACK - 1.7, S, 0.6);
    // warm practicals in the cold room: desk lamp pool, the wall bar
    beam(S, V3(-0.52, DESK_Y + 0.3, -0.67), V3(-0.45, DESK_Y, -0.6), 0.06, 0.38, 0xffa040, 0.08);
    W.glow(0xff8a20, 0.9, 2.06, 1.8, -2.28, S, 0.5);
    // window light through the blinds into the haze (the half-res shaft pass draws the stripes; this adds body)
    hazeSlab(S, V3(0.2, 1.4, -2.0), 4.0, 2.6, 0x1a5060, 0.18);
    // the video-phone on the desk: CRT with scanlines, lighting the desk and faces cold
    const vp = new T.Group(); vp.position.set(0.55, DESK_Y, -0.62); vp.rotation.y = -0.45; S.add(vp);
    const bodyM = new T.MeshLambertMaterial({ color: 0x2a2620 }), darkM = new T.MeshLambertMaterial({ color: 0x0c0b0a });
    const body = new T.Mesh(new T.BoxGeometry(0.3, 0.24, 0.26), bodyM); body.position.set(0, 0.14, -0.02); vp.add(body);
    const hood = new T.Mesh(new T.BoxGeometry(0.32, 0.03, 0.3), darkM); hood.position.set(0, 0.27, 0.0); vp.add(hood);
    const base = new T.Mesh(new T.BoxGeometry(0.34, 0.03, 0.3), darkM); base.position.set(0, 0.015, 0.0); vp.add(base);
    const keys = new T.Mesh(new T.BoxGeometry(0.22, 0.02, 0.08), new T.MeshLambertMaterial({ color: 0x8a7a60 })); keys.position.set(0, 0.04, 0.16); keys.rotation.x = 0.2; vp.add(keys);
    const handset = new T.Mesh(new T.CapsuleGeometry(0.022, 0.16, 4, 8), darkM); handset.rotation.z = Math.PI / 2; handset.position.set(0, 0.29, 0.02); vp.add(handset);
    const scr = crtScreen(0.22, 0.165, (g, w, h) => { g.fillStyle = '#020806'; g.fillRect(0, 0, w, h);
      g.strokeStyle = '#6af0ff'; g.lineWidth = 3; g.beginPath(); g.ellipse(w * 0.5, h * 0.42, w * 0.13, h * 0.22, 0, 0, 7); g.stroke();
      g.beginPath(); g.moveTo(w * 0.28, h * 0.92); g.quadraticCurveTo(w * 0.5, h * 0.55, w * 0.72, h * 0.92); g.stroke();
      g.fillStyle = '#6af0ff'; g.font = 'bold 16px Courier New'; g.fillText('CALL 47-C', 12, 22); g.fillText('\u25CF REC', w - 74, 22);
      g.strokeStyle = '#ffb040'; g.lineWidth = 2; g.beginPath(); for (let x = 0; x < w; x += 4) g.lineTo(x, h - 16 + Math.sin(x * 0.2) * 6 * Math.sin(x * 0.03)); g.stroke(); }, 0x9fe8ff);
    scr.position.set(0, 0.145, 0.111); vp.add(scr);
    const vpLight = new T.PointLight(0x7ad8ff, 1.6, 2.2, 1.8); vpLight.position.set(0.5, DESK_Y + 0.25, -0.4); S.add(vpLight);
    W.glow(0x6ad8ff, 0.45, 0.55, DESK_Y + 0.15, -0.5, S, 0.25);
    const neonSpill = new T.PointLight(0xff2a10, 2.4, 6, 1.6); neonSpill.position.set(0.6, 2.4, BACK + 0.3); S.add(neonSpill);
    L.sideLight = { ambient: 0x9a7868, key: 0xb8e4ff, warm: 0x9a3814 };
    // a floor shadow catcher for 3D characters (the set itself does not take real-time shadows)
    const catcher = new T.Mesh(new T.PlaneGeometry(4.2, 6.8), new T.ShadowMaterial({ opacity: 0.45 })); catcher.rotation.x = -Math.PI / 2; catcher.position.set(0, 0.004, -1.2); catcher.receiveShadow = true; S.add(catcher);
    if (NR.fx) { S.add(NR.fx.smoke(160, L.ashTip, { rise: 0.9, spread: 0.08, size: 26, alpha: 0.2, life: 5, tint: 0xd8c8b8 }, L.shaft)); S.add(NR.fx.smoke(70, V3(0, 1.0, -2.2), { rise: 1.6, spread: 1.6, size: 300, alpha: 0.04, life: 30, tint: 0x8ab8c8 }, L.shaft)); }
    let blades = null;
    L.updaters.push((dt, t) => { U.time.value = t; HZ.time.value = t; { const P = NR.player; if (P.vm) P.vm.cigDefault = !!(P.smoked > 0 || P.forceCig || P.litT > 0); } /* no cigarette in hand until Vela lights it */ vpLight.intensity = 1.6 * (0.9 + 0.1 * Math.sin(t * 47)); if (blades) blades.rotation.y = t * 0.9; cruiser.position.x = 1.6 - ((t * 0.35) % 5.0); cruiser.position.y = 2.6 + Math.sin(t * 0.8) * 0.1; neonSpill.intensity = 2.4 * (Math.sin(t * 1.3) > 0.97 ? 0.3 : 1); });
    L.spawn = { pos: V3(0.0, 0, 1.6), yaw: 0 };
    L.exitDoor = { x: -1.0, z: BACK - 0.3 };
    L.finish();
    attach(L, 'office', (root) => {
      const d = node(root, 'door'); if (d) { doorProxy.position.copy(d.position); d.position.set(0, 0, 0); doorProxy.add(d); }
      blades = node(root, 'fan_blades');
    }, { lm: 4.6, baked: 4.6 });
    return L;
  }

  // ---------------------------------------------------------------- shared outdoor pieces
  function warmRain(L, q) {
    if (!NR.fx) return;
    L.rain = NR.fx.rain(q === 'high' ? 2600 : 1600);
    L.rain.material.fragmentShader = L.rain.material.fragmentShader.replace('vec4(0.72,0.8,0.86, a)', 'vec4(0.95,0.74,0.52, a*0.8)');
    L.scene.add(L.rain); L.updaters.push((dt, t) => { L.rain.material.uniforms.time.value = t; });
  }
  // wet ground: procedural puddles (world xz) turn the baked asphalt into a dark mirror over the reflected set below
  function wetGround(mat, opts = {}) {
    mat.transparent = true; mat.depthWrite = true;
    mat.onBeforeCompile = (s) => {
      s.uniforms.puddleK = { value: opts.k || 0.78 };
      s.vertexShader = s.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWp;').replace('#include <project_vertex>', '#include <project_vertex>\nvWp = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      s.fragmentShader = s.fragmentShader.replace('#include <common>', `#include <common>
        varying vec3 vWp; uniform float puddleK;
        float ph(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float pn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.-2.*f); return mix(mix(ph(i), ph(i+vec2(1,0)), f.x), mix(ph(i+vec2(0,1)), ph(i+vec2(1,1)), f.x), f.y); }
        float puddle(vec2 p){ float n = pn(p*0.45)*0.55 + pn(p*1.1+7.3)*0.3 + pn(p*3.1-2.1)*0.15; return smoothstep(0.585, 0.62, n); }`)
        .replace('#include <opaque_fragment>', `float pm = puddle(vWp.xz) * puddleK; float edge = max(0.0, 1.0 - abs(vWp.x) / 3.0);
          pm *= smoothstep(0.0, 0.25, edge) * 0.6 + 0.4;
          outgoingLight *= 1.0 - pm * 0.55; diffuseColor.a = 1.0 - pm;
          #include <opaque_fragment>`);
    };
    mat.customProgramCacheKey = () => 'wetGround'; mat.needsUpdate = true; mat.userData.wet = true;
  }
  // a mirrored copy of the lit set under y = 0: seen only through the transparent puddles
  function mirror(L, objs, dim) {
    const g = new T.Group(); g.scale.y = -1; L.scene.add(g);
    for (const o of objs) {
      const c = o.clone(true); c.traverse(m => { if (m.isMesh) { const mm = m.material.clone(); if (mm.color && !/^NEON/.test(mm.name)) mm.color.multiplyScalar(dim); mm.fog = true; m.material = mm; } });
      c.position.copy(o.getWorldPosition(new T.Vector3())); c.quaternion.copy(o.getWorldQuaternion(new T.Quaternion())); g.add(c);
    }
    return g;
  }

  // ================================================================ ALLEY
  function buildAlley(q) {
    const L = new W.Level('alley', 0x0c1c20, 0.05), S = L.scene; L.outdoor = true; S.userData.expo = 1.25;
    S.background = new T.Color(0x060a0c);
    // the skyline beyond the street mouth (sodium windows, distant neon, haze)
    const sky = new T.Mesh(new T.PlaneGeometry(140, 60), W.basic(0xffffff, { map: cityTex(2048, 1024, 31, { signs: [['HOTEL', '#ff3a1e', 0.36, 0.52], ['EAT', '#2affc8', 0.6, 0.6], ['BAR', '#ff8a1a', 0.47, 0.66], ['DANCING', '#ff2a6a', 0.7, 0.48]] }), fog: false }));
    sky.position.set(0, 22, -95); S.add(sky);
    const skyGlow = new T.Mesh(new T.PlaneGeometry(40, 30), W.basic(0x6a2a0a, { transparent: true, opacity: 0.18, blending: T.AdditiveBlending, depthWrite: false, fog: false }));
    skyGlow.position.set(0, 18, -42); S.add(skyGlow);
    // real-time light for the characters (the set is baked): neon spill, door lamps, the sodium lamp over Miles
    S.add(new T.HemisphereLight(0x5a3a2a, 0x140c08, 0.9));
    const pl = (c, i, x, y, z, d) => { const p = new T.PointLight(c, i, d || 9, 1.6); p.position.set(x, y, z); S.add(p); return p; };
    const signs = [pl(0xff2a14, 40, -2.4, 4.4, -7, 11), pl(0x20ffc0, 45, 2.4, 4.4, -14, 12), pl(0xff8a20, 40, -2.4, 3.6, -24, 11), pl(0xff2a6a, 34, 2.4, 5.2, -30, 11)];
    for (const [x, z] of [[-2.95, -9], [2.95, -17], [-2.95, -27]]) { pl(0xffa860, 10, x, 2.6, z, 6); W.glow(0xff9a40, 0.4, x, 2.62, z, S, 0.4); beam(S, V3(x, 2.58, z), V3(x * 0.72, 0, z), 0.05, 0.9, 0xff9a40, 0.3); }
    // haze: cold teal air with warm and neon pools; beams from the practicals
    for (const [x, y, z, c, a] of [[0, 3.0, -8, 0x1a6878, 0.26], [0, 3.2, -16, 0x0a7068, 0.22], [0, 3.0, -24, 0x1a5868, 0.22], [0, 3.4, -31, 0x601040, 0.18], [0, 4.0, -40, 0x2a4a58, 0.3]]) hazeSlab(S, V3(x, y, z), 6.4, 6.0, c, a);
    beam(S, V3(2.1, 3.42, -36.6), V3(0.6, 0, -34.8), 0.12, 2.4, 0xff8a20, 0.3);
    for (const z of [-2.3, -3.15, -4.0]) { W.glow(0xff5010, 0.55, 1.6, 2.08, z, S, 0.55); beam(S, V3(1.6, 2.0, z), V3(1.4, 0.0, z), 0.04, 0.5, 0xff6020, 0.12); }
    // the hologram advert over the street mouth (translucent, banded, glitching)
    const holo = hologram(7, 14); holo.position.set(1.0, 11, -47); S.add(holo);
    W.glow(0xff4ab8, 12, 1.0, 11, -47.2, S, 0.12); W.glow(0x3ae8ff, 6, 1.6, 13, -47.1, S, 0.08);
    const holoLight = pl(0xff4ab8, 30, 0.5, 8, -40, 16);
    // police hover cruiser crossing overhead, red/blue roof lights, a searchlight sweeping the alley
    const cop = cruiserModel(); S.add(cop);
    const copBeam = beam(S, V3(0, 12, -14), V3(0, 0, -14), 0.15, 2.2, 0xd8f0ff, 0.55);
    const copSpot = new T.SpotLight(0xd0ecff, 0, 30, 0.16, 0.5, 1.2); S.add(copSpot, copSpot.target);
    const copRB = pl(0xff2010, 0, 0, 12, -14, 18);
    const cookie = W.tex(256, 256, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const r = g.createRadialGradient(w / 2, h / 2, 4, w / 2, h / 2, w / 2); r.addColorStop(0, '#fff'); r.addColorStop(0.7, '#aaa'); r.addColorStop(1, '#000'); g.fillStyle = r; g.fillRect(0, 0, w, h); }, false);
    const spot = new T.SpotLight(0xff9030, 260, 18, 0.62, 0.4, 1.4);
    spot.position.set(2.1, 3.45, -36.6); spot.target.position.set(0.4, 0, -34.6); S.add(spot, spot.target);
    spot.map = cookie; spot.castShadow = true; spot.shadow.mapSize.set(q === 'high' ? 1024 : 512, q === 'high' ? 1024 : 512); spot.shadow.camera.near = 0.5; spot.shadow.camera.far = 18; spot.shadow.bias = -0.0008;
    const lc = new T.PerspectiveCamera(T.MathUtils.radToDeg(0.62) * 2, 1, 0.5, 30); lc.position.copy(spot.position); lc.lookAt(spot.target.position); lc.updateMatrixWorld(); lc.updateProjectionMatrix();
    L.shaft = { cookie, lightVP: new T.Matrix4().multiplyMatrices(lc.projectionMatrix, lc.matrixWorldInverse), pos: spot.position.clone(), color: 0xffa040, k: 0.13, maxD: 30, yTop: 3.6 }; L.spot = spot;
    W.glow(0xffa040, 1.6, 2.1, 3.42, -36.6, S, 0.9); W.glow(0xffa040, 1.3, 2.1, -3.42, -36.6, S, 0.35);
    L.sideLight = { ambient: 0x5a4a44, key: 0xffa040, warm: 0x401808 };
    // glows around the blade signs (+ their reflections)
    const halos = [];
    for (const [c, x, y, z, s] of [[0xff2a14, -2.6, 4.5, -7, 3.2], [0x20ffc0, 2.6, 4.55, -14, 3.6], [0xff8a20, -2.6, 3.75, -24, 2.4], [0xff2a6a, 2.6, 5.3, -30, 3.2]]) {
      halos.push(W.glow(c, s, x, y, z, S, 0.28)); W.glow(c, s * 0.8, x, -y, z, S, 0.12);
    }
    warmRain(L, q);
    if (NR.fx) {
      S.add(NR.fx.smoke(46, V3(0.4, 0.05, -19), { rise: 2.6, spread: 0.45, size: 160, alpha: 0.035, life: 6, tint: 0xb8a898 }, L.shaft));
      S.add(NR.fx.smoke(24, V3(-2.9, 0.4, -24.6), { rise: 1.8, spread: 0.3, size: 140, alpha: 0.03, life: 5, tint: 0xa89888 }, L.shaft));
      S.add(NR.fx.smoke(30, V3(2.6, 1.3, -3.9), { rise: 1.4, spread: 0.2, size: 120, alpha: 0.05, life: 4, tint: 0xd8c0a8 }, L.shaft)); // steam off the noodle pot
    }
    const _a = V3(0, 0, 0), _b = V3(0, 0, 0);
    L.updaters.push((dt, t) => {
      HZ.time.value = t; holoLight.intensity = 30 * (0.8 + 0.2 * Math.sin(t * 31) * Math.sin(t * 7));
      const ph = (t % 28) / 28, on = ph < 0.62; cop.visible = on; copBeam.visible = on;
      if (on) { const k = ph / 0.62; cop.position.set(-22 + 44 * k, 12.5 + Math.sin(t * 0.7) * 0.4, -12 - 8 * Math.sin(k * Math.PI)); cop.rotation.set(0.04, -Math.PI / 2 + 0.25 * Math.sin(k * Math.PI), -0.08 * Math.cos(k * 6.28));
        _a.copy(cop.position).add(V3(0, -0.4, 0)); _b.set(Math.sin(t * 0.9) * 2.2, 0, cop.position.z - 6 + Math.sin(t * 0.6) * 9); aimBeam(copBeam, _a, _b);
        copSpot.position.copy(_a); copSpot.target.position.copy(_b); copSpot.intensity = 320 * Math.min(1, Math.min(k, 1 - k) * 8);
        const rb = Math.sin(t * 9) > 0; cop.userData.red.material.opacity = rb ? 1 : 0.15; cop.userData.blue.material.opacity = rb ? 0.15 : 1;
        copRB.position.copy(cop.position); copRB.color.setHex(rb ? 0xff2010 : 0x2a5aff); copRB.intensity = 40 * Math.min(1, Math.min(k, 1 - k) * 8); }
      else { copSpot.intensity = 0; copRB.intensity = 0; }
    });
    L.updaters.push((dt, t) => { for (let i = 0; i < signs.length; i++) { const k = (L.neonK && L.neonK[i] != null) ? L.neonK[i] : 1; signs[i].intensity = [40, 45, 40, 34][i] * k; halos[i].material.opacity = 0.28 * k; } });
    L.spawn = { pos: V3(0, 0, 0.5), yaw: 0 };
    L.bodyPos = V3(0.2, 0, -34.5);
    L.finish();
    L.updaters.push(() => { if (NR.player.vm) NR.player.vm.cigDefault = true; });
    attach(L, 'alley', (root) => {
      let wet = null; root.traverse(o => { if (o.isMesh && /WET/.test(o.material.name)) wet = o; });
      if (wet) wetGround(wet.material, { k: 0.62 });
      const props = node(root, 'PROPS'), neon = node(root, 'NEON');
      mirror(L, [props, neon].filter(Boolean), 0.4);
      // neon flicker drives the matching real-time spill: red, teal, orange, pink tubes by material name
      const order = ['red', 'teal', 'orange', 'pink']; L.neonK = [1, 1, 1, 1];
      L.updaters.push(() => { for (const n of L.neon) { const i = order.findIndex(c => n.mat.name.endsWith(c)); if (i >= 0) L.neonK[i] = n.mat.color.r / Math.max(1e-3, n.mat.userData.base.r) || 1; } });
      for (const n of L.neon) if (/red$/.test(n.mat.name)) n.mesh.userData.flicker = 0.18;
    }, { lm: 3, baked: 3.2, neon: 0.5 });
    return L;
  }

  // ================================================================ THE BLUE ORCHID
  function buildClub(q) {
    const L = new W.Level('club', 0x0c1a1e, 0.05), S = L.scene; S.userData.expo = 1.3; S.background = new T.Color(0x05090a);
    const RH = 4.2;
    // real-time light for the characters: warm practicals, the blue neon over the stage, the stage spot
    S.add(new T.HemisphereLight(0x6a4a3a, 0x2a1810, 1.6));
    const pl = (c, i, x, y, z, d) => { const p = new T.PointLight(c, i, d || 9, 1.6); p.position.set(x, y, z); S.add(p); return p; };
    pl(0xffa050, 34, -6.6, 2.8, -9, 10); pl(0xff9a50, 34, 6.2, 2.0, -8.5, 11); pl(0xffb070, 16, 7.2, 2.1, -19.2, 6);
    for (const [x, z] of [[-2, -6], [2.5, -10], [-1, -14]]) pl(0xffb070, 18, x, 3.3, z, 9);
    const neonLight = pl(0x3070ff, 26, -1.5, 3.3, -21.5, 10);
    for (const [x, z] of [[-2, -6], [2.5, -10], [-1, -14]]) W.glow(0xffb060, 1.0, x, RH - 0.9, z, S, 0.18);
    W.glow(0xff2a80, 1.6, 2.35, 3.6, -23.2, S, 0.25); W.glow(0xff2a14, 2.6, -7.8, 3.15, -9, S, 0.22);
    const cookie = W.tex(256, 256, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const r = g.createRadialGradient(w / 2, h / 2, 2, w / 2, h / 2, w * 0.42); r.addColorStop(0, '#fff'); r.addColorStop(0.7, '#ddd'); r.addColorStop(1, '#000'); g.fillStyle = r; g.fillRect(0, 0, w, h); }, false);
    const spot = new T.SpotLight(0xffd0a0, 700, 30, 0.32, 0.25, 1.2);
    spot.position.set(1.0, RH - 0.3, -11.5); spot.target.position.set(-1.5, 0.6, -19.5); S.add(spot, spot.target);
    spot.map = cookie; spot.castShadow = true; spot.shadow.mapSize.set(q === 'high' ? 1024 : 512, q === 'high' ? 1024 : 512); spot.shadow.camera.near = 0.5; spot.shadow.camera.far = 30; spot.shadow.bias = -0.0008;
    const lc = new T.PerspectiveCamera(T.MathUtils.radToDeg(0.32) * 2, 1, 0.5, 30); lc.position.copy(spot.position); lc.lookAt(spot.target.position); lc.updateMatrixWorld(); lc.updateProjectionMatrix();
    L.shaft = { cookie, lightVP: new T.Matrix4().multiplyMatrices(lc.projectionMatrix, lc.matrixWorldInverse), pos: spot.position.clone(), color: 0xe8c8a8, k: 0.11, maxD: 18, yTop: 4.1 }; L.spot = spot;
    W.glow(0xffd8a8, 0.8, 1.0, RH - 0.32, -11.5, S);
    L.sideLight = { ambient: 0x5a4438, key: 0xffd0a0, warm: 0x5a2010 };
    if (NR.fx) S.add(NR.fx.smoke(110, V3(-0.5, 0.8, -12), { rise: 2.6, spread: 4.5, size: 380, alpha: 0.02, life: 34, tint: 0x7a9aa8 }, L.shaft));
    L.signLight = new T.PointLight(0xff2a14, 0, 18, 1.2); L.signLight.position.set(0.6, 3.8, -10.5); S.add(L.signLight); // the title sign's red cast (landing menu)
    // haze + beams: chandeliers and sconces pour warm light down through cold smoke; the stage glows blue
    for (const [x, z] of [[-2, -6], [2.5, -10], [-1, -14]]) beam(S, V3(x, RH - 0.95, z), V3(x, 0, z), 0.3, 2.0, 0xffa050, 0.16);
    for (const [x, z, s] of [[-8, -3, 1], [-8, -16, 1], [-8, -19.5, 1], [8, -2.5, -1], [8, -15.6, -1]]) { beam(S, V3(x + s * 0.15, 2.65, z), V3(x + s * 0.3, RH, z), 0.05, 0.5, 0xffa050, 0.25); beam(S, V3(x + s * 0.15, 2.4, z), V3(x + s * 0.4, 0.9, z), 0.05, 0.4, 0xff9040, 0.18); }
    for (const z of [-4.5, -8.5, -12.5]) W.glow(0xff9a40, 0.9, 7.82, 2.42, z - 1.1, S, 0.35);
    for (const [x, y, z, c, a] of [[-1.5, 2.4, -20.5, 0x1a40a0, 0.3], [0, 2.6, -12, 0x0e3a44, 0.22], [-5.5, 2.4, -9, 0x5a2a10, 0.18], [5.5, 2.2, -9, 0x5a2a10, 0.16]]) hazeSlab(S, V3(x, y, z), 7.0, 4.4, c, a);
    // the entrance: cold street light pours through the door glass and transom; gunmen in the door are silhouettes
    const dglow = new T.MeshBasicMaterial({ color: new T.Color(0.3, 0.55, 0.7), fog: false });
    for (const x of [-0.46, 0.46]) { const p = new T.Mesh(new T.CircleGeometry(0.16, 24), dglow); p.position.set(x, 1.55, 1.015); p.rotation.y = Math.PI; S.add(p); W.glow(0x8fd8ff, 0.9, x, 1.55, 1.0, S, 0.3); } // light through the porthole glass
    const tr = new T.Mesh(new T.PlaneGeometry(1.9, 0.3), dglow); tr.position.set(0, 2.72, 1.04); tr.rotation.y = Math.PI; S.add(tr);
    beam(S, V3(0, 2.7, 1.0), V3(0, 0, -3.5), 0.5, 2.4, 0x7ad0ff, 0.28); beam(S, V3(0, 1.5, 1.0), V3(0, 0, -2.2), 0.6, 1.4, 0x7ad0ff, 0.18);
    hazeSlab(S, V3(0, 1.4, 0.4), 3.4, 2.8, 0x2a90b0, 0.4); W.glow(0x9fe0ff, 3.0, 0, 2.0, 0.9, S, 0.22);
    pl(0x8fd8ff, 22, 0, 2.2, 0.2, 7);
    L.updaters.push((dt, t) => { HZ.time.value = t; neonLight.intensity = 26 * (Math.sin(t * 0.9) > 0.985 ? 0.4 : 1); });
    L.spawn = { pos: V3(0, 0, -0.6), yaw: 0 };
    L.doloresPos = V3(5.6, 0, -16.6);
    L.finish();
    L.updaters.push(() => { if (NR.player.vm) NR.player.vm.cigDefault = true; });
    attach(L, 'club', null, { lm: 8, baked: 7, neon: 0.034 });
    return L;
  }

  // ---------------------------------------------------------------- install (only for levels whose GLB exists)
  if (ON) {
    const builders = { office: buildOffice, alley: buildAlley, club: buildClub };
    NR.env.built = Object.keys(builders);
    const orig = Object.assign({}, W.build);
    for (const name of Object.keys(builders)) W.build[name] = builders[name];
    NR.env.orig = orig;
    // fetch order: the club (title backdrop), then the office (first beat), then the alley
    get('club').then(() => get('office')).then(() => get('alley'));
  }
})();
