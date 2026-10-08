// NEON RAIN actors: painted billboard characters (8 view angles + idle frames) and enemies with cover AI.
// Enemies and Miles Corran are rigged 3D people from src/cast.js (block figures only while the GLB is still loading).
(function () {
  const T = THREE, V3 = (x, y, z) => new T.Vector3(x, y, z), C = NR.cfg;

  // ================================================================ painted billboard characters
  const ANG = ['front', 'front34L', 'sideL', 'back34R', 'back', 'back34L', 'sideR', 'front34L']; // sector k = round(theta/45deg) mod 8; last one mirrored
  const FLIP = [0, 0, 0, 0, 0, 0, 0, 1];
  const texCache = {};
  const loader = new T.TextureLoader();
  function loadTex(url) { if (!texCache[url]) { const t = loader.load(url, undefined, undefined, () => console.warn('missing sprite', url)); t.colorSpace = T.SRGBColorSpace; t.anisotropy = 4; texCache[url] = t; } return texCache[url]; }
  function preload(who) { const set = { angle: {}, idle: [] }; for (const a of new Set(ANG)) set.angle[a] = loadTex(NR.SPRITE(who, a)); for (let i = 0; i < 12; i++) set.idle.push(loadTex(NR.SPRITE(who, 'idle_' + String(i).padStart(2, '0')))); return set; }
  const blackTex = new T.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1); blackTex.needsUpdate = true;
  function paintedMat(level) {
    const sl = level.sideLight || { ambient: 0x606878, key: 0xffffff, warm: 0 };
    const sh = level.shaft;
    return new T.ShaderMaterial({
      transparent: false, side: T.DoubleSide,
      uniforms: { map: { value: null }, rect: { value: new T.Vector4(0, 0, 1, 1) }, flip: { value: 0 }, walkPh: { value: 0 }, walk: { value: 0 }, side: { value: 0 }, cookie: { value: sh ? sh.cookie : blackTex }, lightVP: { value: sh ? sh.lightVP : new T.Matrix4() },
        ambient: { value: new T.Color(sl.ambient) }, key: { value: new T.Color(sl.key) }, warm: { value: new T.Color(sl.warm) }, keyGain: { value: sh ? 1.0 : 0.0 },
        fogC: { value: level.scene.fog.color }, fogD: { value: level.scene.fog.density }, hit: { value: 0 },
        rimGain: { value: 0 }, rimSide: { value: 1 }, rimCol: { value: new T.Color(0xf0dcc4) } },
      vertexShader: 'uniform float flip; uniform vec4 rect; varying vec2 vUv, vL; varying vec3 vW; varying float vDepth; void main(){ vL=vec2(flip>0.5?1.-uv.x:uv.x, uv.y); vUv=rect.xy+vL*rect.zw; vec4 w=modelMatrix*vec4(position,1.); vW=w.xyz; vec4 mv=viewMatrix*w; vDepth=-mv.z; gl_Position=projectionMatrix*mv; }',
      fragmentShader: `uniform vec4 rect; uniform float rimGain, rimSide; uniform vec3 rimCol; uniform sampler2D map, cookie; uniform mat4 lightVP; uniform vec3 ambient, key, warm, fogC; uniform float keyGain, fogD, hit, walk, walkPh, side; varying vec2 vUv, vL; varying vec3 vW; varying float vDepth;
        void main(){ vec2 uv = vUv;
          // two-pose walk: below the hem, the leg on one half lifts and swings while the other plants, then they swap
          if (walk > 0.0 && uv.y < 0.34) { float k = 1.0 - uv.y / 0.34; float s = sin(walkPh); float leg = uv.x < 0.5 ? 1.0 : -1.0;
            float lift = max(0.0, s * leg) * 0.022 * k * walk; uv.y -= lift;
            uv.x -= s * 0.035 * k * walk * side; }
          vec4 t=texture2D(map,uv); if(t.a<0.5) discard;
          // 1-2 px matte erosion: the light anti-aliased edge of the sprite (its old background) never reaches the screen
          vec2 e = max(abs(dFdx(uv)), abs(dFdy(uv))) * 1.5; float ea = min(min(texture2D(map, uv + vec2(e.x, 0.)).a, texture2D(map, uv - vec2(e.x, 0.)).a), min(texture2D(map, uv + vec2(0., e.y)).a, texture2D(map, uv - vec2(0., e.y)).a));
          if (ea < 0.5) discard; t.rgb *= mix(0.75, 1.0, smoothstep(0.5, 0.95, ea)); vec3 c=t.rgb*t.rgb; // ~linear
          vec4 lp=lightVP*vec4(vW,1.); vec2 luv=lp.xy/lp.w*0.5+0.5; float ck=0.; if(keyGain>0. && lp.w>0. && luv.x>0. && luv.x<1. && luv.y>0. && luv.y<1.) ck=smoothstep(0.3,0.8,texture2D(cookie,luv).r);
          float side=smoothstep(0.1,0.9,vL.x);
          vec3 light = ambient*(1.3+0.7*side) + key*ck*keyGain*(0.4+0.6*side) + warm*(1.0-vL.y)*0.5;
          vec3 col = c*light*1.25 + vec3(hit,0.,0.);
          // rim: a warm edge on the side the key light comes from (painted walker only; rimGain 0 elsewhere)
          if (rimGain > 0.0) { float an = texture2D(map, uv + vec2(rect.z * 0.006 * rimSide, rect.w * 0.002)).a; col += rimCol * rimCol * (1.0 - an) * rimGain * 0.35 * (0.5 + 0.5 * vL.y); } // thin, faint: no halo
          float f = 1.0-exp(-fogD*fogD*vDepth*vDepth); col = mix(col, fogC*fogC, f);
          // red-keep mask for the B&W grade: painted reds (dress, lips) write alpha < 1, the post pass keeps their colour
          float rk = smoothstep(2.0, 2.8, t.r / max(0.03, max(t.g, t.b))) * smoothstep(0.16, 0.3, t.r);
          col = mix(col, col * vec3(1.25, 0.8, 0.8), rk * 0.5);
          gl_FragColor=vec4(col, 1.0 - rk * 0.95); }`,
    });
  }
  class Painted {
    constructor(who, level, pos, yaw, height = 1.86) {
      this.who = who; this.set = preload(who); this.pos = pos.clone(); this.yaw = yaw || 0; this.h = height;
      this.mat = paintedMat(level); this.mat.uniforms.map.value = this.set.idle[0];
      this.mesh = new T.Mesh(new T.PlaneGeometry(height * 0.5, height), this.mat); this.mesh.renderOrder = 1;
      const cs = new T.Mesh(new T.PlaneGeometry(0.9, 0.5), new T.MeshBasicMaterial({ map: NR.world.glowTex, color: 0x000000, transparent: true, opacity: 0.75, depthWrite: false }));
      cs.material.onBeforeCompile = s => { s.fragmentShader = s.fragmentShader.replace('#include <map_fragment>', 'vec4 sc=texture2D(map,vMapUv); diffuseColor=vec4(0.,0.,0.,sc.r*opacity);'); };
      cs.rotation.x = -Math.PI / 2; cs.position.y = 0.012; cs.renderOrder = 1; this.shadow = cs;
      this.group = new T.Group(); this.group.add(this.mesh, cs); level.scene.add(this.group);
      this.path = null; this.speed = 1.15; this.t = Math.random() * 10; this.ph = 0; this.walkAmt = 0; this.visible = true; this.sector = 0; this.walking = false; this.onArrive = null;
      this.sync();
    }
    walkTo(points, speed) { this.path = points.map(p => p.clone()); this.speed = speed || 1.15; return new Promise(r => { this.onArrive = r; }); }
    faceTo(p) { this.yaw = Math.atan2(p.x - this.pos.x, p.z - this.pos.z); }
    sync() { this.group.position.copy(this.pos); const w = this.walkAmt || 0; this.mesh.position.y = this.h / 2 - 0.02 + w * (Math.abs(Math.cos(this.ph)) * 0.03 - 0.012); this.mesh.rotation.z = w * Math.sin(this.ph) * 0.025; }
    update(dt, cam) {
      this.t += dt;
      this.walking = false;
      if (this.path && this.path.length) {
        const tgt = this.path[0], d = V3(tgt.x - this.pos.x, 0, tgt.z - this.pos.z), L = d.length();
        if (L < 0.05) { this.path.shift(); if (!this.path.length) { this.path = null; const f = this.onArrive; this.onArrive = null; if (f) f(); } }
        else { // paced steps: speed swells mid-stride and eases as each heel lands, so she does not glide
          const pace = 0.45 + 1.1 * Math.pow(Math.sin(this.ph), 2), step = Math.min(L, this.speed * pace * dt);
          const before = Math.sin(this.ph); this.ph += dt * this.speed / 0.62 * Math.PI; if (Math.sign(Math.sin(this.ph)) !== Math.sign(before) && NR.audio) NR.audio.fx.heel();
          this.pos.addScaledVector(d.normalize(), step); const ty = Math.atan2(d.x, d.z); let dy = ty - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 8); this.walking = true; }
      }
      this.walkAmt += ((this.walking ? 1 : 0) - this.walkAmt) * Math.min(1, dt * 6);
      this.sync();
      // billboard toward the camera; choose the painted angle from where the camera stands relative to her facing
      const cx = cam.position.x - this.pos.x, cz = cam.position.z - this.pos.z;
      this.mesh.rotation.y = Math.atan2(cx, cz);
      const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw), cl = Math.hypot(cx, cz) || 1, tx = cx / cl, tz = cz / cl;
      const rx = tz, rz = -tx; // camera's screen-right on the ground plane (camera looks along -t)
      const th = Math.atan2(fx * rx + fz * rz, fx * tx + fz * tz);
      const k = ((Math.round(th / (Math.PI / 4)) % 8) + 8) % 8; this.sector = k;
      this.mat.uniforms.map.value = (k === 0 && !this.walking) ? this.set.idle[Math.floor(this.t * 8) % 12] : this.set.angle[ANG[k]];
      this.mat.uniforms.flip.value = FLIP[k]; this.mat.uniforms.walk.value = this.walkAmt; this.mat.uniforms.walkPh.value = this.ph;
      this.mat.uniforms.side.value = (k === 2 || k === 6) ? (k === 2 ? 1 : -1) : 0.25;
      this.group.visible = this.visible;
    }
    remove() { if (this.group.parent) this.group.parent.remove(this.group); }
  }

  // ================================================================ frame-animated painted walker (Vela)
  // Painted over a mocap walk: 16-frame loop from 8 camera angles, a stop-and-turn clip that carries its own root motion,
  // an idle loop seen from the front and one still per angle at rest. Walk frames advance with distance walked, so feet do not slide.
  function loadAnim(who) { return Promise.resolve((NR.ANIM && NR.ANIM[who]) || null); } // table lives in src/anim_data.js (no fetch, no 404)
  const sheet = name => loadTex(NR.ASSET + 'sprites/' + name);
  function cellRect(v, s, i) { const c = i % s.cols, r = Math.floor(i / s.cols); v.set(c / s.cols, 1 - (r + 1) / s.rows, 1 / s.cols, 1 / s.rows); }
  class Walker {
    constructor(who, level, pos, yaw, D) {
      this.who = who; this.D = D; this.pos = pos.clone(); this.yaw = yaw || 0; this.rimSrc = level.shaft ? level.shaft.pos : null;
      this.tex = { walk: {}, stop: {}, pose: sheet(D.pose.sheet), idle: sheet(D.idle.sheet) };
      if (D.stop.angles) for (const a in D.stop.angles) this.tex.stop[a] = sheet(D.stop.angles[a].sheet); else this.tex.stop['0'] = sheet(D.stop.sheet);
      for (const a in D.walk.angles) this.tex.walk[a] = sheet(D.walk.angles[a].sheet);
      this.mat = paintedMat(level); this.mat.uniforms.map.value = this.tex.idle; cellRect(this.mat.uniforms.rect.value, D.idle, 0);
      this.mesh = new T.Mesh(new T.PlaneGeometry(D.world[0], D.world[1]), this.mat); this.mesh.position.y = D.centerY; this.mesh.renderOrder = 1;
      const cs = new T.Mesh(new T.PlaneGeometry(0.9, 0.5), new T.MeshBasicMaterial({ map: NR.world.glowTex, color: 0x000000, transparent: true, opacity: 0.75, depthWrite: false }));
      cs.material.onBeforeCompile = s => { s.fragmentShader = s.fragmentShader.replace('#include <map_fragment>', 'vec4 sc=texture2D(map,vMapUv); diffuseColor=vec4(0.,0.,0.,sc.r*opacity);'); };
      cs.rotation.x = -Math.PI / 2; cs.position.y = 0.012; cs.renderOrder = 1; this.shadow = cs;
      this.group = new T.Group(); this.group.add(this.mesh, cs); level.scene.add(this.group);
      this.path = null; this.speed = D.walk.speed; this.mode = 'idle'; this.t = 0; this.dist = 0; this.ph0 = 0; this.stopAt = null; this.clip = null;
      this.visible = true; this.walking = false; this.sector = 0; this.frame = 0; this.onArrive = null; this.lastPh = 0;
      this.group.position.copy(this.pos);
    }
    walkTo(points, speed, opt) {
      const stop = !(opt && opt.stop === false), W = this.D.walk, S = this.D.stop;
      this.path = points.map(p => p.clone()); this.speed = speed || W.speed; this.dist = 0; this.mode = 'walk';
      let L = 0, prev = this.pos; for (const p of this.path) { L += Math.hypot(p.x - prev.x, p.z - prev.z); prev = p; }
      const last = this.path.length > 1 ? this.path[this.path.length - 2] : this.pos, end = this.path[this.path.length - 1];
      const lastLen = Math.hypot(end.x - last.x, end.z - last.z), dClip = S.root[S.root.length - 1][0];
      this.stopAt = stop && lastLen > dClip + 0.3 ? L - dClip : null; // the clip carries her the last dClip metres onto the mark
      this.endYaw = Math.atan2(end.x - last.x, end.z - last.z);
      // start the cycle on the phase that lands the clip's first frame exactly where the loop leaves off
      this.ph0 = this.stopAt != null ? (((S.phase - this.stopAt / W.cycle) % 1) + 1) % 1 : 0; this.lastPh = this.ph0;
      return new Promise(r => { this.onArrive = r; });
    }
    faceTo(p) { this.yaw = Math.atan2(p.x - this.pos.x, p.z - this.pos.z); }
    arrive() { this.path = null; this.mode = 'idle'; this.t = 0; const f = this.onArrive; this.onArrive = null; if (f) f(); }
    update(dt, cam) {
      const D = this.D, W = D.walk, S = D.stop, u = this.mat.uniforms; this.t += dt; this.walking = false;
      if (this.mode === 'walk') {
        if (this.stopAt != null && this.dist >= this.stopAt) { this.mode = 'stop'; this.clip = { t: 0, o: this.pos.clone(), y: this.endYaw, f: -1 }; this.yaw = this.endYaw; }
        else if (this.path && this.path.length) {
          const tgt = this.path[0], d = V3(tgt.x - this.pos.x, 0, tgt.z - this.pos.z), L = d.length();
          if (L < 0.02) { this.path.shift(); if (!this.path.length) this.arrive(); }
          else {
            const step = Math.min(L, this.speed * dt); this.pos.addScaledVector(d.normalize(), step); this.dist += step; this.walking = true;
            let dy = Math.atan2(d.x, d.z) - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 6);
          }
        } else this.arrive();
      }
      if (this.mode === 'stop') {
        const c = this.clip; c.t += dt; const f = Math.min(S.frames - 1, Math.floor(c.t * S.fps)), r = S.root[f];
        const sy = Math.sin(c.y), cy = Math.cos(c.y);
        this.pos.set(c.o.x + sy * r[0] + cy * r[1], 0, c.o.z + cy * r[0] - sy * r[1]);
        if (f !== c.f && S.heels.includes(f) && NR.audio) NR.audio.fx.heel(); c.f = f;
        if (c.t >= S.frames / S.fps) { this.yaw = c.y + S.turn * Math.PI / 180; this.arrive(); }
      }
      this.group.position.copy(this.pos);
      const cx = cam.position.x - this.pos.x, cz = cam.position.z - this.pos.z;
      this.mesh.rotation.y = Math.atan2(cx, cz);
      let az = Math.atan2(cx, cz) - this.yaw; az = Math.atan2(Math.sin(az), Math.cos(az));
      const k = ((Math.round(az / (Math.PI / 4)) % 8) + 8) % 8; this.sector = k; const ang = String(k * 45);
      if (this.mode === 'walk') {
        const ph = (this.ph0 + this.dist / W.cycle) % 1;
        for (const p of W.plants) if ((this.lastPh < p && ph >= p) || (this.lastPh > ph && (p > this.lastPh || ph >= p))) { if (NR.audio) NR.audio.fx.heel(); }
        this.lastPh = ph; this.frame = Math.floor(ph * W.frames) % W.frames;
        u.map.value = this.tex.walk[ang]; cellRect(u.rect.value, W.angles[ang], this.frame);
      } else if (this.mode === 'stop') { // the clip was painted from 8 angles around her final facing
        let az2 = Math.atan2(cx, cz) - (this.clip.y + S.turn * Math.PI / 180); az2 = Math.atan2(Math.sin(az2), Math.cos(az2));
        const a2 = S.angles ? String((((Math.round(az2 / (Math.PI / 4)) % 8) + 8) % 8) * 45) : '0';
        u.map.value = this.tex.stop[a2]; cellRect(u.rect.value, S.angles ? S.angles[a2] : S, Math.max(0, this.clip.f));
      } else if (k === 0) {
        u.map.value = this.tex.idle; cellRect(u.rect.value, D.idle, Math.floor(this.t * D.idle.fps) % D.idle.frames);
      } else { u.map.value = this.tex.pose; cellRect(u.rect.value, D.pose, D.pose.index[ang]); }
      u.flip.value = 0; u.walk.value = 0;
      if (this.rimSrc) { const cl = Math.hypot(cx, cz) || 1, lx = this.rimSrc.x - this.pos.x, lz = this.rimSrc.z - this.pos.z; u.rimSide.value = (lx * cz - lz * cx) / cl >= 0 ? 1 : -1; u.rimGain.value = 0.55; }
      this.group.visible = this.visible;
    }
    remove() { if (this.group.parent) this.group.parent.remove(this.group); }
  }

  // ================================================================ 3D characters (rigged GLB: 'idle' + 'walk')
  const glbCache = {};
  function loadGLB(url) { if (!glbCache[url]) glbCache[url] = NR.gltf.load(url); return glbCache[url]; }
  // B&W grade: reds on the dress and the lips write alpha < 1 so the post pass keeps their colour
  function keepRed(m) {
    m.onBeforeCompile = (sh) => { sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', '#include <opaque_fragment>\n float rq = diffuseColor.r / max(0.004, max(diffuseColor.g, diffuseColor.b)); gl_FragColor.a = 1.0 - smoothstep(4.0, 7.0, rq) * smoothstep(0.02, 0.05, diffuseColor.r) * 0.95;'); };
    m.customProgramCacheKey = () => 'keepRed'; m.needsUpdate = true;
  }
  class Model3D {
    constructor(gl, level, pos, yaw) {
      this.pos = pos.clone(); this.yaw = yaw || 0; this.path = null; this.speed = 0.85; this.visible = true; this.walking = false; this.onArrive = null; this.t = 0;
      this.group = new T.Group(); this.root = gl.scene; this.group.add(this.root);
      for (const m of gl.materials) if (/red|skin/.test(m.name)) keepRed(m);
      this.root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
      this.mixer = new T.AnimationMixer(this.root); this.acts = {};
      for (const c of gl.animations) this.acts[c.name] = this.mixer.clipAction(c);
      this.cur = null; this.play('idle', 0);
      level.scene.add(this.group); this.sync();
    }
    play(name, fade = 0.3) { const a = this.acts[name]; if (!a || this.cur === a) return; a.reset().setEffectiveWeight(1).fadeIn(fade).play(); if (this.cur) this.cur.fadeOut(fade); this.cur = a; }
    walkTo(points, speed) { this.path = points.map(p => p.clone()); this.speed = speed || 0.85; return new Promise(r => { this.onArrive = r; }); }
    faceTo(p) { this.wantYaw = Math.atan2(p.x - this.pos.x, p.z - this.pos.z); }
    sync() { this.group.position.copy(this.pos); this.group.rotation.y = this.yaw; this.group.visible = this.visible; }
    update(dt) {
      this.t += dt; this.walking = false;
      if (this.path && this.path.length) {
        const tgt = this.path[0], d = V3(tgt.x - this.pos.x, 0, tgt.z - this.pos.z), L = d.length();
        if (L < 0.05) { this.path.shift(); if (!this.path.length) { this.path = null; const f = this.onArrive; this.onArrive = null; if (f) f(); } }
        else { this.pos.addScaledVector(d.normalize(), Math.min(L, this.speed * dt)); const ty = Math.atan2(d.x, d.z); let dy = ty - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 6); this.walking = true; this.wantYaw = null; }
      }
      if (!this.walking && this.wantYaw != null) { let dy = this.wantYaw - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 4); }
      this.play(this.walking ? 'walk' : 'idle');
      if (this.acts.walk) this.acts.walk.timeScale = this.speed / 0.85;
      this.mixer.update(dt); this.sync();
    }
    remove() { if (this.group.parent) this.group.parent.remove(this.group); }
  }
  const MODELS = { vela: 'models/vela_game_v5.glb' };
  async function character(who, level, pos, yaw) {
    if (NR.core.settings.chars === '3d' && MODELS[who]) {
      try { return new Model3D(await loadGLB(NR.ASSET + MODELS[who]), level, pos, yaw); } catch (e) { console.warn('3D model failed, using the painted figure', e); }
    }
    const D = NR.core.settings.chars !== '3d' ? await loadAnim(who) : null;
    if (D) return new Walker(who, level, pos, yaw, D);
    return new Painted(who, level, pos, yaw);
  }

  // ================================================================ enemies
  function mergeColored(parts) { // parts: [geometry(with matrix applied), color]
    let nv = 0, ni = 0; for (const [g] of parts) { nv += g.attributes.position.count; ni += g.index.count; }
    const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), col = new Float32Array(nv * 3), idx = new Uint16Array(ni);
    let vo = 0, io = 0; const c = new T.Color();
    for (const [g, hex] of parts) {
      const n = g.attributes.position.count; pos.set(g.attributes.position.array, vo * 3); nor.set(g.attributes.normal.array, vo * 3);
      c.setHex(hex); for (let i = 0; i < n; i++) { col[(vo + i) * 3] = c.r; col[(vo + i) * 3 + 1] = c.g; col[(vo + i) * 3 + 2] = c.b; }
      const a = g.index.array; for (let i = 0; i < a.length; i++) idx[io + i] = a[i] + vo; io += a.length; vo += n; g.dispose();
    }
    const m = new T.BufferGeometry(); m.setAttribute('position', new T.BufferAttribute(pos, 3)); m.setAttribute('normal', new T.BufferAttribute(nor, 3)); m.setAttribute('color', new T.BufferAttribute(col, 3)); m.setIndex(new T.BufferAttribute(idx, 1)); m.computeBoundingSphere(); return m;
  }
  const B = (w, h, d, x, y, z, rx, ry, rz) => { const g = new T.BoxGeometry(w, h, d); if (rx || ry || rz) g.applyMatrix4(new T.Matrix4().makeRotationFromEuler(new T.Euler(rx || 0, ry || 0, rz || 0))); g.translate(x, y, z); return g; };
  const CYL = (r0, r1, h, x, y, z, seg = 10) => { const g = new T.CylinderGeometry(r0, r1, h, seg); g.translate(x, y, z); return g; };
  const SPH = (r, x, y, z, sy = 1) => { const g = new T.SphereGeometry(r, 10, 8); g.scale(1, sy, 1); g.translate(x, y, z); return g; };
  const figMat = new T.MeshLambertMaterial({ vertexColors: true });
  const STYLES = {
    gale: { suit: 0x26292e, shirt: 0xd8d4c8, tie: 0x8a1010, skin: 0xb08a70, hat: 0x1a1a1c, band: 0x5a1010, pants: 0x1e2024, weapon: 'pistol', brim: 0.2 },
    thug: { suit: 0x3e3428, shirt: 0xa8a090, tie: 0x3e3428, skin: 0xa07a60, hat: 0x2a2620, band: 0x2a2620, pants: 0x2a2826, weapon: 'knife', brim: 0.15, cap: true },
    thugGun: { suit: 0x2e3430, shirt: 0xa8a090, tie: 0x2e3430, skin: 0x9a7058, hat: 0x222220, band: 0x222220, pants: 0x262626, weapon: 'pistol', brim: 0.15, cap: true },
    corpse: { suit: 0x4a4038, shirt: 0xd0ccc0, tie: 0x2a2a40, skin: 0x8a8078, hat: 0x3a342c, band: 0x1a1a1a, pants: 0x2a2826, weapon: 'none', brim: 0.2 },
  };
  function buildFigure(s) {
    const legs = mergeColored([[B(0.17, 0.86, 0.19, -0.1, 0.43, 0), s.pants], [B(0.17, 0.86, 0.19, 0.1, 0.43, 0), s.pants], [B(0.18, 0.07, 0.28, -0.1, 0.035, 0.05), 0x0a0a0a], [B(0.18, 0.07, 0.28, 0.1, 0.035, 0.05), 0x0a0a0a]]);
    // upper body: origin at the hips (y=0.86); built in local coords relative to the hips
    const up = [[B(0.48, 0.64, 0.27, 0, 0.32, 0), s.suit], [B(0.14, 0.28, 0.02, 0, 0.47, 0.135), s.shirt], [B(0.045, 0.24, 0.025, 0, 0.44, 0.145), s.tie],
      [B(0.07, 0.3, 0.03, -0.075, 0.46, 0.14, 0, 0, 0.35), s.suit], [B(0.07, 0.3, 0.03, 0.075, 0.46, 0.14, 0, 0, -0.35), s.suit],
      [B(0.13, 0.6, 0.14, -0.31, 0.3, 0, 0, 0, 0.06), s.suit], [B(0.09, 0.1, 0.1, -0.33, -0.03, 0.0), s.skin],
      [CYL(0.06, 0.07, 0.1, 0, 0.68, 0, 8), s.skin], [SPH(0.115, 0, 0.8, 0.0, 1.12), s.skin], [B(0.12, 0.03, 0.02, 0, 0.84, 0.105), 0x1a1210]];
    if (s.cap) up.push([CYL(0.125, 0.13, 0.08, 0, 0.92, 0, 12), s.hat], [B(0.2, 0.02, 0.12, 0, 0.885, 0.12), s.hat]);
    else up.push([CYL(0.11, 0.125, 0.13, 0, 0.98, 0, 12), s.hat], [CYL(0.125, 0.125, 0.03, 0, 0.935, 0, 12), s.band], [CYL(s.brim, s.brim, 0.015, 0, 0.915, 0, 14), s.hat]);
    const upper = mergeColored(up);
    // weapon arm: pivot at the right shoulder, extends along +z
    const ar = [[B(0.13, 0.13, 0.5, 0, 0, 0.23), s.suit], [B(0.09, 0.1, 0.1, 0, 0, 0.5), s.skin]];
    if (s.weapon === 'pistol') ar.push([B(0.035, 0.06, 0.2, 0, 0.04, 0.6), 0x101012], [B(0.03, 0.09, 0.04, 0, -0.03, 0.52), 0x101012]);
    if (s.weapon === 'knife') ar.push([B(0.02, 0.03, 0.2, 0, 0.0, 0.64), 0xc8ccd0], [B(0.03, 0.04, 0.08, 0, 0, 0.53), 0x2a1a10]);
    const arm = mergeColored(ar);
    const g = new T.Group(), lm = new T.Mesh(legs, figMat), um = new T.Mesh(upper, figMat), am = new T.Mesh(arm, figMat);
    um.position.y = 0.86; am.position.set(0.31, 0.56, 0); um.add(am);
    for (const m of [lm, um, am]) { m.castShadow = true; m.receiveShadow = false; }
    g.add(lm, um);
    return { group: g, legs: lm, upper: um, arm: am };
  }

  let nextId = 1;
  class Enemy {
    constructor(level, o) {
      this.id = nextId++; this.level = level; this.type = o.type || 'gunman'; this.kind = o.kind || 'human';
      this.style = o.style || (this.type === 'thug' ? 'thug' : 'gale');
      this.variant = this.kind === 'artificial' ? 'synth' : this.style === 'thugGun' ? 'thug_c' : this.style === 'thug' ? (o.flashlight ? 'thug_b' : 'thug_a') : ['gale_a', 'gale_b', 'gale_c'][Enemy.galeN++ % 3];
      this.hs = this.variant === 'synth' ? 1.1 : 1; // the artificial man stands 2 m tall
      const f = buildFigure(STYLES[this.style]); Object.assign(this, f);
      this.pos = o.pos.clone(); this.yaw = o.yaw || 0; this.hp = o.hp || (this.type === 'thug' ? 70 : 100); this.maxHp = this.hp;
      this.state = o.dormant ? 'dormant' : 'idle'; this.t = 0; this.cover = null; this.crouch = 0; this.peekOff = V3(0, 0, 0); this.peekAmt = 0;
      this.shots = 0; this.fireT = 0; this.flinch = 0; this.dead = false; this.deadT = 0; this.flankT = 6 + Math.random() * 6; this.speed = this.type === 'thug' ? 3.5 : 3.0;
      this.aimT = 0; this.atkT = 0; this.accuracy = o.accuracy || 1; this.dmg = o.dmg || (this.type === 'thug' ? 13 : 15); this.seenT = 0; this.lastSeen = null; this.suppressed = false; this.entry = o.entry ? o.entry.map(p => p.clone()) : null;
      this.drops = o.drops || 0;
      if (this.type === 'thug' && o.flashlight) {
        const cone = new T.Mesh(new T.ConeGeometry(0.5, 3.0, 12, 1, true), new T.MeshBasicMaterial({ color: 0xfff0c0, transparent: true, opacity: 0.07, blending: T.AdditiveBlending, depthWrite: false, side: T.DoubleSide }));
        cone.rotation.x = -Math.PI / 2; cone.position.set(0, 0, 1.9); this.upper.children[0].add(cone); NR.world.glow(0xfff0c0, 0.5, 0, 0, 0.4, this.upper.children[0]);
        this.arm.geometry = mergeColored([[B(0.13, 0.13, 0.5, 0, 0, 0.23), STYLES.thug.suit], [B(0.07, 0.07, 0.22, 0, 0, 0.55), 0x303030]]);
      }
      // muzzle glint: telegraphs a shot ~0.4 s before it comes
      this.glint = NR.world.glow(0xfff6e0, 0.32, 0, 0.05, 0.74, this.arm); this.glint.visible = false; this.glint.material.depthTest = true;
      this.group.position.copy(this.pos); this.group.rotation.y = this.yaw; level.scene.add(this.group);
      this.fallAxis = V3(1, 0, 0); this.prev = this.pos.clone(); this.vel = V3(0, 0, 0);
      this.cr = null; const tpl = NR.cast && NR.cast.ready(this.variant);
      if (tpl) this.useRig(tpl); else if (NR.cast) NR.cast.family(NR.ASSET + NR.cast.URL[NR.cast.FAMILY[this.variant]]).then(t => { if (!this.removed && t) this.useRig(t); }, () => {});
    }
    useRig(tpl) { // swap the block figure for the rigged person
      const r = new NR.cast.Rig(tpl, this.variant); this.cr = r;
      for (const m of [this.legs, this.upper]) this.group.remove(m);
      this.group.add(r.root);
      if (this.glint && this.glint.parent) this.glint.parent.remove(this.glint);
      this.glint = NR.world.glow(0xfff6e0, 0.32, 0, 0, 0, r.muzzle || r.bones.handR); this.glint.visible = false; this.glint.material.depthTest = true;
      if (this.type === 'thug' && r.lampTip) {
        let cone = null; this.upper.traverse(c => { if (c.isMesh && c.geometry.type === 'ConeGeometry') cone = c; });
        if (cone) { cone.parent.remove(cone); this.group.add(cone); cone.rotation.set(0, 0, 0); this.cone = cone; }
        NR.world.glow(0xfff0c0, 0.5, 0, 0, 0, r.lampTip);
      }
      if (this.dead) { r.full(this.deathClip || 'die_back', 0); r.update(5); }
    }
    get headY() { return 1.66 * this.hs; }
    get eye() { return V3(this.pos.x, 1.5 * this.hs - 0.48 * this.crouch, this.pos.z).add(this.peekOff); }
    get headC() { return V3(this.pos.x + this.peekOff.x, this.headY - 0.45 * this.crouch, this.pos.z + this.peekOff.z); }
    // ray hit test against head sphere and body cylinder; returns {t, head, point}
    hitTest(o, d, maxT) {
      if (this.dead) return null;
      const hc = this.headC, oc = o.clone().sub(hc), b = oc.dot(d), c = oc.lengthSq() - 0.15 * 0.15, disc = b * b - c;
      let best = null;
      if (disc >= 0) { const t = -b - Math.sqrt(disc); if (t > 0 && t < maxT) best = { t, head: true }; }
      const bx = this.pos.x + this.peekOff.x, bz = this.pos.z + this.peekOff.z, top = 1.5 * this.hs - 0.45 * this.crouch, r = 0.27;
      const ox = o.x - bx, oz = o.z - bz, A = d.x * d.x + d.z * d.z, Bq = 2 * (ox * d.x + oz * d.z), Cq = ox * ox + oz * oz - r * r, D = Bq * Bq - 4 * A * Cq;
      if (A > 1e-9 && D >= 0) { const t = (-Bq - Math.sqrt(D)) / (2 * A); if (t > 0 && t < maxT) { const y = o.y + d.y * t; if (y > 0 && y < top && (!best || t < best.t)) best = { t, head: false }; } }
      if (best) best.point = o.clone().addScaledVector(d, best.t);
      return best;
    }
    damage(amount, point, dir, head) {
      if (this.dead) return false;
      this.hp -= amount; this.flinch = 0.28; this.aimT = 0; this.mat && 0;
      if (this.cr) { // the wound sits on the body surface, on the bone that was hit; the body reacts to the side it was hit from
        const b = this.cr.bones, part = head ? b.head : point.y < 0.86 * this.hs ? (this.legSide(point) > 0 ? b.thighL : b.thighR) : b.spine2;
        const c = part.getWorldPosition(V3(0, 0, 0)); if (head) c.y += 0.1;
        const out = V3(point.x - c.x, 0, point.z - c.z); if (out.lengthSq() < 1e-6) out.set(-dir.x, 0, -dir.z); out.normalize();
        const p2 = c.clone().addScaledVector(out, head ? 0.1 : part === b.spine2 ? 0.14 : 0.08); p2.y = head ? c.y : Math.min(Math.max(point.y, c.y - 0.25), c.y + 0.3);
        NR.fx.blood(p2, dir, this.kind, head ? 1.6 : 1.0, part);
        const f = V3(Math.sin(this.yaw), 0, Math.cos(this.yaw)), side = f.x * dir.z - f.z * dir.x;
        this.cr.additive(Math.abs(side) < 0.5 ? 'hit_front' : side > 0 ? 'hit_left' : 'hit_right', head ? 1.3 : 1);
      } else NR.fx.blood(point, dir, this.kind, head ? 1.6 : 1.0, head ? this.upper : (point.y < 0.86 ? this.legs : this.upper));
      if (this.state === 'dormant' || this.state === 'idle') this.alert();
      if (this.hp <= 0) { this.die(dir, head); return true; }
      return false;
    }
    legSide(p) { const r = V3(Math.cos(this.yaw), 0, -Math.sin(this.yaw)); return -((p.x - this.pos.x) * r.x + (p.z - this.pos.z) * r.z); }
    alert() { if (this.dead) return; if (this.state === 'dormant' || this.state === 'idle') { this.state = this.entry ? 'enter' : (this.type === 'thug' ? 'rush' : 'engage'); this.t = 0; } }
    die(dir, head) {
      this.dead = true; this.state = 'dead'; this.deadT = 0; if (this.cover) { this.cover.taken = null; this.cover = null; }
      this.fallAxis = V3(dir.z, 0, -dir.x).normalize(); this.fallFrom = this.group.quaternion.clone();
      const fwd = Math.sin(this.yaw) * dir.x + Math.cos(this.yaw) * dir.z; // > 0: shot from behind
      // which fall: from a crouch he folds where he is; shot from behind he pitches forward; from the front he goes back,
      // buckles to his knees or slips. The fall must have room: rotate it away from tables and walls when it does not.
      const r_ = Math.random();
      this.deathClip = this.crouch > 0.5 ? 'die_crouch' : fwd > 0.3 ? 'die_fwd' : (head && r_ < 0.4) || r_ < 0.2 ? 'die_slip' : r_ < 0.55 ? 'die_kneel' : 'die_back';
      if (this.cr && !this.cr.has(this.deathClip)) this.deathClip = fwd > 0.3 ? 'die_fwd' : 'die_back';
      const back = this.deathClip === 'die_back' || this.deathClip === 'die_slip';
      const L_ = this.level, reach = this.deathClip === 'die_crouch' ? 1.4 : 1.9, room = (yaw) => { const d = V3(Math.sin(yaw), 0, Math.cos(yaw)).multiplyScalar(back ? -1 : 1); return [0.25, 0.6, 0.85].every(h => !L_.ray(V3(this.pos.x, h, this.pos.z), d, reach)) && !L_.blockedAt(this.pos.x + d.x * reach * 0.7, this.pos.z + d.z * reach * 0.7, 0.3); };
      this.deathYaw = this.yaw;
      for (const off of [0, 0.5, -0.5, 1.0, -1.0, 1.6, -1.6, Math.PI]) { if (room(this.yaw + off)) { this.deathYaw = this.yaw + off; break; } }
      if (this.cr) { this.group.rotation.y = this.deathYaw; this.cr.full(this.deathClip, this.crouch > 0.3 ? 0.3 : 0.12, true); this.glint.visible = false; if (this.cone) this.cone.visible = false; }
      NR.bus.emit('enemyDown', { enemy: this, head });
    }
    update(dt, P) {
      const L = this.level; this.t += dt;
      if (this.dead && this.cr) {
        this.deadT += dt; this.cr.update(dt);
        if (!this.pooled && this.deadT > 1.1) { this.pooled = true; const h = this.cr.bones.hips.getWorldPosition(V3(0, 0, 0)); NR.fx.pool(V3(h.x, 0, h.z), this.kind); }
        return;
      }
      if (this.dead) {
        if (this.deadT < 1) {
          this.deadT += dt; const k = Math.min(1, this.deadT / 0.55), e = k * k;
          this.group.quaternion.copy(this.fallFrom).premultiply(new T.Quaternion().setFromAxisAngle(this.fallAxis, e * Math.PI / 2 * 0.98));
          this.group.position.set(this.pos.x, 0.02 * k, this.pos.z);
          if (this.deadT >= 1 || (k >= 1 && !this.pooled)) { if (!this.pooled) { this.pooled = true; const fp = this.pos.clone().addScaledVector(V3(-this.fallAxis.z, 0, this.fallAxis.x), -0.0); NR.fx.pool(V3(this.pos.x + (this.group.localToWorld(V3(0, 1, 0)).x - this.pos.x) * 0.6, 0, this.pos.z + (this.group.localToWorld(V3(0, 1, 0)).z - this.pos.z) * 0.6), this.kind); void fp; } }
        }
        return;
      }
      if (this.state === 'dormant') return;
      const toP = V3(P.pos.x - this.pos.x, 0, P.pos.z - this.pos.z), dist = toP.length(); toP.normalize();
      const pHead = V3(P.pos.x, P.pos.y + C.EYE - 0.1, P.pos.z), pChest = V3(P.pos.x, P.pos.y + 1.15, P.pos.z);
      if (this.flinch > 0) this.flinch -= dt;
      let wantYaw = Math.atan2(toP.x, toP.z), moveTo = null, crouchT = 0, peekT = 0, aiming = false, glint = false;

      if (this.state === 'idle') { if (dist < 22 && L.los(this.eye, pHead)) this.alert(); }
      else if (this.state === 'enter') { // walk in through a door before fighting
        if (this.entry.length) { moveTo = this.entry[0]; if (V3(moveTo.x - this.pos.x, 0, moveTo.z - this.pos.z).length() < 0.3) this.entry.shift(); }
        else { this.entry = null; this.state = this.type === 'thug' ? 'rush' : 'engage'; }
      }
      else if (this.state === 'rush') {
        if (this.recover > 0) { this.recover -= dt; moveTo = V3(this.pos.x - toP.x, 0, this.pos.z - toP.z); } else { moveTo = P.pos; if (dist < 1.35) { this.state = 'melee'; this.atkT = 0.8; } }
      }
      else if (this.state === 'melee') {
        this.atkT -= dt; aiming = true;
        if (this.atkT <= 0) { if (dist < 1.7 && this.flinch <= 0) NR.bus.emit('playerHit', { dmg: this.dmg, from: this.pos.clone(), melee: true }); this.state = 'rush'; this.atkT = 0; this.t = 0; this.recover = 0.6; }
        if (dist > 2.2) this.state = 'rush';
      }
      else if (this.state === 'engage') {
        this.cover = this.pickCover(P, false); this.state = this.cover ? 'move' : 'stand'; this.t = 0;
      }
      else if (this.state === 'move') {
        if (!this.cover) { this.state = 'stand'; }
        else { moveTo = this.cover.pos; if (V3(moveTo.x - this.pos.x, 0, moveTo.z - this.pos.z).length() < 0.2) { this.state = 'cover'; this.t = 0; this.wait = 0.8 + Math.random() * 1.6; } if (this.t > 7) { this.state = 'stand'; this.t = 0; } }
      }
      else if (this.state === 'cover') {
        if (!this.coverGood(P)) { this.cover.taken = null; this.cover = null; this.state = 'engage'; }
        else {
          crouchT = this.cover.low ? 1 : 0; wantYaw = Math.atan2(-this.cover.n.x, -this.cover.n.z);
          if (this.t > this.wait) { this.state = 'peek'; this.t = 0; this.suppressed = false; this.shots = 1 + Math.floor(Math.random() * 3); this.aimT = 0.5 + Math.random() * 0.3; this.peekDir = this.findPeek(P); }
          this.flankT -= dt; if (this.flankT <= 0 && Enemy.flankers < 1) { const c = this.pickCover(P, true); if (c) { Enemy.flankers++; this.flanking = true; this.cover.taken = null; this.cover = c; this.state = 'move'; this.t = 0; } this.flankT = 7 + Math.random() * 5; }
        }
      }
      else if (this.state === 'peek' || this.state === 'stand') {
        if (this.state === 'peek') { if (this.cover && this.cover.low) crouchT = 0; else if (this.peekDir) peekT = 1; }
        const see = L.los(this.eye, pChest) || L.los(this.eye, pHead);
        aiming = true;
        if (see && this.flinch <= 0) {
          if (this.seenT <= 0) this.aimT = Math.max(this.aimT, 0.75 + Math.random() * 0.45 + (P.drawn ? 0 : 0.35)); // a holstered man gets a beat longer // reaction delay after losing sight
          this.seenT = 2.5; this.lastSeen = pChest.clone();
          this.aimT -= dt; glint = this.aimT < 0.42;
          if (this.aimT <= 0) { this.fire(P, dist); this.shots--; this.aimT = 0.6 + Math.random() * 0.4; if (this.shots <= 0) { this.backToCover(); } }
        } else {
          // suppress: keep the player's head down at the last place they were seen, while a partner flanks
          if (this.lastSeen && !this.suppressed && this.t > 0.5 && (Enemy.flankers > 0 || Math.random() < 0.02)) { this.suppressed = true; this.fire(P, dist, this.lastSeen); }
          if (this.t > 1.4) { this.backToCover(true); }
        }
        if (this.state === 'stand' && this.t > 3) { this.state = 'engage'; this.t = 0; }
      }
      if (this.seenT > 0) this.seenT -= dt;
      this.glint.visible = glint && Math.sin(this.t * 60) > -0.3;
      if (this.flanking && this.state !== 'move') { this.flanking = false; Enemy.flankers = Math.max(0, Enemy.flankers - 1); }

      // movement with obstacle slide
      if (moveTo && this.flinch <= 0) {
        const d = V3(moveTo.x - this.pos.x, 0, moveTo.z - this.pos.z), Ld = d.length();
        if (Ld > 0.05) { this.pos.addScaledVector(d.normalize(), Math.min(Ld, this.speed * dt)); wantYaw = Math.atan2(d.x, d.z); if (this.state === 'rush' && dist < 6) wantYaw = Math.atan2(toP.x, toP.z); }
        L.collide(this.pos, 0.3, 0, false);
        for (const o of Enemy.all) if (o !== this && !o.dead) { const dx = this.pos.x - o.pos.x, dz = this.pos.z - o.pos.z, dd = Math.hypot(dx, dz); if (dd < 0.6 && dd > 1e-4) { this.pos.x += dx / dd * (0.6 - dd) * 0.5; this.pos.z += dz / dd * (0.6 - dd) * 0.5; } }
      }
      // pose
      let dy = wantYaw - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); this.yaw += dy * Math.min(1, dt * 10);
      this.crouch += (crouchT - this.crouch) * Math.min(1, dt * 9);
      this.peekAmt += (peekT - this.peekAmt) * Math.min(1, dt * 8);
      if (this.peekDir) this.peekOff.copy(this.peekDir).multiplyScalar(0.75 * this.peekAmt); else this.peekOff.multiplyScalar(0.8);
      if (this.cr) { this.animate(dt, P, aiming, pChest, dist); return; }
      const walk = moveTo ? Math.sin(this.t * 11) : 0;
      this.group.position.set(this.pos.x + this.peekOff.x, Math.abs(walk) * 0.03, this.pos.z + this.peekOff.z); this.group.rotation.y = this.yaw;
      this.legs.scale.y = 1 - 0.5 * this.crouch; this.upper.position.y = 0.86 - 0.45 * this.crouch; this.upper.rotation.x = this.crouch * 0.25 + (this.flinch > 0 ? -0.2 : 0);
      this.upper.rotation.z = this.flinch > 0 ? Math.sin(this.t * 40) * 0.08 : 0;
      const armDown = 1.25, armAim = -0.02 - (aiming ? Math.atan2(pChest.y - this.eye.y, dist) : 0);
      const at = aiming || this.state === 'rush' ? armAim : armDown; this.arm.rotation.x += (at - this.arm.rotation.x) * Math.min(1, dt * 12);
      if (this.state === 'melee') this.arm.rotation.x = this.atkT > 0.2 ? -1.6 - Math.sin(this.t * 30) * 0.05 : -1.6 + (0.2 - this.atkT) * 12; // raised knife telegraphs the swing
    }
    animate(dt, P, aiming, pChest, dist) {
      const r = this.cr, k = r.kind;
      this.vel.set((this.pos.x - this.prev.x) / Math.max(dt, 1e-3), 0, (this.pos.z - this.prev.z) / Math.max(dt, 1e-3)); this.prev.copy(this.pos);
      this.group.position.set(this.pos.x + this.peekOff.x, 0, this.pos.z + this.peekOff.z); this.group.rotation.y = this.yaw;
      const sp = this.vel.length(), fwd = this.vel.x * Math.sin(this.yaw) + this.vel.z * Math.cos(this.yaw);
      const alerted = this.state !== 'dormant' && this.state !== 'idle';
      if (this.state === 'melee') {
        if (this.lastState !== 'melee') r.full(r.has('slash') ? 'slash' : 'hold_' + k, 0.08, true);
      } else {
        let low = 'idle', ts = 1;
        if (sp > 0.5 && this.state !== 'peek') {
          if (fwd >= -0.2 * sp) { low = sp > 2.0 ? 'run' : 'walk'; ts = sp / r.speedOf(low); }
          else { low = 'walk'; ts = -sp / r.speedOf('walk'); }
        } else if (this.crouch > 0.5) low = 'crouch';
        if (this.lastState === 'melee') { r.layerName.L = ''; r.layerName.U = ''; }
        const fadeL = (low === 'crouch') !== (r.layerName.L === 'crouch') ? 0.35 : 0.22; // crouch <-> stand blends over 0.35 s
        r.play('L', low, fadeL, false, ts);
        let up = low;
        if (alerted && k !== 'none') up = aiming && r.has('aim_' + k) ? 'aim_' + k : 'hold_' + k;
        r.play('U', up, fadeL > 0.3 ? 0.35 : 0.2, false, up === low ? ts : 1);
      }
      this.lastState = this.state;
      r.update(dt);
      if (aiming && this.state !== 'melee') { // pitch the chest onto the target
        const f = V3(Math.sin(this.yaw), 0, Math.cos(this.yaw)), ax = V3(f.z, 0, -f.x);
        const pitch = Math.atan2(pChest.y - this.eye.y, Math.max(dist, 0.5));
        r.bend(r.bones.chest, ax, -pitch * 0.85);
      }
      if (this.flinch > 0) r.bend(r.bones.head, V3(0, 1, 0), Math.sin(this.t * 40) * 0.06);
      if (this.state !== 'melee') r.footLock(dt, r.layerName.L === 'run' || r.layerName.L === 'walk' || r.layerName.L === 'idle', 0, r.layerName.L === 'idle' ? 0.16 : 0.6);
      r.lod(Math.hypot(P.pos.x - this.pos.x, P.pos.z - this.pos.z) > 13);
      if (this.cone && r.lampTip) { // the flashlight beam follows the lamp in his hand
        const tip = r.lampTip.getWorldPosition(V3(0, 0, 0)), hand = r.bones.handL.getWorldPosition(V3(0, 0, 0));
        const d = tip.clone().sub(hand).normalize(); this.group.worldToLocal(tip);
        const dl = d.applyQuaternion(this.group.quaternion.clone().invert());
        this.cone.quaternion.setFromUnitVectors(V3(0, -1, 0), dl); this.cone.position.copy(tip).addScaledVector(dl, 1.5);
      }
    }
    backToCover(failed) { if (this.cover) { this.state = 'cover'; this.t = 0; this.wait = 1.0 + Math.random() * 1.8; if (failed) this.flankT = Math.min(this.flankT, 1.5); } else { this.state = 'engage'; this.t = 0; } }
    coverGood(P) { if (!this.cover) return false; const d = V3(P.pos.x - this.cover.pos.x, 0, P.pos.z - this.cover.pos.z); const L = d.length(); if (L < 2.2) return false; return d.normalize().dot(this.cover.n) < -0.25; }
    findPeek(P) { // tall cover: step left or right to see the player
      if (!this.cover || this.cover.low) return null; const n = this.cover.n, tan = V3(-n.z, 0, n.x);
      for (const s of [1, -1]) { const p = this.cover.pos.clone().addScaledVector(tan, 0.75 * s); if (this.level.los(V3(p.x, 1.5, p.z), V3(P.pos.x, P.pos.y + 1.4, P.pos.z)) && !this.level.blockedAt(p.x, p.z, 0.25)) return tan.clone().multiplyScalar(s); }
      return null;
    }
    pickCover(P, flank) {
      let best = null, bs = 1e9; const L = this.level;
      const pa = Math.atan2(this.pos.x - P.pos.x, this.pos.z - P.pos.z);
      for (const c of L.covers) {
        if (c.taken && c.taken !== this) continue;
        const d = V3(P.pos.x - c.pos.x, 0, P.pos.z - c.pos.z), dp = d.length(); if (dp < 3.5 || dp > 20) continue;
        if (d.normalize().dot(c.n) > -0.35) continue;
        const dm = Math.hypot(c.pos.x - this.pos.x, c.pos.z - this.pos.z); if (dm > 14) continue;
        let s = dm + Math.abs(dp - 8) * 0.5 + Math.random() * 1.5;
        if (flank) { const ca = Math.atan2(c.pos.x - P.pos.x, c.pos.z - P.pos.z); let da = Math.abs(Math.atan2(Math.sin(ca - pa), Math.cos(ca - pa))); if (da < 0.6 || c === this.cover) continue; s -= da * 3; }
        if (!L.los(V3(this.pos.x, 0.5, this.pos.z), V3(c.pos.x, 0.5, c.pos.z))) s += 6;
        if (s < bs) { bs = s; best = c; }
      }
      if (best) { if (this.cover && this.cover !== best) this.cover.taken = null; best.taken = this; }
      return best;
    }
    fire(P, dist, suppressAt) {
      const muzzle = this.cr ? (this.cr.muzzle || this.cr.bones.handR).getWorldPosition(V3(0, 0, 0)) : this.arm.localToWorld(V3(0, 0.04, 0.72));
      if (this.cr) this.cr.additive('recoil', this.cr.kind === 'tommy' ? 0.6 : 1);
      // accuracy falls off with range, a moving target and slow-mo; the first shot of a peek is the steadiest
      let ch = (0.72 - dist * 0.028) * this.accuracy; if (P.moving) ch *= 0.6; if (P.focus > 0) ch *= 0.75; ch = NR.clamp(ch, 0.1, 0.72);
      const hit = !suppressAt && Math.random() < ch, tgt = suppressAt ? suppressAt.clone() : V3(P.pos.x, P.pos.y + 1.2, P.pos.z);
      if (suppressAt) { const h = this.level.ray(muzzle, tgt.clone().sub(muzzle).normalize(), muzzle.distanceTo(tgt)); if (h) { tgt.copy(h.point); NR.fx.impact(h.point, h.normal); } }
      if (!hit) { tgt.x += (Math.random() - 0.5) * 1.6; tgt.y += (Math.random() - 0.3) * 1.0; tgt.z += (Math.random() - 0.5) * 1.6; }
      NR.fx.tracer(muzzle, tgt); NR.fx.muzzle(muzzle, 0.8);
      NR.bus.emit('enemyShot', { pos: muzzle, hit });
      if (hit) NR.bus.emit('playerHit', { dmg: this.dmg, from: this.pos.clone() });
      else if (!suppressAt && NR.core) NR.bus.emit('nearMiss', { from: this.pos.clone() });
    }
    remove() { this.removed = true; if (this.group.parent) this.group.parent.remove(this.group); if (this.cover) this.cover.taken = null; }
  }
  Enemy.all = []; Enemy.flankers = 0; Enemy.galeN = 0;
  function spawn(level, o) { const e = new Enemy(level, o); Enemy.all.push(e); return e; }
  function clear() { for (const e of Enemy.all) e.remove(); Enemy.all = []; Enemy.flankers = 0; Enemy.galeN = 0; }
  function corpse(level, pos, yaw) { // Miles Corran on his back, his fedora fallen beside him
    const g = new T.Group(); level.scene.add(g);
    const fb = corpseBlocks(level, pos, yaw); fb.group.visible = false;
    const show = (tpl) => {
      if (!g.parent || !tpl) return;
      // he lies under the alley's work light: a darker, rougher wet coat so the spot does not blow him out to yellow
      if (!tpl.milesTuned) { tpl.milesTuned = true; for (const m of tpl.mats) m.color.setRGB(0.34, 0.33, 0.35); }
      const r = new NR.cast.Rig(tpl, 'miles'); r.full('dead_pose', 0, true); r.update(2); r.lod(false);
      g.add(r.root); g.rotation.y = yaw; g.position.copy(pos); g.updateMatrixWorld(true);
      const h = r.bones.hips.getWorldPosition(V3(0, 0, 0)); g.position.x += pos.x - h.x; g.position.z += pos.z - h.z; g.updateMatrixWorld(true);
      if (r.hat) { // the fedora lies on the ground beside his head
        const hp = r.bones.head.getWorldPosition(V3(0, 0, 0)); r.hat.parent.remove(r.hat);
        const hat = new T.Group(); hat.add(r.hat); r.hat.position.set(0, 0, 0); r.hat.quaternion.identity(); r.hat.updateMatrix();
        const bb = new T.Box3().setFromObject(r.hat), c = bb.getCenter(V3(0, 0, 0)); r.hat.position.set(-c.x, -bb.min.y, -c.z);
        hat.position.set(hp.x + 0.35 * Math.cos(yaw), 0.0, hp.z - 0.35 * Math.sin(yaw)); hat.rotation.set(0, yaw + 0.7, 0.08); level.scene.add(hat); g.userData.hat = hat;
      }
      g.userData.rig = r; if (fb.group.parent) fb.group.parent.remove(fb.group);
    };
    const t = NR.cast && NR.cast.ready('miles');
    if (t) show(t); else if (NR.cast) { fb.group.visible = true; NR.cast.family(NR.ASSET + NR.cast.URL.miles).then(show, () => {}); } else fb.group.visible = true;
    return { group: g };
  }
  function corpseBlocks(level, pos, yaw) { const f = buildFigure(STYLES.corpse); f.group.position.copy(pos); f.group.rotation.set(-Math.PI / 2 + 0.05, yaw, 0, 'YXZ'); f.group.position.y = 0.14; f.arm.rotation.x = 0.4; level.scene.add(f.group); return f; }

  if (NR.cast) setTimeout(() => NR.cast.preload(), 300); // fetch the cast while the title is up
  NR.actors = { Painted, Walker, loadAnim, Model3D, character, loadGLB, MODELS, Enemy, spawn, clear, corpse, buildFigure, preload, get enemies() { return Enemy.all; } };
})();
