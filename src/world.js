// NEON RAIN world: grey-box level builder (merged static boxes, AABB colliders, cover points), ray/LOS queries, and the
// three slice levels: Harrow's office, the alley behind Kestrel Street, the Blue Orchid club.
(function () {
  const T = THREE;
  const V3 = (x, y, z) => new T.Vector3(x, y, z);

  // ---------------------------------------------------------------- helpers
  function tex(w, h, draw, srgb = true, rep) {
    const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
    const t = new T.CanvasTexture(c); if (srgb) t.colorSpace = T.SRGBColorSpace; t.anisotropy = 4;
    if (rep) { t.wrapS = t.wrapT = T.RepeatWrapping; }
    return t;
  }
  const rnd = NR.rng(1234);
  function lam(color, map, extra) { const m = new T.MeshLambertMaterial(Object.assign({ color }, map ? { map } : {}, extra || {})); return m; }
  function stdm(color, rough, metal, extra) { return new T.MeshStandardMaterial(Object.assign({ color, roughness: rough, metalness: metal || 0 }, extra || {})); }
  function basic(color, extra) { return new T.MeshBasicMaterial(Object.assign({ color }, extra || {})); }
  const glowTex = tex(128, 128, (g, w, h) => { const r = g.createRadialGradient(64, 64, 0, 64, 64, 64); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.25, 'rgba(255,255,255,0.45)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, w, h); });
  function glow(color, s, x, y, z, parent, opacity = 1) {
    const sp = new T.Sprite(new T.SpriteMaterial({ map: glowTex, color, blending: T.AdditiveBlending, depthWrite: false, fog: false, transparent: true, opacity }));
    sp.scale.set(s, s, 1); sp.position.set(x, y, z); if (parent) parent.add(sp); return sp;
  }
  function neonTex(text, color, glowC, w = 1024, h = 256, font = 'bold 150px Georgia') {
    return tex(w, h, (g) => { g.clearRect(0, 0, w, h); g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.shadowColor = glowC; g.shadowBlur = 40; g.fillStyle = color; g.fillText(text, w / 2, h / 2); g.shadowBlur = 12; g.fillStyle = '#fff6e8'; g.globalAlpha = 0.7; g.fillText(text, w / 2, h / 2); });
  }
  function neon(text, color, glowC, x, y, z, ry, sw, parent, font) {
    const t = neonTex(text, color, glowC, 1024, 256, font);
    const m = new T.Mesh(new T.PlaneGeometry(sw, sw / 4), basic(0xffffff, { map: t, transparent: true, blending: T.AdditiveBlending, depthWrite: false, fog: false }));
    m.position.set(x, y, z); m.rotation.y = ry || 0; parent.add(m); return m;
  }
  // box geometry with metre-scaled UVs (texture repeats once per `tile` metres)
  function boxGeo(w, h, d, tile) {
    const g = new T.BoxGeometry(w, h, d); if (!tile) return g;
    const uv = g.attributes.uv; const dims = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
    for (let f = 0; f < 6; f++) for (let i = 0; i < 4; i++) { const k = f * 4 + i; uv.setXY(k, uv.getX(k) * dims[f][0] / tile, uv.getY(k) * dims[f][1] / tile); }
    return g;
  }
  function mergeGeos(geos) {
    let nv = 0, ni = 0; for (const g of geos) { nv += g.attributes.position.count; ni += g.index ? g.index.count : g.attributes.position.count; }
    const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), idx = new Uint32Array(ni);
    let vo = 0, io = 0;
    for (const g of geos) {
      const p = g.attributes.position, n = g.attributes.normal, u = g.attributes.uv, c = p.count;
      pos.set(p.array, vo * 3); nor.set(n.array, vo * 3); if (u) uv.set(u.array, vo * 2);
      if (g.index) { const a = g.index.array; for (let i = 0; i < a.length; i++) idx[io + i] = a[i] + vo; io += a.length; }
      else { for (let i = 0; i < c; i++) idx[io + i] = vo + i; io += c; }
      vo += c;
    }
    const m = new T.BufferGeometry(); m.setAttribute('position', new T.BufferAttribute(pos, 3)); m.setAttribute('normal', new T.BufferAttribute(nor, 3)); m.setAttribute('uv', new T.BufferAttribute(uv, 2)); m.setIndex(new T.BufferAttribute(idx, 1));
    m.computeBoundingSphere(); m.computeBoundingBox(); return m;
  }

  // ---------------------------------------------------------------- level object
  class Level {
    constructor(name, fogColor, fogDensity) {
      this.name = name; this.scene = new T.Scene(); this.scene.background = new T.Color(0); this.scene.fog = new T.FogExp2(fogColor, fogDensity);
      this.scene.userData.level = this;
      this.boxes = []; this.buckets = new Map(); this.covers = []; this.interact = []; this.clues = []; this.triggers = []; this.updaters = []; this.spawn = { pos: V3(0, 0, 0), yaw: 0 };
      this.shaft = null; this.outdoor = false; this.decor = new T.Group(); this.scene.add(this.decor);
    }
    // static box: merged into one mesh per material; solid boxes also collide, block bullets and can give cover
    box(cx, cy, cz, w, h, d, mat, o = {}) {
      if (!mat) { this.boxes.push({ min: V3(cx - w / 2, cy - h / 2, cz - d / 2), max: V3(cx + w / 2, cy + h / 2, cz + d / 2), cover: !!o.cover, step: !!o.step, tag: o.tag || '' }); return null; } // collider only
      const g = boxGeo(w, h, d, mat.userData.tile); g.translate(cx, cy, cz);
      if (o.ry) { g.translate(-cx, -cy, -cz); g.rotateY(o.ry); g.translate(cx, cy, cz); }
      const key = mat.uuid + (o.noShadow ? 'n' : '') + (o.noCast ? 'c' : '');
      if (!this.buckets.has(key)) this.buckets.set(key, { mat, geos: [], cast: !o.noCast && !o.noShadow, recv: !o.noShadow });
      this.buckets.get(key).geos.push(g);
      if (o.solid !== false) {
        let hw = w / 2, hd = d / 2; if (o.ry && Math.abs(Math.sin(o.ry)) > 0.7) { hw = d / 2; hd = w / 2; }
        const b = { min: V3(cx - hw, cy - h / 2, cz - hd), max: V3(cx + hw, cy + h / 2, cz + hd), cover: !!o.cover, step: !!o.step, tag: o.tag || '' };
        this.boxes.push(b);
      }
      return g;
    }
    add(obj, shadows) { if (shadows) obj.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } }); this.decor.add(obj); return obj; }
    finish() {
      for (const b of this.buckets.values()) { const m = new T.Mesh(mergeGeos(b.geos), b.mat); m.castShadow = b.cast; m.receiveShadow = b.recv; m.matrixAutoUpdate = false; this.scene.add(m); for (const g of b.geos) g.dispose(); }
      this.buckets.clear();
      // cover points: along each side of low/tall cover boxes, 0.55 m out
      for (const b of this.boxes) {
        if (!b.cover) continue;
        const h = b.max.y - b.min.y, low = h < 1.5, cx = (b.min.x + b.max.x) / 2, cz = (b.min.z + b.max.z) / 2;
        const sides = [[1, 0], [-1, 0], [0, 1], [0, -1]];
        for (const [nx, nz] of sides) {
          const along = nx ? (b.max.z - b.min.z) : (b.max.x - b.min.x), n = Math.max(1, Math.round(along / 1.1));
          for (let i = 0; i < n; i++) {
            const f = (i + 0.5) / n - 0.5;
            const x = nx ? (nx > 0 ? b.max.x + 0.5 : b.min.x - 0.5) : cx + f * along, z = nz ? (nz > 0 ? b.max.z + 0.5 : b.min.z - 0.5) : cz + f * along;
            if (this.blockedAt(x, z, 0.3)) continue;
            this.covers.push({ pos: V3(x, 0, z), n: V3(nx, 0, nz), box: b, low, taken: null });
          }
        }
      }
    }
    blockedAt(x, z, r) { for (const b of this.boxes) { if (b.step || b.min.y > 1.6 || b.max.y < 0.2) continue; if (x > b.min.x - r && x < b.max.x + r && z > b.min.z - r && z < b.max.z + r) return true; } return false; }
    // circle-vs-AABB slide; returns ground height under the mover (step boxes)
    collide(p, r, feetY, canStep) {
      let ground = 0;
      for (let it = 0; it < 2; it++) for (const b of this.boxes) {
        if (b.max.y <= feetY + 0.02 || b.min.y > feetY + 1.7) continue;
        if (canStep && b.step && b.max.y <= feetY + 0.66) continue;
        const qx = NR.clamp(p.x, b.min.x, b.max.x), qz = NR.clamp(p.z, b.min.z, b.max.z);
        let dx = p.x - qx, dz = p.z - qz; const d2 = dx * dx + dz * dz;
        if (d2 >= r * r) continue;
        if (d2 > 1e-8) { const d = Math.sqrt(d2), k = (r - d) / d; p.x += dx * k; p.z += dz * k; }
        else { // centre inside the box: push out along the shallowest axis
          const ex = [p.x - b.min.x + r, b.max.x - p.x + r, p.z - b.min.z + r, b.max.z - p.z + r]; const m = Math.min(...ex);
          if (m === ex[0]) p.x = b.min.x - r; else if (m === ex[1]) p.x = b.max.x + r; else if (m === ex[2]) p.z = b.min.z - r; else p.z = b.max.z + r;
        }
      }
      if (canStep) for (const b of this.boxes) { if (b.step && p.x > b.min.x - 0.05 && p.x < b.max.x + 0.05 && p.z > b.min.z - 0.05 && p.z < b.max.z + 0.05 && b.max.y <= feetY + 0.66) ground = Math.max(ground, b.max.y); }
      return ground;
    }
    // ray vs solid boxes: {t, point, normal, box} or null
    ray(o, d, maxT) {
      let best = maxT, hit = null, bn = 0;
      for (const b of this.boxes) {
        let t0 = 0, t1 = best, ax = -1;
        for (let a = 0; a < 3; a++) {
          const oa = a === 0 ? o.x : a === 1 ? o.y : o.z, da = a === 0 ? d.x : a === 1 ? d.y : d.z;
          const mn = a === 0 ? b.min.x : a === 1 ? b.min.y : b.min.z, mx = a === 0 ? b.max.x : a === 1 ? b.max.y : b.max.z;
          if (Math.abs(da) < 1e-9) { if (oa < mn || oa > mx) { t0 = 1; t1 = 0; break; } continue; }
          let ta = (mn - oa) / da, tb = (mx - oa) / da, s = -1; if (ta > tb) { const q = ta; ta = tb; tb = q; s = 1; }
          if (ta > t0) { t0 = ta; ax = a * 2 + (s > 0 ? 1 : 0); }
          if (tb < t1) t1 = tb; if (t0 > t1) break;
        }
        if (t0 <= t1 && ax >= 0 && t0 < best) { best = t0; hit = b; bn = ax; }
      }
      if (!hit) return null;
      const n = V3(0, 0, 0); const a = bn >> 1, sgn = (bn & 1) ? 1 : -1;
      // entering face normal points against the ray on that axis
      if (a === 0) n.x = d.x > 0 ? -1 : 1; else if (a === 1) n.y = d.y > 0 ? -1 : 1; else n.z = d.z > 0 ? -1 : 1;
      void sgn;
      return { t: best, point: o.clone().addScaledVector(d, best), normal: n, box: hit };
    }
    los(a, b) { const d = b.clone().sub(a), L = d.length(); if (L < 1e-4) return true; d.divideScalar(L); const h = this.ray(a, d, L - 0.05); return !h; }
    update(dt, t) { for (const f of this.updaters) f(dt, t); }
  }

  // ---------------------------------------------------------------- shared textures
  const TX = {};
  function textures() {
    if (TX.ok) return TX;
    TX.wall = tex(512, 512, (g, w, h) => { g.fillStyle = '#4a4238'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 9000; i++) { g.fillStyle = `rgba(${20 + rnd() * 40 | 0},${18 + rnd() * 30 | 0},${14 + rnd() * 20 | 0},${rnd() * 0.12})`; g.fillRect(rnd() * w, rnd() * h, 2 + rnd() * 6, 2 + rnd() * 10); }
      for (let x = 0; x < w; x += 64) { g.fillStyle = 'rgba(0,0,0,0.10)'; g.fillRect(x, 0, 3, h); } }, true, true);
    TX.floor = tex(512, 512, (g, w, h) => { g.fillStyle = '#3a2a1e'; g.fillRect(0, 0, w, h);
      for (let y = 0; y < h; y += 32) { g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(0, y, w, 2); for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(${70 + rnd() * 40 | 0},${45 + rnd() * 25 | 0},30,0.12)`; g.fillRect(rnd() * w, y + 2, 40 + rnd() * 120, 28); } } }, true, true);
    TX.wood = tex(512, 256, (g, w, h) => { g.fillStyle = '#3b2214'; g.fillRect(0, 0, w, h); for (let i = 0; i < 220; i++) { g.strokeStyle = `rgba(${15 + rnd() * 30 | 0},${8 + rnd() * 12 | 0},4,${0.2 + rnd() * 0.3})`; g.lineWidth = 1 + rnd() * 2; g.beginPath(); const y = rnd() * h; g.moveTo(0, y); g.bezierCurveTo(w * 0.3, y + rnd() * 10 - 5, w * 0.6, y + rnd() * 10 - 5, w, y + rnd() * 8 - 4); g.stroke(); } }, true, true);
    TX.brick = tex(512, 512, (g, w, h) => { g.fillStyle = '#2a1d18'; g.fillRect(0, 0, w, h);
      for (let y = 0, r = 0; y < h; y += 32, r++) for (let x = -(r % 2) * 32; x < w; x += 64) { const v = 80 + rnd() * 50 | 0; g.fillStyle = `rgb(${v + 12},${v * 0.8 | 0},${v * 0.72 | 0})`; g.fillRect(x + 2, y + 2, 60, 28); }
      for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(0,0,0,${rnd() * 0.25})`; g.fillRect(rnd() * w, rnd() * h, 2 + rnd() * 5, 2 + rnd() * 30); } }, true, true);
    TX.asphalt = tex(512, 512, (g, w, h) => { g.fillStyle = '#34363a'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 14000; i++) { const v = 40 + rnd() * 50 | 0; g.fillStyle = `rgba(${v},${v},${v + 4},0.5)`; g.fillRect(rnd() * w, rnd() * h, 2, 2); }
      for (let i = 0; i < 9; i++) { g.fillStyle = 'rgba(16,18,20,0.5)'; g.beginPath(); g.ellipse(rnd() * w, rnd() * h, 30 + rnd() * 70, 14 + rnd() * 30, rnd() * 3, 0, 7); g.fill(); } }, true, true);
    TX.puddleRough = tex(512, 512, (g, w, h) => { g.fillStyle = '#b0b0b0'; g.fillRect(0, 0, w, h);
      for (let i = 0; i < 12; i++) { g.fillStyle = '#101010'; g.beginPath(); g.ellipse(rnd() * w, rnd() * h, 40 + rnd() * 80, 18 + rnd() * 36, rnd() * 3, 0, 7); g.fill(); } }, false, true);
    TX.carpet = tex(256, 256, (g, w, h) => { g.fillStyle = '#4e4240'; g.fillRect(0, 0, w, h); g.strokeStyle = 'rgba(160,110,60,0.25)'; g.lineWidth = 2;
      for (let x = 0; x < w; x += 64) for (let y = 0; y < h; y += 64) { g.beginPath(); g.moveTo(x + 32, y + 4); g.lineTo(x + 60, y + 32); g.lineTo(x + 32, y + 60); g.lineTo(x + 4, y + 32); g.closePath(); g.stroke(); }
      for (let i = 0; i < 4000; i++) { g.fillStyle = `rgba(0,0,0,${rnd() * 0.2})`; g.fillRect(rnd() * w, rnd() * h, 2, 2); } }, true, true);
    TX.velvet = tex(256, 512, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, 0); for (let i = 0; i <= 8; i++) { gr.addColorStop(i / 8, i % 2 ? '#5a0a10' : '#a01822'); } g.fillStyle = gr; g.fillRect(0, 0, w, h); }, true, true);
    TX.deco = tex(256, 256, (g, w, h) => { g.fillStyle = '#7a766c'; g.fillRect(0, 0, w, h); g.strokeStyle = 'rgba(200,160,90,0.35)'; g.lineWidth = 3;
      for (let x = 0; x < w; x += 128) { g.beginPath(); g.moveTo(x + 64, 0); g.lineTo(x + 64, h); g.stroke(); g.beginPath(); g.moveTo(x + 64, h * 0.3); g.lineTo(x + 20, 0); g.moveTo(x + 64, h * 0.3); g.lineTo(x + 108, 0); g.stroke(); } }, true, true);
    TX.paper = tex(256, 330, (g, w, h) => { g.fillStyle = '#e9e0c8'; g.fillRect(0, 0, w, h); g.fillStyle = '#2a2620'; g.font = 'bold 15px Courier New'; g.fillText('CASE FILE 47-C', 20, 30); g.font = '11px Courier New';
      for (let y = 55; y < h - 20; y += 14) { let s = ''; const n = 10 + rnd() * 24 | 0; for (let i = 0; i < n; i++) s += String.fromCharCode(97 + rnd() * 26 | 0) + (rnd() < 0.18 ? ' ' : ''); g.fillText(s, 20, y); } });
    TX.ok = true; return TX;
  }
  function tiled(m, tile) { m.userData.tile = tile; return m; }

  // a spotlight with a cookie texture that also drives the half-res light-shaft pass
  function cookieSpot(lvl, color, intensity, pos, target, angle, cookie, mapSize, shaftOpt) {
    const s = new T.SpotLight(color, intensity, 30, angle, 0.25, 1.2);
    s.position.copy(pos); s.target.position.copy(target); lvl.scene.add(s, s.target);
    s.map = cookie; s.castShadow = true; s.shadow.mapSize.set(mapSize, mapSize); s.shadow.camera.near = 0.5; s.shadow.camera.far = 30; s.shadow.bias = -0.0008;
    const lc = new T.PerspectiveCamera(T.MathUtils.radToDeg(angle) * 2, 1, 0.5, 30); lc.position.copy(pos); lc.lookAt(target); lc.updateMatrixWorld(); lc.updateProjectionMatrix();
    const vp = new T.Matrix4().multiplyMatrices(lc.projectionMatrix, lc.matrixWorldInverse);
    lvl.shaft = Object.assign({ cookie, lightVP: vp, pos: pos.clone(), color: 0xd8ebff, k: 0.16, maxD: 9, yTop: 2.9 }, shaftOpt || {});
    lvl.spot = s; return s;
  }

  // ================================================================ OFFICE (prologue)
  function buildOffice(q) {
    const X = textures(), L = new Level('office', 0x0b1014, 0.045), S = L.scene;
    L.scene.userData.expo = 1.2;
    const RW = 4.2, RD = 6.5, RH = 3.1, BACK = -4.6, FRONT = BACK + RD;
    const wallMat = tiled(lam(0xd8ccb8, X.wall), 2.2), trim = lam(0x2a1d14), frameM = lam(0x24170f);
    const floorMat = tiled(stdm(0x8a7a6a, 0.55, 0, { map: X.floor }), 1.4);
    L.box(0, -0.05, BACK + RD / 2, RW, 0.1, RD, floorMat, { solid: false, noCast: true });
    L.box(0, RH + 0.05, BACK + RD / 2, RW, 0.1, RD, lam(0x3a352e), { solid: false, noCast: true });
    L.box(-RW / 2 - 0.05, RH / 2, BACK + RD / 2, 0.1, RH, RD, wallMat, { noCast: true });
    L.box(RW / 2 + 0.05, RH / 2, BACK + RD / 2, 0.1, RH, RD, wallMat, { noCast: true });
    L.box(0, RH / 2, FRONT + 0.05, RW, RH, 0.1, wallMat, { noCast: true });
    const DOOR = { x0: -1.5, x1: -0.5, h: 2.3 }, WIN = { x0: 0.15, x1: 1.55, y0: 0.8, y1: 2.8 };
    const piece = (x0, x1, y0, y1) => L.box((x0 + x1) / 2, (y0 + y1) / 2, BACK - 0.05, x1 - x0, y1 - y0, 0.1, wallMat, { noCast: true });
    piece(-RW / 2, DOOR.x0, 0, RH); piece(DOOR.x0, DOOR.x1, DOOR.h, RH); piece(DOOR.x1, WIN.x0, 0, RH);
    piece(WIN.x0, WIN.x1, 0, WIN.y0); piece(WIN.x0, WIN.x1, WIN.y1, RH); piece(WIN.x1, RW / 2, 0, RH);
    L.box(WIN.x0 + 0.7, 1.5, BACK - 0.06, 1.4, 2, 0.04, null); // invisible collider over the window
    L.box(0, 1.0, BACK + 0.02, RW, 0.05, 0.04, trim, { solid: false }); L.box(0, 0.07, BACK + 0.02, RW, 0.14, 0.03, trim, { solid: false });
    L.box(DOOR.x0 - 0.04, DOOR.h / 2, BACK, 0.08, DOOR.h + 0.08, 0.14, frameM, { solid: false }); L.box(DOOR.x1 + 0.04, DOOR.h / 2, BACK, 0.08, DOOR.h + 0.08, 0.14, frameM, { solid: false });
    L.box((DOOR.x0 + DOOR.x1) / 2, DOOR.h + 0.04, BACK, DOOR.x1 - DOOR.x0 + 0.16, 0.08, 0.14, frameM, { solid: false });
    // hallway behind the door
    L.box(-1.0, 1.25, BACK - 2.6, 1.6, 2.5, 0.1, lam(0x1c2228), { noCast: true });
    L.box(-1.85, 1.25, BACK - 1.3, 0.1, 2.5, 2.6, lam(0x2a2e30), { noCast: true }); L.box(-0.15, 1.25, BACK - 1.3, 0.1, 2.5, 2.6, lam(0x2a2e30), { noCast: true });
    L.box(-1.0, -0.05, BACK - 1.3, 1.6, 0.1, 2.6, lam(0x2a2420), { solid: false });
    const hallLight = new T.PointLight(0x5f8f9a, 2.2, 4, 1.6); hallLight.position.set(-1.0, 2.1, BACK - 0.9); S.add(hallLight);
    // the door: swings open when Vela enters (pivot on the left jamb)
    const glassTex = tex(512, 640, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#c8c2a8'); gr.addColorStop(1, '#8e8a78'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
      g.save(); g.translate(w, 0); g.scale(-1, 1); g.fillStyle = '#14110c'; g.textAlign = 'center'; g.font = 'bold 54px Georgia'; g.fillText('S. HARROW', w / 2, 250); g.font = '30px Georgia'; g.fillText('PRIVATE INVESTIGATIONS', w / 2, 310); g.restore(); });
    const door = new T.Group(); door.position.set(DOOR.x0 + 0.02, 0, BACK + 0.02); door.rotation.y = 0; S.add(door);
    const leaf = new T.Mesh(new T.BoxGeometry(0.98, 2.26, 0.05), lam(0x3a2516)); leaf.position.set(0.49, 1.13, 0); door.add(leaf);
    const pane = new T.Mesh(new T.PlaneGeometry(0.72, 0.9), lam(0xffffff, glassTex, { emissive: 0x3a3a30, emissiveIntensity: 0.6 })); pane.position.set(0.49, 1.55, 0.03); door.add(pane);
    door.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
    L.door = door;
    const doorCol = { min: V3(DOOR.x0, 0, BACK - 0.06), max: V3(DOOR.x1, DOOR.h, BACK + 0.06), cover: false, step: false, tag: 'door' }; L.boxes.push(doorCol); L.doorCol = doorCol;
    // window, blinds, rainy glass
    const wf = lam(0x1f1611), wcx = (WIN.x0 + WIN.x1) / 2, wcy = (WIN.y0 + WIN.y1) / 2, ww = WIN.x1 - WIN.x0, wh = WIN.y1 - WIN.y0;
    for (const [x, y, sx, sy] of [[WIN.x0, wcy, 0.07, wh + 0.07], [WIN.x1, wcy, 0.07, wh + 0.07], [wcx, WIN.y0, ww + 0.07, 0.07], [wcx, WIN.y1, ww + 0.07, 0.07], [wcx, wcy, 0.035, wh], [wcx, wcy + 0.15, ww, 0.035]]) L.box(x, y, BACK, sx, sy, 0.12, wf, { solid: false });
    L.box(wcx, WIN.y0 - 0.03, BACK + 0.08, ww + 0.25, 0.05, 0.22, wf, { solid: false });
    const slatMat = lam(0x9c9078, null, { side: T.DoubleSide });
    for (let y = WIN.y1 - 0.06; y > WIN.y0 + 0.42; y -= 0.07) { const g = L.box(wcx, y, BACK + 0.08, ww - 0.06, 0.004, 0.045, slatMat, { solid: false, noCast: true }); void g; }
    const U = { time: { value: 0 } }; L.U = U;
    const glass = new T.Mesh(new T.PlaneGeometry(ww, wh), new T.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: U,
      vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }',
      fragmentShader: `uniform float time; varying vec2 vUv; float h(float n){ return fract(sin(n)*43758.5453); }
        void main(){ vec2 uv=vUv*vec2(46.,1.); float col=floor(uv.x); float fx=fract(uv.x);
          float sp=0.25+h(col)*0.6; float y=fract(vUv.y*(1.5+h(col*3.1)*2.)+time*sp+h(col*7.)); float streak=smoothstep(0.86,1.,y)*smoothstep(0.5,0.0,abs(fx-0.5))*step(0.35,h(col*1.7));
          vec2 d=vUv*vec2(70.,110.); vec2 id=floor(d); float drop=step(0.93,h(dot(id,vec2(12.9,78.2))))*smoothstep(0.45,0.1,length(fract(d)-0.5));
          gl_FragColor=vec4(vec3(0.75,0.85,0.9), streak*0.55+drop*0.35+0.05); }` }));
    glass.position.set(wcx, wcy, BACK - 0.03); S.add(glass);
    // city outside the window
    const bldTex = tex(512, 1024, (g, w, h) => { g.fillStyle = '#07090c'; g.fillRect(0, 0, w, h);
      for (let y = 30; y < h; y += 22) for (let x = 10; x < w; x += 18) if (rnd() < 0.28) { g.fillStyle = rnd() < 0.7 ? `rgba(255,${170 + rnd() * 50 | 0},90,${0.25 + rnd() * 0.6})` : `rgba(110,220,230,${0.3 + rnd() * 0.5})`; g.fillRect(x, y, 9, 12); } });
    const city = new T.Group(); S.add(city);
    const bmat = basic(0xffffff, { map: bldTex, fog: false });
    for (const [x, z, wd, ht] of [[-1.5, -16, 6, 22], [5.5, -14, 5, 26], [1.8, -24, 7, 40], [-6, -26, 6, 34]]) { const b = new T.Mesh(new T.PlaneGeometry(wd, ht), bmat); b.position.set(x, ht / 2 - 6, z); city.add(b); }
    neon('HOTEL ARCADIA', '#ffc45a', '#ffb030', 1.6, 3.1, -12, -0.25, 5.0, city, 'bold 120px Georgia');
    const cruiser = new T.Group(); cruiser.position.set(1.1, 2.6, -8); city.add(cruiser);
    cruiser.add(new T.Mesh(new T.BoxGeometry(1.6, 0.25, 0.6), basic(0x050608, { fog: false })));
    glow(0xff3a2a, 0.55, -0.8, 0, 0.3, cruiser); glow(0xfff2d0, 0.9, 0.8, 0, 0.3, cruiser); glow(0x40e0ff, 0.35, 0, 0.15, 0.3, cruiser);
    for (let i = 0; i < 12; i++) glow(rnd() < 0.5 ? 0xffb050 : 0x50e0ff, 0.3 + rnd() * 0.5, -6 + rnd() * 14, -2 + rnd() * 12, -18 - rnd() * 12, city);
    // desk + props
    const DESK_Y = 0.76; L.DESK_Y = DESK_Y;
    const deskMat = tiled(lam(0x9a8070, X.wood), 1.2);
    L.box(0, DESK_Y - 0.03, -0.43, 2.2, 0.06, 1.55, deskMat, { solid: false });
    L.box(0, 0.38, -1.15, 2.1, 0.7, 0.05, lam(0x24140a), { solid: false });
    L.box(0, 0.4, -0.43, 2.2, 0.8, 1.55, null, { cover: true }); // desk collider
    L.box(0.05, DESK_Y + 0.003, -0.5, 0.8, 0.006, 0.5, lam(0x1d2a1c), { solid: false, noShadow: true });
    for (const [x, z, r, y] of [[-0.1, -0.55, 0.25, 0.008], [0.1, -0.6, -0.18, 0.011], [-0.28, -0.45, 0.6, 0.013]]) { const m = new T.Mesh(new T.PlaneGeometry(0.21, 0.27), lam(0xffffff, X.paper)); m.position.set(x, DESK_Y + y, z); m.rotation.set(-Math.PI / 2, 0, r); S.add(m); }
    const brass = stdm(0xc8963e, 0.28, 1.0);
    const lamp = new T.Group(); lamp.position.set(-0.55, DESK_Y, -0.75); S.add(lamp);
    lamp.add((() => { const _m = new T.Mesh(new T.CylinderGeometry(0.09, 0.11, 0.03, 16), brass); _m.position.set(0, 0.015, 0); return _m; })());
    lamp.add((() => { const _m = new T.Mesh(new T.CylinderGeometry(0.012, 0.012, 0.36, 8), brass); _m.position.set(0, 0.2, 0); return _m; })());
    const shade = new T.Mesh(new T.CylinderGeometry(0.05, 0.15, 0.13, 16, 1, true), stdm(0x2a6a3a, 0.35, 0.3, { side: T.DoubleSide, emissive: 0x0a2a10, emissiveIntensity: 1 })); shade.position.set(0.12, 0.40, 0.02); lamp.add(shade);
    glow(0xffb060, 0.12, 0.12, 0.33, 0.02, lamp);
    const lampLight = new T.PointLight(0xffb565, 1.8, 3.2, 1.8); lampLight.position.set(-0.43, DESK_Y + 0.32, -0.73); S.add(lampLight);
    // ashtray + resting cigarette
    const ash = new T.Group(); ash.position.set(0.3, DESK_Y, -0.62); S.add(ash);
    ash.add((() => { const _m = new T.Mesh(new T.CylinderGeometry(0.085, 0.075, 0.03, 16), stdm(0x6d6a60, 0.15, 0.2)); _m.position.set(0, 0.015, 0); return _m; })());
    L.ashTip = V3(0.3 - 0.09, DESK_Y + 0.05, -0.62);
    // revolver on the desk (picked up in the prologue)
    const gun = NR.fx ? NR.fx.revolverModel(true) : new T.Group(); gun.position.set(-0.12, DESK_Y + 0.03, -0.35); gun.rotation.set(-Math.PI / 2, 0, -0.9); gun.scale.setScalar(1.1); S.add(gun); L.deskGun = gun;
    // fedora
    const hat = NR.fx ? NR.fx.hatModel(0x2a2826) : new T.Group(); hat.position.set(0.62, DESK_Y, -1.0); hat.rotation.y = -0.5; S.add(hat);
    // ceiling fan, cabinet, coat rack, chair
    const fan = new T.Group(); fan.position.set(0.15, 2.8, -2.7); S.add(fan);
    const blades = new T.Group(); fan.add(blades); const bladeM = lam(0x2a1a10);
    for (let i = 0; i < 4; i++) { const b = new T.Mesh(new T.BoxGeometry(0.62, 0.008, 0.12), bladeM); b.geometry.translate(0.36, 0, 0); b.rotation.y = i * Math.PI / 2; b.castShadow = true; blades.add(b); }
    L.box(1.7, 0.65, -3.3, 0.5, 1.3, 0.6, stdm(0x3c3a33, 0.5, 0.6), { cover: false });
    L.box(-1.8, 0.9, 1.5, 0.3, 1.8, 0.3, lam(0x24170f)); // coat rack
    L.box(-1.77, 1.6, 1.5, 0.3, 0.5, 0.2, lam(0x1a1a1c), { solid: false });
    L.box(0.1, 0.25, 1.3, 0.5, 0.5, 0.5, lam(0x3a2418)); L.box(0.1, 0.75, 1.55, 0.5, 0.6, 0.08, lam(0x3a2418)); // desk chair, pushed back
    L.box(0.9, 0.25, -1.9, 0.45, 0.5, 0.45, lam(0x3a2418)); // client chair
    // lights: moonlight through the blinds (cookie spot = shafts), teal outside fill, amber sign spill
    S.add(new T.HemisphereLight(0x5a6a7a, 0x14100c, 0.8));
    const cookie = tex(512, 512, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const x0 = w * 0.18, x1 = w * 0.82, y0 = h * 0.12, y1 = h * 0.88;
      const n = 17, sh = (y1 - y0) / n; for (let i = 0; i < n; i++) { g.fillStyle = '#fff'; g.fillRect(x0, y0 + i * sh + sh * 0.45, x1 - x0, sh * 0.5); }
      g.fillStyle = '#000'; g.fillRect(w * 0.3 - 6, y0, 12, y1 - y0); g.fillRect(x0, y0 + (y1 - y0) * 0.42, x1 - x0, 10); g.filter = 'blur(1px)'; g.drawImage(g.canvas, 0, 0); }, false);
    cookieSpot(L, 0xdce8f0, 260, V3(1.75, 3.6, BACK - 3.6), V3(-0.75, 0.55, -1.2), 0.36, cookie, q === 'high' ? 1024 : 512, { zMin: BACK - 0.02 });
    const outsideFill = new T.PointLight(0x40c0c8, 3.0, 5, 1.5); outsideFill.position.set(1.2, 2.0, BACK + 0.6); S.add(outsideFill);
    const signSpill = new T.PointLight(0xffa040, 2.0, 5, 1.6); signSpill.position.set(0.9, 2.6, BACK + 0.4); S.add(signSpill);
    L.sideLight = { ambient: 0x6c7684, key: 0xfff0dc, warm: 0x5a3010 };
    // smoke: resting cigarette + room haze
    if (NR.fx) { S.add(NR.fx.smoke(160, L.ashTip, { rise: 0.9, spread: 0.08, size: 26, alpha: 0.2, life: 5 }, L.shaft)); S.add(NR.fx.smoke(50, V3(0, 1.0, -2.2), { rise: 1.6, spread: 1.4, size: 260, alpha: 0.025, life: 30 }, L.shaft)); }
    L.updaters.push((dt, t) => { U.time.value = t; blades.rotation.y = t * 0.9; cruiser.position.x = 1.6 - ((t * 0.35) % 5.0); cruiser.position.y = 2.6 + Math.sin(t * 0.8) * 0.1; });
    L.spawn = { pos: V3(0.1, 0, 0.75), yaw: 0 };
    L.exitDoor = { x: -1.0, z: BACK - 0.3 };
    L.finish(); return L;
  }

  // ================================================================ ALLEY (tutorial fight)
  function buildAlley(q) {
    const X = textures(), L = new Level('alley', 0x0d1216, 0.05), S = L.scene; L.outdoor = true; S.userData.expo = 1.25;
    const LEN = 40, HW = 3.2;
    const brick = tiled(lam(0xffffff, X.brick), 2.4);
    const ground = tiled(stdm(0xffffff, 0.35, 0.0, { map: X.asphalt, roughnessMap: X.puddleRough }), 4);
    L.box(0, -0.05, -LEN / 2, HW * 2 + 2, 0.1, LEN + 6, ground, { solid: false, noCast: true });
    L.box(-HW - 0.3, 6, -LEN / 2, 0.6, 12, LEN + 6, brick, { noCast: true }); L.box(HW + 0.3, 6, -LEN / 2, 0.6, 12, LEN + 6, brick, { noCast: true });
    L.box(0, 3, -LEN - 0.5, HW * 2, 6, 0.6, brick, { noCast: true }); L.box(0, 3, 3.2, HW * 2, 6, 0.6, lam(0x101418), { noCast: true });
    // doorways, pipes, fire escapes
    const dark = lam(0x0e1012), metal = stdm(0x2a2e33, 0.5, 0.7), green = lam(0x24302a);
    for (const [x, z] of [[-HW, -9], [HW, -17], [-HW, -27]]) { L.box(x + (x < 0 ? 0.02 : -0.02), 1.2, z, 0.05, 2.4, 1.2, dark, { solid: false }); L.box(x + (x < 0 ? 0.1 : -0.1), 2.5, z, 0.2, 0.08, 1.5, metal, { solid: false }); }
    for (let z = -2; z > -LEN; z -= 9) { L.box(-HW + 0.12, 5, z, 0.1, 10, 0.1, metal, { solid: false }); }
    for (const [x, z0] of [[HW - 0.6, -6], [-HW + 0.6, -21]]) {
      for (let y = 3.6; y < 11; y += 3.2) { L.box(x, y, z0 - 3, 1.2, 0.06, 6, metal, { solid: false }); for (let k = 0; k < 6; k++) L.box(x + (x > 0 ? -0.6 : 0.6), y + 0.5, z0 - k * 1.2, 0.04, 1.0, 0.04, metal, { solid: false }); }
    }
    // cover: dumpsters, crates, barrels
    const dump = lam(0x4a5a50), crate = tiled(lam(0xffffff, X.wood), 0.8), barrel = lam(0x3a2a20);
    L.box(-HW + 0.75, 0.65, -12, 1.3, 1.3, 2.0, dump, { cover: true }); L.box(-HW + 0.75, 1.36, -12, 1.4, 0.1, 2.1, green, { solid: false });
    L.box(HW - 0.75, 0.65, -22, 1.3, 1.3, 2.0, dump, { cover: true }); L.box(HW - 0.75, 1.36, -22, 1.4, 0.1, 2.1, green, { solid: false });
    L.box(1.2, 0.5, -16, 1.0, 1.0, 1.0, crate, { cover: true }); L.box(1.0, 1.25, -16.1, 0.5, 0.5, 0.5, crate, { cover: true });
    L.box(-0.9, 0.55, -29, 1.4, 1.1, 0.9, crate, { cover: true });
    L.box(HW - 0.6, 0.45, -31, 0.7, 0.9, 0.7, barrel, { cover: true }); L.box(-HW + 0.5, 0.45, -5, 0.7, 0.9, 0.7, barrel, { cover: true });
    // neon signs + glow spill lights (few lights; the signs are emissive)
    neon('HOTEL', '#ff6a5a', '#ff2010', -HW + 0.02, 4.2, -7, Math.PI / 2, 3.2, S);
    neon('NOODLES', '#7ff4ff', '#20d0ff', HW - 0.02, 3.4, -14, -Math.PI / 2, 3.6, S);
    neon('BAR', '#ffc45a', '#ffa020', -HW + 0.02, 3.0, -24, Math.PI / 2, 2.4, S);
    neon('ROOMS', '#ff7ab0', '#ff2a70', HW - 0.02, 5.0, -30, -Math.PI / 2, 3.0, S);
    const pl = (c, i, x, y, z, d) => { const p = new T.PointLight(c, i, d || 9, 1.6); p.position.set(x, y, z); S.add(p); return p; };
    pl(0xffb8a0, 45, -HW + 0.8, 3.8, -7, 12); pl(0x30d0ff, 60, HW - 0.8, 3.2, -14, 14); pl(0xffa040, 50, -HW + 0.8, 2.8, -24, 14); pl(0xd0a0ff, 35, HW - 0.8, 4.6, -30, 12);
    S.add(new T.HemisphereLight(0x6a7a8c, 0x1a1616, 1.3));
    // street lamp over Miles: grated cookie spot through the rain (drives the shafts)
    const cookie = tex(256, 256, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const r = g.createRadialGradient(w / 2, h / 2, 4, w / 2, h / 2, w / 2); r.addColorStop(0, '#fff'); r.addColorStop(0.85, '#999'); r.addColorStop(1, '#000'); g.fillStyle = r; g.fillRect(0, 0, w, h);
      g.fillStyle = '#000'; for (let x = 0; x < w; x += 22) g.fillRect(x, 0, 7, h); }, false);
    cookieSpot(L, 0xffe2b0, 520, V3(0.8, 9.5, -33), V3(0, 0, -34.5), 0.42, cookie, q === 'high' ? 1024 : 512, { color: 0xffe0b0, k: 0.12, maxD: 30, yTop: 9.0 });
    const lampHead = new T.Mesh(new T.CylinderGeometry(0.1, 0.4, 0.3, 12), lam(0x202020)); lampHead.position.set(0.8, 9.6, -33); S.add(lampHead); glow(0xffe0b0, 1.2, 0.8, 9.4, -33, S);
    // the city beyond the end wall
    const bldTex = tex(256, 512, (g, w, h) => { g.fillStyle = '#05070a'; g.fillRect(0, 0, w, h); for (let y = 10; y < h; y += 14) for (let x = 6; x < w; x += 12) if (rnd() < 0.25) { g.fillStyle = rnd() < 0.7 ? 'rgba(255,190,100,.7)' : 'rgba(110,220,230,.6)'; g.fillRect(x, y, 6, 8); } });
    for (const [x, z, w, h] of [[-4, -60, 14, 50], [8, -70, 12, 70], [-12, -80, 16, 60]]) { const b = new T.Mesh(new T.PlaneGeometry(w, h), basic(0xffffff, { map: bldTex, fog: false })); b.position.set(x, h / 2 - 2, z); S.add(b); }
    L.sideLight = { ambient: 0x56606e, key: 0xffe0b0, warm: 0x401808 };
    if (NR.fx) { L.rain = NR.fx.rain(q === 'high' ? 2600 : 1600); S.add(L.rain); S.add(NR.fx.smoke(30, V3(0.6, 0.1, -19), { rise: 2.4, spread: 0.5, size: 220, alpha: 0.05, life: 6 }, L.shaft)); }
    L.updaters.push((dt, t) => { if (L.rain) L.rain.material.uniforms.time.value = t; });
    L.spawn = { pos: V3(0, 0, 0.5), yaw: 0 };
    L.bodyPos = V3(0.2, 0, -34.5);
    L.finish(); return L;
  }

  // ================================================================ THE BLUE ORCHID (club)
  function buildClub(q) {
    const X = textures(), L = new Level('club', 0x120c10, 0.035), S = L.scene; S.userData.expo = 1.3;
    const HW = 8, Z1 = -24, RH = 4.2;
    L.box(0, -0.05, Z1 / 2, HW * 2, 0.1, -Z1 + 2, tiled(lam(0xffffff, X.carpet), 1.6), { solid: false, noCast: true });
    L.box(0, RH + 0.05, Z1 / 2, HW * 2, 0.1, -Z1 + 2, lam(0x1a1416), { solid: false, noCast: true });
    const wall = tiled(lam(0xffffff, X.deco), 1.6);
    L.box(-HW - 0.1, RH / 2, Z1 / 2, 0.2, RH, -Z1 + 2, wall, { noCast: true }); L.box(HW + 0.1, RH / 2, Z1 / 2, 0.2, RH, -Z1 + 2, wall, { noCast: true });
    L.box(0, RH / 2, 1.1, HW * 2, RH, 0.2, wall, { noCast: true }); L.box(0, RH / 2, Z1 - 0.1, HW * 2, RH, 0.2, wall, { noCast: true });
    // entrance doors (front) and kitchen door (left back): Gale's men come through these
    L.box(0, 1.2, 0.98, 1.8, 2.4, 0.05, lam(0x3a2216), { solid: false });
    L.box(-HW + 0.02, 1.2, -16, 0.05, 2.4, 1.2, lam(0x2a1a12), { solid: false });
    // stage + curtain + piano + mic
    const stageWood = tiled(stdm(0xffffff, 0.4, 0, { map: X.wood }), 1.2);
    L.box(-1.5, 0.3, -21, 11, 0.6, 6, stageWood, { step: true });
    L.box(-1.5, 2.4, Z1 + 0.25, 11, 4.0, 0.2, tiled(lam(0xffffff, X.velvet), 2.2), { noCast: true });
    L.box(-5.2, 1.1, -21.5, 1.6, 1.0, 1.0, lam(0x0c0c0e), { cover: true }); L.box(-5.2, 1.65, -21.6, 1.6, 0.1, 0.4, lam(0xe8e2d4), { solid: false });
    L.box(-1.5, 1.35, -19.5, 0.03, 1.5, 0.03, stdm(0x888888, 0.3, 1), { solid: false }); L.box(-1.5, 1.35, -19.5, 0.25, 1.5, 0.25, null); L.box(-1.5, 2.1, -19.5, 0.07, 0.12, 0.07, stdm(0x666666, 0.3, 1), { solid: false });
    // dressing room (right of stage, behind a partition)
    L.box(4.6, RH / 2, -18.5, 0.2, RH, 3.0, wall); L.box(4.6, 3.3, -16.2, 0.2, 1.8, 1.6, wall, { solid: false }); L.box(4.6, RH / 2, -21.8, 0.2, RH, 0.4, wall);
    L.box(4.6 + 1.7, RH / 2, -15.1, 3.2, RH, 0.2, wall);
    L.box(7.4, 0.4, -19.2, 1.0, 0.8, 2.6, lam(0x3a2a24), { cover: true }); // vanity table
    const mirror = new T.Mesh(new T.PlaneGeometry(0.9, 1.1), stdm(0x9aa4a8, 0.08, 0.9)); mirror.position.set(7.88, 1.45, -19.2); mirror.rotation.y = -Math.PI / 2; S.add(mirror);
    for (let i = 0; i < 6; i++) glow(0xffe0a0, 0.18, 7.86, 2.05, -19.6 + i * 0.16, S, 0.8);
    L.box(5.6, 0.9, -23.3, 1.6, 1.8, 0.8, lam(0x2a2028), { cover: true }); // wardrobe
    const vanityLight = new T.PointLight(0xffd8a0, 14, 6, 1.7); vanityLight.position.set(7.2, 2.1, -19.2); S.add(vanityLight);
    // bar (left wall) with bottles and backlight
    const barWood = tiled(stdm(0xffffff, 0.35, 0, { map: X.wood }), 1.0);
    L.box(-5.4, 0.55, -9, 0.8, 1.1, 10, barWood, { cover: true }); L.box(-5.4, 1.13, -9, 1.0, 0.06, 10.2, stdm(0x1a1010, 0.15, 0.3), { solid: false });
    L.box(-7.7, 1.6, -9, 0.4, 0.06, 9, lam(0x2a1a12), { solid: false }); L.box(-7.7, 2.2, -9, 0.4, 0.06, 9, lam(0x2a1a12), { solid: false });
    const bottleCols = [0x3a6a3a, 0x7a4a1a, 0xc8b070, 0x2a3a5a, 0x8a1a1a];
    for (let i = 0; i < 26; i++) { const c = bottleCols[i % 5]; L.box(-7.7 + (rnd() - 0.5) * 0.15, 1.78 + (i % 2) * 0.6, -13.2 + i * 0.33, 0.08, 0.3, 0.08, stdm(c, 0.15, 0.1, { emissive: c, emissiveIntensity: 0.25 }), { solid: false, noShadow: true }); }
    const barLight = new T.PointLight(0xffa050, 40, 10, 1.6); barLight.position.set(-7, 2.8, -9); S.add(barLight);
    // booths (right wall), tables, pillars
    const leather = stdm(0x6a1418, 0.45), tableM = stdm(0x1a1210, 0.3, 0.2);
    for (const z of [-4.5, -8.5, -12.5]) {
      L.box(6.9, 0.55, z, 1.6, 1.1, 0.4, leather, { cover: true }); L.box(6.9, 0.55, z - 2.2, 1.6, 1.1, 0.4, leather, { cover: true });
      L.box(7.6, 0.6, z - 1.1, 0.4, 1.2, 2.6, leather, { cover: true }); L.box(6.6, 0.38, z - 1.1, 1.0, 0.76, 1.0, tableM, { cover: true });
      glow(0xffb060, 0.35, 6.6, 0.95, z - 1.1, S); L.box(6.6, 0.82, z - 1.1, 0.06, 0.12, 0.06, lam(0xffd090, null, { emissive: 0xff9040 }), { solid: false });
    }
    const boothLight = new T.PointLight(0xff9a50, 40, 11, 1.7); boothLight.position.set(5.8, 2.0, -8.5); S.add(boothLight);
    for (const [x, z] of [[-1.5, -5.5], [1.8, -8], [-2.2, -11.5], [1.2, -13.5], [-0.5, -15.6]]) {
      L.box(x, 0.36, z, 1.0, 0.72, 1.0, tableM, { cover: true }); L.box(x, 0.74, z, 1.1, 0.04, 1.1, lam(0xe8e2d4), { solid: false, noShadow: true });
      glow(0xffb060, 0.28, x, 0.85, z, S); L.box(x, 0.8, z, 0.05, 0.1, 0.05, lam(0xffd090, null, { emissive: 0xff9040 }), { solid: false });
    }
    const pillar = lam(0x2a2622);
    for (const [x, z] of [[-3.2, -3.5], [3.6, -3.5], [-3.2, -16.8], [3.4, -16.8]]) { L.box(x, RH / 2, z, 0.6, RH, 0.6, pillar, { cover: true }); L.box(x, 3.0, z, 0.66, 0.08, 0.66, lam(0xc8963e, null, { emissive: 0x3a2808 }), { solid: false }); }
    // practical wall sconces so the far walls read (emissive shades + glow, two fill lights)
    const sconceM = lam(0xe8d8b0, null, { emissive: 0xffc070, emissiveIntensity: 0.9 });
    for (const [x, z, ry] of [[-HW + 0.06, -3, 1], [-HW + 0.06, -12.5, 1], [-HW + 0.06, -19.5, 1], [HW - 0.06, -2.5, -1], [HW - 0.06, -15.6, -1], [-6.5, Z1 + 0.06, 0], [3.6, Z1 + 0.06, 0]]) {
      const dx = ry ? 0.1 * ry : 0, dz = ry ? 0 : 0.1;
      L.box(x + dx, 2.55, z + dz, ry ? 0.16 : 0.26, 0.3, ry ? 0.26 : 0.16, sconceM, { solid: false, noShadow: true });
      glow(0xffb060, 0.9, x + dx * 2.2, 2.6, z + dz * 2.2, S, 0.55);
    }
    for (const [x, z] of [[-7.2, -15.5], [7.2, -4.5], [-6.6, -22.6]]) { const p = new T.PointLight(0xffb070, 18, 8, 1.6); p.position.set(x, 2.7, z); S.add(p); }
    // neon sign over the stage
    neon('The Blue Orchid', '#8ff0ff', '#2ad0ff', -1.5, 3.75, Z1 + 0.5, 0, 6.0, S, 'italic bold 128px Georgia');
    const neonLight = new T.PointLight(0x40c8ff, 40, 10, 1.6); neonLight.position.set(-1.5, 3.4, -21.5); S.add(neonLight);
    S.add(new T.HemisphereLight(0x8a8aaa, 0x3a2a2a, 2.2));
    for (const [x, z, c] of [[-2, -6, 0xffb070], [2.5, -10, 0xffa060], [-1, -14, 0xffb070]]) { const p = new T.PointLight(c, 22, 9, 1.6); p.position.set(x, 3.6, z); S.add(p); glow(c, 0.5, x, 3.95, z, S); L.box(x, 4.05, z, 0.5, 0.1, 0.5, lam(0xc8963e, null, { emissive: 0x6a4010 }), { solid: false }); }
    // stage spotlight (round soft cookie) = the light shaft through the smoke
    const cookie = tex(256, 256, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); const r = g.createRadialGradient(w / 2, h / 2, 2, w / 2, h / 2, w * 0.42); r.addColorStop(0, '#fff'); r.addColorStop(0.7, '#ddd'); r.addColorStop(1, '#000'); g.fillStyle = r; g.fillRect(0, 0, w, h); }, false);
    cookieSpot(L, 0xcfe0ff, 900, V3(1.0, RH - 0.1, -11.5), V3(-1.5, 0.6, -19.5), 0.32, cookie, q === 'high' ? 1024 : 512, { color: 0xcfe2ff, k: 0.22, maxD: 18, yTop: 4.1 });
    glow(0xe0eaff, 0.8, 1.0, RH - 0.15, -11.5, S);
    L.sideLight = { ambient: 0x606070, key: 0xe8f0ff, warm: 0x5a2010 };
    if (NR.fx) { S.add(NR.fx.smoke(90, V3(-0.5, 0.8, -12), { rise: 2.6, spread: 4.0, size: 420, alpha: 0.03, life: 34 }, L.shaft)); }
    L.signLight = new T.PointLight(0xff2a14, 0, 18, 1.2); L.signLight.position.set(0.6, 3.8, -10.5); S.add(L.signLight); // the title sign's red cast
    L.spawn = { pos: V3(0, 0, -0.6), yaw: 0 };
    L.doloresPos = V3(5.6, 0, -16.6);
    L.finish(); return L;
  }

  NR.world = { Level, tex, glow, lam, stdm, basic, V3, glowTex, build: { office: buildOffice, alley: buildAlley, club: buildClub } };
})();
