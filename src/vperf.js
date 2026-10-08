// NEON RAIN video performances: AI-filmed loops (LTX image-to-video, matted, looped) on the painted billboards and in the
// interrogation close-up. Chrome/Firefox/Android play VP9 WebM with alpha; WebKit (iOS, Safari) plays an H.264 MP4 with the
// alpha stacked under the colour, unpacked in the shader. The clips are filmed from the front, so they show only while the
// camera sees her from the front and frames her waist-up (cinematic beats); the painted angles cover every other view.
// Assets: assets/video/*. Build: tools/video_perf/. URL ?vp=webm|stack|off forces a path.
(function () {
  const T = THREE, UA = navigator.userAgent;
  const iOS = /iPhone|iPad|iPod/.test(UA) || (/Macintosh/.test(UA) && navigator.maxTouchPoints > 1);
  const webkit = /AppleWebKit/.test(UA) && !/Chrome|Chromium|CriOS|FxiOS|Edg|Android/.test(UA);
  const probe = document.createElement('video');
  const canWebm = !!probe.canPlayType('video/webm; codecs="vp9"');
  const canMp4 = !!probe.canPlayType('video/mp4; codecs="avc1.4D401E"');
  const force = new URLSearchParams(location.search).get('vp');
  const MODE = force === 'off' || force === 'webm' || force === 'stack' ? force : (iOS || webkit || !canWebm) ? 'stack' : 'webm';
  const BASE = NR.ASSET + 'video/';
  // clips that exist in assets/video (kept in step with tools/video_perf); anything else stays on the painted figure, no request made
  const AVAIL = new Set(['vela_idle', 'vela_talk', 'dolores_idle', 'dolores_warm', 'dolores_guarded', 'dolores_cold', 'vela_smoke', 'vela_stole', 'vela_full', 'vela_full_640']);

  // framing per clip, in frame fractions: top = top of the hair, chin = bottom of the chin, cx = centre of the face
  const FAV1 = { top: 0.037, chin: 0.32, cx: 0.5 };
  const CLIPS = {
    vela_idle: Object.assign({ file: 'vela_idle' }, FAV1),
    vela_talk: Object.assign({ file: 'vela_talk' }, FAV1),
    vela_smoke: Object.assign({ file: 'vela_smoke' }, FAV1),
    vela_stole: { file: 'vela_stole', top: 0.065, chin: 0.28, cx: 0.5, once: true },
    vela_full: { file: 'vela_full', top: 0.072, foot: 0.973, cx: 0.5, full: true }, // full-length idle for the open lens (1280 px)
    vela_full_sm: { file: 'vela_full_640', top: 0.072, foot: 0.973, cx: 0.5, full: true }, // same clip, 640 px: used when she covers < ~850 render px (no shimmer from 2x minification)
    dolores_idle: { file: 'dolores_idle', top: 0.03, chin: 0.215, cx: 0.48 },
  };
  const PANEL = { dolores: { warm: 'dolores_warm', guarded: 'dolores_guarded', cold: 'dolores_cold' } };
  const HEAD = 0.27; // metres from the top of the hair to the chin
  const FRAMED_FOV = 27, OPEN_FOV = 74; // 32 deg: at ~2 m the waist-up frame fills a portrait phone and its lower edge stays off screen

  const vids = {};
  // WebKit (and iOS Safari) only paint frames for a <video> that sits in the document; park them, invisible, in a 1 px box
  let park = null;
  function parkVideo(v) { if (!park) { park = document.createElement('div'); park.setAttribute('aria-hidden', 'true'); park.style.cssText = 'position:fixed;left:0;top:0;width:1px;height:1px;overflow:hidden;opacity:0.01;pointer-events:none;z-index:-1'; document.body.appendChild(park); } park.appendChild(v); }
  function video(file, stacked, loop) {
    const key = file + (stacked ? '_stack' : '') + (loop ? '' : '_once');
    if (vids[key]) return vids[key];
    const v = document.createElement('video');
    v.muted = true; v.defaultMuted = true; v.loop = !!loop; v.playsInline = true; v.preload = 'auto';
    v.setAttribute('playsinline', ''); v.setAttribute('webkit-playsinline', ''); v.setAttribute('muted', '');
    v.src = BASE + file + (stacked ? '_stack.mp4' : '.webm');
    v.addEventListener('error', () => { v.failed = true; console.warn('[vperf] video failed', v.src); }); parkVideo(v);
    // WebKit uploads a <video> straight into a WebGL2 texture as empty pixels, so on that path each new frame is copied through a 2D canvas
    let tex, cv = null, g = null, lastT = -1;
    if (stacked) { cv = document.createElement('canvas'); cv.width = 2; cv.height = 2; g = cv.getContext('2d'); tex = new T.CanvasTexture(cv); }
    else tex = new T.VideoTexture(v);
    tex.colorSpace = T.NoColorSpace; tex.minFilter = T.LinearFilter; tex.magFilter = T.LinearFilter; tex.generateMipmaps = false;
    const pump = () => { if (!cv || v.readyState < 2 || !v.videoWidth) return; if (cv.width !== v.videoWidth || cv.height !== v.videoHeight) { cv.width = v.videoWidth; cv.height = v.videoHeight; tex.dispose(); lastT = -1; }
      if (v.currentTime === lastT) return; lastT = v.currentTime; g.drawImage(v, 0, 0); tex.needsUpdate = true; };
    return (vids[key] = { v, tex, stacked: !!stacked, file, pump });
  }
  const live = (c) => c && !c.v.failed && c.v.readyState >= 2;
  function play(c) { if (c && c.v.paused) { const p = c.v.play(); if (p && p.catch) p.catch(() => {}); } }

  // ---------------------------------------------------------------- billboard material
  const SAMPLE = `
    vec4 samp(sampler2D m, float st, vec2 uv) {
      if (st > 0.5) { vec3 c = texture2D(m, vec2(uv.x, 0.5 + uv.y * 0.5)).rgb; float a = texture2D(m, vec2(uv.x, uv.y * 0.5)).g; return vec4(c, a); }
      return texture2D(m, uv); }
    vec4 both(vec2 uv) { vec4 a = samp(map, st1, uv); if (mixK <= 0.001) return a; vec4 b = samp(map2, st2, uv); return mix(a, b, mixK); }`;
  const VERT = 'varying vec2 vUv; varying vec3 vW; varying float vDepth; void main(){ vUv=uv; vec4 w=modelMatrix*vec4(position,1.); vW=w.xyz; vec4 mv=viewMatrix*w; vDepth=-mv.z; gl_Position=projectionMatrix*mv; }';
  function mats(u) {
    const head = 'uniform sampler2D map, map2, cookie; uniform float st1, st2, mixK, fade, keyGain, fogD, hit, rimK; uniform vec3 ambient, key, warm, fogC, rimC; uniform vec2 rimDir; uniform mat4 lightVP; varying vec2 vUv; varying vec3 vW; varying float vDepth;' + SAMPLE;
    const col = new T.ShaderMaterial({
      uniforms: u, vertexShader: VERT, transparent: true, depthWrite: false, side: T.DoubleSide,
      blending: T.CustomBlending, blendEquation: T.AddEquation, blendSrc: T.SrcAlphaFactor, blendDst: T.OneMinusSrcAlphaFactor, blendSrcAlpha: T.ZeroFactor, blendDstAlpha: T.OneFactor,
      fragmentShader: head + `
        void main(){ vec4 t = both(vUv); float a = t.a * fade; if (a < 0.004) discard;
          vec3 c = pow(t.rgb, vec3(2.2)) * 0.62; // filmed footage keeps its own contrast; the scene light only tints and stripes it
          vec4 lp = lightVP * vec4(vW, 1.); vec2 luv = lp.xy / lp.w * 0.5 + 0.5; float ck = 0.;
          if (keyGain > 0. && lp.w > 0. && luv.x > 0. && luv.x < 1. && luv.y > 0. && luv.y < 1.) {
            // softened blinds on the filmed figure: 9-tap blur of the cookie and half the contrast, so the stripes read as light, not damage
            float acc = 0.; for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) acc += texture2D(cookie, luv + vec2(float(i), float(j)) * 0.012).r;
            ck = mix(0.4, smoothstep(0.2, 0.9, acc / 9.), 0.5); }
          float side = smoothstep(0.1, 0.9, vUv.x);
          vec3 light = ambient * (1.3 + 0.7 * side) + key * ck * keyGain * (0.4 + 0.6 * side) + warm * (1.0 - vUv.y) * 0.5;
          vec3 o = c * light * 1.25 + vec3(hit, 0., 0.);
          // rim: the edge that faces the light catches it
          float ao = both(vUv + rimDir).a; float rim = clamp(t.a - ao, 0., 1.) * rimK; o += rimC * rim * (0.35 + ck);
          float f = 1.0 - exp(-fogD * fogD * vDepth * vDepth); o = mix(o, fogC * fogC, f);
          gl_FragColor = vec4(o, a); }`,
    });
    // second pass: depth + the red-keep alpha for the B&W RED grade, colour untouched
    const keep = new T.ShaderMaterial({
      uniforms: u, vertexShader: VERT, transparent: false, depthWrite: true, side: T.DoubleSide,
      blending: T.CustomBlending, blendEquation: T.AddEquation, blendSrc: T.ZeroFactor, blendDst: T.OneFactor, blendSrcAlpha: T.OneFactor, blendDstAlpha: T.ZeroFactor,
      fragmentShader: head + `
        void main(){ vec4 t = both(vUv); if (t.a * fade < 0.5) discard; vec3 lin = pow(t.rgb, vec3(2.2));
          float rk = smoothstep(2.0, 2.8, lin.r / max(0.03, max(lin.g, lin.b))) * smoothstep(0.16, 0.3, lin.r);
          gl_FragColor = vec4(0., 0., 0., 1.0 - rk * 0.95); }`,
    });
    return { col, keep };
  }

  // ---------------------------------------------------------------- the walker at rest: the painted angle set (same art as the stills), correct aspect
  const ANG = ['front', 'front34L', 'sideL', 'back34R', 'back', 'back34L', 'sideR', 'front34L'], FLIP = [0, 0, 0, 0, 0, 0, 0, 1];
  const FACE_COS = 0.5;
  const sets = {};
  function paintedStand(a, cam, rest) {
    const D = a.D, u = a.mat.uniforms;
    if (!rest) { if (a._ps) { a.mesh.scale.set(1, 1, 1); a.mesh.position.y = D.centerY; a._ps = false; } return; }
    const set = sets[a.who] || (sets[a.who] = NR.actors.preload(a.who));
    const cx = cam.position.x - a.pos.x, cz = cam.position.z - a.pos.z, cl = Math.hypot(cx, cz) || 1, tx = cx / cl, tz = cz / cl;
    const fx = Math.sin(a.yaw), fz = Math.cos(a.yaw), th = Math.atan2(fx * tz - fz * tx, fx * tx + fz * tz);
    const k = ((Math.round(th / (Math.PI / 4)) % 8) + 8) % 8;
    u.map.value = k === 0 ? set.idle[Math.floor(a.t * 8) % 12] : set.angle[ANG[k]]; u.rect.value.set(0, 0, 1, 1); u.flip.value = FLIP[k]; u.rimGain.value = 0;
    // the stills are 384x768 (1:2) like the walker plane (1 x 2 m): one uniform scale to 1.86 m, feet on the floor
    const h = 1.86; a.mesh.scale.set(h / D.world[1], h / D.world[1], 1); a.mesh.position.y = h / 2 - 0.02; a._ps = true;
  }

  // ---------------------------------------------------------------- a performance attached to a painted character
  class Perf {
    constructor(actor) {
      this.a = actor; this.who = actor.who; const pu = actor.mat.uniforms;
      this.u = { map: { value: null }, map2: { value: null }, st1: { value: 0 }, st2: { value: 0 }, mixK: { value: 0 }, fade: { value: 1 },
        cookie: pu.cookie, lightVP: pu.lightVP, ambient: pu.ambient, key: pu.key, warm: pu.warm, keyGain: pu.keyGain, fogC: pu.fogC, fogD: pu.fogD, hit: pu.hit,
        rimC: { value: new T.Color(0xffe2b0) }, rimK: { value: 0.0 }, rimDir: { value: new T.Vector2(0.006, 0.002) } };
      const m = mats(this.u), g = new T.PlaneGeometry(1, 1);
      this.mA = new T.Mesh(g, m.col); this.mB = new T.Mesh(g, m.keep); this.mA.renderOrder = 2; this.mB.renderOrder = 1;
      this.mA.visible = this.mB.visible = false; actor.group.add(this.mA, this.mB);
      this.cur = null; this.prev = null; this.mixT = 1; this.want = null; this.shown = false;
    }
    clipFor() { // which clip the story wants now
      const G = NR.game, b = G.beat, st = NR.core.state;
      if (this.who === 'vela') {
        if (b === 'office_talk' && !this.stoleDone && AVAIL.has('vela_stole')) { const c = vids[CLIPS.vela_stole.file + (MODE === 'stack' ? '_stack' : '') + '_once']; if (!(c && c.v.failed)) return 'vela_stole'; this.stoleDone = true; }
        if (b === 'office_light') return 'vela_smoke';
        return VP.speaking('VELA') ? 'vela_talk' : 'vela_idle';
      }
      if (this.who === 'dolores') return 'dolores_idle';
      void st; return null;
    }
    use(name) {
      const spec = CLIPS[name]; if (!spec) return;
      if (!AVAIL.has(spec.file)) { if (spec.once) this.stoleDone = true; if (name !== 'vela_idle' && AVAIL.has('vela_idle') && this.who === 'vela') return this.use('vela_idle'); return; }
      const c = video(spec.file, MODE === 'stack', !spec.once); c.spec = spec; c.name = name;
      if (this.cur === c || this.next === c) return;
      if (spec.once && (c.v.failed || this.stoleDone)) { this.stoleDone = true; return; }
      if (spec.once) { c.v.currentTime = 0; c.v.onended = () => { if (name === 'vela_stole') this.stoleDone = true; }; }
      play(c); this.next = c;
    }
    update(dt, cam) {
      if (MODE === 'off') return;
      const a = this.a, framedNow = cam.fov <= FRAMED_FOV + 8;
      // open lens: the full-length clip; close lens: the waist-up performance the story wants
      // texture tier by screen footprint: her height in render pixels at this distance and lens
      const dist = Math.hypot(cam.position.x - a.pos.x, cam.position.z - a.pos.z) || 1, rh = NR.core.renderer.domElement.height;
      const px = 1.8 / (2 * dist * Math.tan(cam.fov * Math.PI / 360)) * rh;
      this.small = VP.forceTier ? VP.forceTier === 'small' : this.small ? px < 1000 : px < 850;
      const fullName = this.small && AVAIL.has('vela_full_640') ? 'vela_full_sm' : 'vela_full';
      const name = framedNow ? this.clipFor() : (this.who === 'vela' && AVAIL.has('vela_full') && !(NR.game.beat === 'office_talk' && !this.stoleDone && AVAIL.has('vela_stole')) ? fullName : null);
      if (name) this.use(name);
      // swap in the wanted clip once it has a frame; cross-dissolve 0.35 s
      if (this.next && live(this.next)) { if (this.cur && this.cur !== this.next) { this.prev = this.cur; this.mixT = 0; } this.cur = this.next; this.next = null; }
      if (this.prev && this.mixT >= 1) { this.prev.v.pause(); this.prev = null; }
      this.mixT = Math.min(1, this.mixT + dt / 0.35);
      const cx = cam.position.x - a.pos.x, cz = cam.position.z - a.pos.z, cl = Math.hypot(cx, cz) || 1;
      const fx = Math.sin(a.yaw), fz = Math.cos(a.yaw), facing = (fx * cx + fz * cz) / cl; // 1 = she faces the camera
      const framed = framedNow; this.facingOK = facing > FACE_COS;
      const standing = !a.walking && (a.walkAmt || 0) < 0.05 && (!a.mode || a.mode === 'idle');
      // her face can be seen (within 60 deg of her front): the filmed performance; full-length clip at the open lens
      const on = !!this.cur && a.visible && standing && facing > FACE_COS && (framed ? !this.cur.spec.full : this.cur.spec.full);
      this.shown = on; this.mA.visible = this.mB.visible = on; a.mesh.visible = !on;
      if (a.D) paintedStand(a, cam, standing && !on); // the frame-animated walker: painted angle sprites at rest, never the mocap render
      if (!on) { for (const c of [this.cur, this.next]) if (c && c.spec && c.spec.once && !c.v.paused) c.v.pause(); return; }
      for (const c of [this.cur, this.prev]) if (c) { play(c); c.pump(); }
      const u = this.u, s = this.cur.spec;
      if (this.prev) { u.map.value = this.prev.tex; u.st1.value = this.prev.stacked ? 1 : 0; u.map2.value = this.cur.tex; u.st2.value = this.cur.stacked ? 1 : 0; u.mixK.value = this.mixT * this.mixT * (3 - 2 * this.mixT); }
      else { u.map.value = this.cur.tex; u.st1.value = this.cur.stacked ? 1 : 0; u.map2.value = this.cur.tex; u.st2.value = u.st1.value; u.mixK.value = 0; }
      // size from the head: hair-top-to-chin is HEAD metres; the top of the hair sits at the figure's height
      const vw = this.cur.v.videoWidth || 512, vh = (this.cur.v.videoHeight || 896) / (this.cur.stacked ? 2 : 1);
      const topY = (a.h || 1.86) * 0.968, H = s.full ? topY / (s.foot - s.top) : HEAD / (s.chin - s.top), W = H * vw / vh; // uniform: W/H is the clip's own aspect
      for (const m of [this.mA, this.mB]) {
        m.scale.set(W, H, 1); m.rotation.copy(a.mesh.rotation);
        const off = (0.5 - s.cx) * W; m.position.set(Math.cos(m.rotation.y) * off, topY - H * (0.5 - s.top), -Math.sin(m.rotation.y) * off);
      }
      u.rimDir.value.set(0.006 * (a.level && a.level.rimSide || 1), 0.002);
    }
  }

  // ---------------------------------------------------------------- hooks (no edits to the other modules)
  const VP = NR.vperf = { MODE, CLIPS, AVAIL, forceTier: null, vids, Perf, speaking: () => false, stats() { return Object.values(vids).map(c => ({ src: c.v.currentSrc.split('/').pop(), rs: c.v.readyState, t: +c.v.currentTime.toFixed(2), paused: c.v.paused, w: c.v.videoWidth, h: c.v.videoHeight, failed: !!c.v.failed })); } };
  let whoEl = null;
  VP.speaking = (name) => { if (!whoEl || !whoEl.isConnected) whoEl = document.querySelector('#nru .who'); return !!(whoEl && whoEl.textContent === name && whoEl.closest('.on')); };
  if (MODE !== 'off' && NR.actors) for (const K of [NR.actors.Painted, NR.actors.Walker]) { // the painted figure and the frame-animated walker
    if (!K) continue; const P = K.prototype, up = P.update;
    P.update = function (dt, cam) { up.call(this, dt, cam); if (!this.perf && (this.who === 'vela' || this.who === 'dolores')) this.perf = new Perf(this); this.perf && this.perf.update(dt, cam); };
    const rm = P.remove; P.remove = function () { if (this.perf) { for (const c of [this.perf.cur, this.perf.prev, this.perf.next]) if (c) c.v.pause(); } return rm.call(this); };
  }
  // cinematic framing: while she talks to Harrow the lens tightens so the waist-up clips fill the frame
  const FRAMED_BEATS = { office_talk: 1, office_light: 1, office_leave: 0, club_meet: 1 };
  let fovNow = OPEN_FOV;
  function frameCam(rdt) {
    const G = NR.game, core = NR.core, cam = core.camera, P = NR.player;
    let want = OPEN_FOV;
    if (MODE !== 'off' && G && FRAMED_BEATS[G.beat] && core.state === 'CUTSCENE' && !(P && P.forceCig) && G.chars.some(c => c.perf && c.perf.facingOK && c.visible && !c.walking)) want = FRAMED_FOV;
    if (G && G.beat === 'office_smoke' && core.state === 'CUTSCENE' && !(P && P.forceCig) && G.chars.some(c => c.perf && c.perf.facingOK && c.visible)) want = FRAMED_FOV;
    fovNow += (want - fovNow) * Math.min(1, rdt * 2.2);
    if (Math.abs(fovNow - want) < 0.05) fovNow = want;
    if (Math.abs(cam.fov - fovNow) > 0.01) { cam.fov = fovNow; cam.updateProjectionMatrix(); }
  }
  if (NR.game && NR.game.update) {
    const gu = NR.game.update; NR.game.update = function (dt, rdt) { gu.call(this, dt, rdt); try { frameCam(rdt); } catch (e) { console.error('[vperf]', e); } };
  }

  // ---------------------------------------------------------------- interrogation close-up: looping reactions per mood
  function panel(who) {
    const set = PANEL[who]; if (!set || MODE === 'off' || !Object.values(set).some(f => AVAIL.has(f))) return;
    const pic = document.querySelector('#nru .itg .pic'); if (!pic) return;
    const cv = document.createElement('canvas'); cv.className = 'vp'; pic.insertBefore(cv, pic.querySelector('.nm'));
    const gl = cv.getContext('webgl', { premultipliedAlpha: false, alpha: false, preserveDrawingBuffer: false }); if (!gl) { cv.remove(); return; }
    const vs = 'attribute vec2 p; varying vec2 v; void main(){ v = p * 0.5 + 0.5; gl_Position = vec4(p, 0., 1.); }';
    const fs = `precision mediump float; uniform sampler2D a, b; uniform float k, bw, asp; uniform vec2 sc, of; varying vec2 v;
      vec3 g(vec3 c){ if (bw < 0.5) return c; float l = dot(c, vec3(0.299, 0.587, 0.114)); float q = c.r / max(0.04, max(c.g, c.b)); float r = clamp((q - 2.0) / 0.8, 0., 1.) * clamp((c.r - 0.18) / 0.16, 0., 1.);
        return mix(vec3(l), vec3(min(1., c.r * 1.08), c.g * 0.9, c.b * 0.9), r); }
      void main(){ vec2 uv = vec2(v.x, 1.0 - v.y) * sc + of; vec3 c = mix(texture2D(a, uv).rgb, texture2D(b, uv).rgb, k); gl_FragColor = vec4(g(c), 1.); }`;
    const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); return o; };
    const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = (n) => gl.getUniformLocation(pr, n);
    gl.uniform1i(U('a'), 0); gl.uniform1i(U('b'), 1);
    const texs = [0, 1].map(() => { const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t); for (const [p, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, p, v); return t; });
    const useMp4 = MODE === 'stack' || !canWebm;
    const vs2 = {}; for (const m in set) { if (!AVAIL.has(set[m])) continue; const v = document.createElement('video'); v.muted = true; v.loop = true; v.playsInline = true; v.setAttribute('playsinline', ''); v.preload = 'auto'; v.src = BASE + set[m] + (useMp4 && canMp4 ? '.mp4' : '.webm'); v.addEventListener('error', () => { v.failed = true; }); parkVideo(v); vs2[m] = v; }
    const imgs = pic.querySelectorAll('img');
    let cur = null, prev = null, k = 1, live2 = true, last = performance.now();
    const pc = [document.createElement('canvas'), document.createElement('canvas')], pg = pc.map(c => c.getContext('2d'));
    const grab = (i, v) => { const c = pc[i]; if (c.width !== v.videoWidth || c.height !== v.videoHeight) { c.width = v.videoWidth; c.height = v.videoHeight; } pg[i].drawImage(v, 0, 0); return c; };
    VP.panelState = () => ({ cur: cur && cur.src.split('/').pop(), rs: cur && cur.readyState, t: cur && +cur.currentTime.toFixed(2), shown: cv.style.opacity });
    const moodNow = () => { for (const im of imgs) if (im.classList.contains('on')) { const m = /(warm|guarded|cold)$/.exec(im.alt); if (m) return m[1]; } return 'guarded'; };
    (function frame(now) {
      const itg = pic.closest('.itg'); if (!live2 || !itg || !itg.classList.contains('on') || !pic.isConnected) { for (const m in vs2) { vs2[m].pause(); vs2[m].remove(); } live2 = false; cv.remove(); return; }
      requestAnimationFrame(frame); const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const want = vs2[moodNow()];
      if (!want) { cv.style.opacity = 0; if (cur) { cur.pause(); cur = null; } if (prev) { prev.pause(); prev = null; } return; } // no clip for this mood: the still shows
      if (want && want !== cur && !want.failed) { if (want.paused) want.play().catch(() => {}); if (want.readyState >= 2) { prev = cur; cur = want; k = prev ? 0 : 1; } }
      k = Math.min(1, k + dt / 0.45); if (prev && k >= 1) { prev.pause(); prev = null; }
      if (!cur || cur.readyState < 2) return;
      const w = pic.clientWidth, h = pic.clientHeight, dpr = Math.min(2, devicePixelRatio || 1);
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); gl.viewport(0, 0, cv.width, cv.height); }
      // object-fit: cover, object-position 50% 22% (as the stills)
      const va = cur.videoWidth / cur.videoHeight, ca = w / h; let sx = 1, sy = 1; if (va > ca) sx = ca / va; else sy = va / ca;
      gl.uniform2f(U('sc'), sx, sy); gl.uniform2f(U('of'), (1 - sx) * 0.5, (1 - sy) * 0.22);
      try {
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texs[0]); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, grab(0, prev || cur));
        gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texs[1]); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, grab(1, cur));
      } catch (e) { return; }
      gl.uniform1f(U('k'), prev ? k * k * (3 - 2 * k) : 1); gl.uniform1f(U('bw'), NR.core.settings.film === 'bwred' ? 1 : 0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); cv.style.opacity = 1;
    })(last);
  }
  const st = document.createElement('style');
  st.textContent = '#nru .itg .pic canvas.vp{position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity .45s;pointer-events:none}';
  document.head.appendChild(st);
  if (NR.ui && NR.ui.interrogate) {
    const it = NR.ui.interrogate; NR.ui.interrogate = function (who, data, found) { const p = it.call(this, who, data, found); try { panel(who); } catch (e) { console.error('[vperf panel]', e); } return p; };
  }
})();
