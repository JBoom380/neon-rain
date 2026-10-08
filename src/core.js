// NEON RAIN core: renderer, noir post pass (half-res light shafts, grade, B&W+red, grain, vignette), camera, loop, states.
(function () {
  const T = window.THREE, C = NR.cfg;
  const canvas = document.getElementById('game');
  const isTouch = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
  const settings = Object.assign({ bw: true, music: 0.6, sfx: 0.8, quality: isTouch ? 'low' : 'high', sens: 1 }, load(C.SETTINGS_KEY));
  if (settings.film !== 'bwred') settings.film = 'noir'; settings.bw = settings.film === 'bwred'; // FILM: noir colour (default) or B&W with red kept
  { const q = new URLSearchParams(location.search).get('chars'); if (q === '3d' || q === 'painted') settings.chars = q; if (settings.chars !== '3d') settings.chars = 'painted'; } // CHARACTERS: painted (default) or 3d
  function load(k) { try { return JSON.parse(localStorage.getItem(k)) || {}; } catch (e) { return {}; } }

  const renderer = new T.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFShadowMap; renderer.shadowMap.autoUpdate = false;
  renderer.toneMapping = T.NoToneMapping;
  const camera = new T.PerspectiveCamera(74, 9 / 19.5, 0.05, 120);
  camera.rotation.order = 'YXZ';
  const vmCam = new T.PerspectiveCamera(); // view-model camera: identity pose, same projection as the main camera

  // ---- render targets ----
  let rt = null, srt = null, W = 0, H = 0, PR = 1;
  const post = new T.ShaderMaterial({
    depthTest: false, depthWrite: false,
    uniforms: {
      tCol: { value: null }, tShaft: { value: null }, shaftOn: { value: 0 }, shaftCol: { value: new T.Color(0.85, 0.92, 1) }, shaftK: { value: 0.16 },
      time: { value: 0 }, bw: { value: 1 }, hurt: { value: 0 }, scan: { value: 0 }, focus: { value: 0 }, fade: { value: 0 },
      flash: { value: new T.Vector4(0, 0, 0, 0) }, expo: { value: 1.15 }, res: { value: new T.Vector2(1, 1) },
    },
    vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }',
    fragmentShader: `precision highp float; uniform sampler2D tCol, tShaft; uniform vec3 shaftCol; uniform vec4 flash; uniform vec2 res;
      uniform float shaftOn, shaftK, time, bw, hurt, scan, focus, fade, expo; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453); }
      vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.,1.); }
      void main(){
        vec3 col = texture2D(tCol, vUv).rgb;
        if (shaftOn > 0.5) { vec2 px = 2.0/res; float sh = texture2D(tShaft, vUv).r*0.36 + (texture2D(tShaft, vUv+vec2(px.x,px.y)).r + texture2D(tShaft, vUv+vec2(-px.x,px.y)).r + texture2D(tShaft, vUv+vec2(px.x,-px.y)).r + texture2D(tShaft, vUv-px).r)*0.16;
          col += shaftCol * sh * shaftK; }
        if (bw < 0.5) { vec2 px = 1.0/res; vec3 hal = vec3(0.0), stk = vec3(0.0);
          // halation: bright practicals bleed a warm halo
          for (int i = 0; i < 8; i++) { float a = float(i) * 0.785398; vec2 o = vec2(cos(a), sin(a)) * px * (9.0 + 9.0 * mod(float(i), 2.0));
            vec3 c2 = texture2D(tCol, vUv + o).rgb; hal += max(c2 - 0.9, 0.0); }
          col += hal * vec3(1.0, 0.6, 0.35) * 0.09;
          // anamorphic streak: a thin horizontal flare on the brightest lights, swelling now and then
          for (int i = 1; i <= 6; i++) { float d = float(i) * float(i) * 0.0045; vec3 l1 = texture2D(tCol, vUv + vec2(d, 0.0)).rgb, l2 = texture2D(tCol, vUv - vec2(d, 0.0)).rgb;
            stk += (max(l1 - 1.4, 0.0) + max(l2 - 1.4, 0.0)) * (1.0 - float(i) / 7.0); }
          float swell = 0.35 + 0.65 * pow(max(0.0, sin(time * 0.31) * sin(time * 0.17 + 1.3)), 2.0);
          col += dot(stk, vec3(0.33)) * vec3(0.35, 0.75, 1.0) * 0.06 * swell; }
        col = aces(col * expo); col = pow(col, vec3(1./2.2));
        float l = dot(col, vec3(0.299,0.587,0.114));
        float mx=max(col.r,max(col.g,col.b)), mn=min(col.r,min(col.g,col.b)); float sat=(mx-mn)/(mx+1e-4);
        float red = smoothstep(0.28,0.5,sat)*smoothstep(0.02,0.1,col.r-max(col.g,col.b))*smoothstep(0.42,0.3,col.g/(col.r+1e-3));
        red = max(red, clamp(1.0 - texture2D(tCol, vUv).a, 0.0, 1.0)); // sprites flag their painted reds through alpha
        if (bw > 0.5) { vec3 g = vec3(pow(l,1.08)); col = mix(g, col*vec3(1.1,0.9,0.9), clamp(red*1.4,0.,1.)); }
        else { // NOIR COLOR: warm amber practicals against cold teal shadows and haze; red only for lips, blood and red neon
          float hr = col.r - col.b, hg = col.g - col.r;
          float strictRed = smoothstep(0.55, 0.75, sat) * smoothstep(0.12, 0.25, col.r - max(col.g, col.b)) * smoothstep(0.4, 0.28, col.g / (col.r + 1e-3)) * smoothstep(0.08, 0.2, mx);
          red = max(strictRed, clamp(1.0 - texture2D(tCol, vUv).a, 0.0, 1.0));
          float warm = smoothstep(0.04, 0.16, hr) * smoothstep(0.1, 0.3, sat) * smoothstep(0.16, 0.42, mx);    // lit warm areas: lamps, sconces, sodium
          float teal = smoothstep(0.03, 0.12, hg + (col.b - col.r) * 0.5) * smoothstep(0.2, 0.4, sat) * smoothstep(0.15, 0.4, mx); // neon teal / cyan / green
          // split tone: teal shadows and haze, warm-neutral highlights
          vec3 split = l * mix(vec3(0.62, 0.95, 1.02), vec3(1.05, 0.98, 0.9), smoothstep(0.08, 0.55, l));
          split += vec3(0.0, 0.016, 0.022) * (1.0 - smoothstep(0.0, 0.28, l));                                  // lifted teal haze in the blacks
          vec3 amber = mx * vec3(1.0, 0.64, 0.3);                                                               // warm hues pulled to sodium amber
          vec3 kept = mix(mix(amber, col, 0.35), col, red);                                                     // red stays red; other warm hues go amber
          kept = mix(kept, mix(vec3(l), col, 1.2), teal);
          float keep = clamp(max(max(warm * 0.85, teal), red), 0.0, 1.0);
          col = max(mix(split, kept, keep), 0.0); }
        col = smoothstep(vec3(0.035), vec3(1.0), col); // deep blacks
        // scan: amber wash + scanlines
        col = mix(col, col*vec3(1.25,0.95,0.55) + vec3(0.03,0.02,0.0), scan*0.6);
        col *= 1.0 - scan*0.08*step(0.5, fract(gl_FragCoord.y*0.25));
        // focus (slow-mo): crushed, cooler edges
        vec2 q = vUv-0.5; float r2 = dot(q*vec2(1.0,0.75), q*vec2(1.0,0.75));
        col = mix(col, col*col*1.25, focus*smoothstep(0.05,0.3,r2));
        col *= 1.0 - r2*(1.35 + focus*1.6);
        // hurt: red screen edges (kept red in B&W)
        float e = smoothstep(0.08, 0.32, r2) * hurt;
        col = mix(col, vec3(0.55,0.02,0.02) + col*vec3(0.4,0.,0.), clamp(e*1.2,0.,0.92));
        col = mix(col, flash.rgb, flash.a);
        float gr = h(gl_FragCoord.xy*0.73 + fract(time*7.3)*100.) - 0.5; col += gr*0.045*(0.3+0.7*(1.-l));
        col *= 1.0 - fade;
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  // half-res volumetric light shafts: ray-march the current scene's cookie spotlight through the depth buffer
  const shaftMat = new T.ShaderMaterial({
    depthTest: false, depthWrite: false,
    uniforms: { tDep: { value: null }, cookie: { value: null }, lightVP: { value: new T.Matrix4() }, lightPos: { value: new T.Vector3() },
      projInv: { value: camera.projectionMatrixInverse }, camWorld: { value: camera.matrixWorld }, time: { value: 0 }, maxD: { value: 9 }, yTop: { value: 2.9 }, zMin: { value: -1e3 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }',
    fragmentShader: `precision highp float; uniform sampler2D tDep, cookie; uniform mat4 lightVP, projInv, camWorld; uniform vec3 lightPos; uniform float time, maxD, yTop, zMin; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453); }
      float n2(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
      void main(){ float d = texture2D(tDep, vUv).r;
        vec4 vp = projInv*vec4(vUv*2.-1., d*2.-1., 1.); vp/=vp.w; vec3 wp=(camWorld*vp).xyz; vec3 ro=(camWorld*vec4(0,0,0,1)).xyz;
        vec3 rd = wp-ro; float dist=min(length(rd), maxD); rd=normalize(rd);
        const int STEPS=18; float sl=dist/float(STEPS); float j=h(gl_FragCoord.xy)*0.85; float acc=0.;
        for(int i=0;i<STEPS;i++){ vec3 p=ro+rd*(float(i)+j)*sl; if(p.z<zMin) break;
          vec4 lp=lightVP*vec4(p,1.); if(lp.w<=0.) continue; vec2 luv=lp.xy/lp.w*0.5+0.5; if(luv.x<0.||luv.x>1.||luv.y<0.||luv.y>1.) continue;
          float ck=texture2D(cookie,luv).r; float den=0.55+0.9*n2(p.xz*2.2+p.y*1.3+vec2(time*0.05,time*0.03));
          float att=1./(1.+0.08*dot(p-lightPos,p-lightPos)); acc += ck*den*att*sl*smoothstep(yTop,yTop-1.3,p.y); }
        gl_FragColor = vec4(acc, 0., 0., 1.); }`,
  });
  const quad = new T.Mesh(new T.PlaneGeometry(2, 2), post); quad.frustumCulled = false;
  const pScene = new T.Scene(); pScene.add(quad); const pCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  function setRes() {
    fit();
    const v = core.view; PR = Math.min(devicePixelRatio || 1, settings.quality === 'high' ? 2 : 1.5);
    W = Math.round(v.w * PR); H = Math.round(v.h * PR);
    renderer.setPixelRatio(1); renderer.setSize(W, H, false);
    canvas.style.width = v.w + 'px'; canvas.style.height = v.h + 'px';
    if (rt) { rt.dispose(); srt.dispose(); }
    rt = new T.WebGLRenderTarget(W, H, { type: T.HalfFloatType, depthBuffer: true });
    rt.depthTexture = new T.DepthTexture(W, H); rt.depthTexture.type = T.UnsignedIntType;
    srt = new T.WebGLRenderTarget(Math.max(1, W >> 1), Math.max(1, H >> 1), { type: T.UnsignedByteType, depthBuffer: false });
    post.uniforms.tCol.value = rt.texture; post.uniforms.tShaft.value = srt.texture; post.uniforms.res.value.set(W, H);
    shaftMat.uniforms.tDep.value = rt.depthTexture;
    camera.aspect = v.w / v.h; camera.updateProjectionMatrix();
  }
  function fit() { // portrait column: full width on phones, letterboxed on wide screens
    const vw = innerWidth, vh = innerHeight; const asp = NR.clamp(vw / vh, 9 / 21, 3 / 4);
    let w = Math.min(vw, Math.round(vh * asp)), h = Math.min(vh, Math.round(w / asp));
    const left = Math.round((vw - w) / 2), top = Math.round((vh - h) / 2);
    Object.assign(canvas.style, { left: left + 'px', top: top + 'px' });
    const ui = document.getElementById('ui'); if (ui) Object.assign(ui.style, { width: w + 'px', height: h + 'px', left: left + 'px', top: top + 'px' });
    core.view = { w, h, left, top };
  }
  let resizeT = 0;
  addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(() => { setRes(); NR.bus.emit('resize', core.view); }, 60); });

  // ---- core object ----
  const core = NR.core = {
    T, renderer, camera, settings, isTouch, scene: null, shaft: null, time: 0, dt: 0, rdt: 0, timeScale: 1, state: 'BOOT', view: null, frame: 0,
    fx: { hurt: 0, scan: 0, focus: 0, fade: 0 },
    saveSettings() { try { localStorage.setItem(C.SETTINGS_KEY, JSON.stringify(settings)); } catch (e) {} },
    setQuality(q) { settings.quality = q; core.saveSettings(); setRes(); },
    setState(s) { const prev = core.state; if (prev === s) return; core.state = s; NR.bus.emit('state', { state: s, prev }); },
    setScene(scene, shaft) {
      core.scene = scene; core.shaft = shaft || null; scene.add(camera); renderer.shadowMap.needsUpdate = true;
      try { renderer.compile(scene, camera); if (core.vm) renderer.compile(core.vm.scene, camera); } catch (e) {} // compile all programs now (boot / behind the black cards), not on first draw
      if (shaft) { const u = shaftMat.uniforms; u.cookie.value = shaft.cookie; u.lightVP.value = shaft.lightVP; u.lightPos.value = shaft.pos; u.maxD.value = shaft.maxD || 9; u.yTop.value = shaft.yTop || 2.9; u.zMin.value = shaft.zMin == null ? -1e3 : shaft.zMin;
        post.uniforms.shaftCol.value.set(shaft.color || 0xd8ebff); post.uniforms.shaftK.value = shaft.k || 0.16; }
      post.uniforms.expo.value = scene.userData.expo || 1.15;
    },
    flash(hex, s, a = 0.5) { flashC.setHex(hex); flashT = flashMax = s; flashA = a; },
    shake(a, s) { shakeA = Math.max(shakeA, a); shakeT = Math.max(shakeT, s); },
    fadeTo(v, s) { return new Promise(r => { fadeFrom = core.fx.fade; fadeTo = v; fadeDur = Math.max(0.01, s); fadeT = 0; fadeDone = r; }); },
    wait(s) { return new Promise(r => waits.push({ t: s, r })); }, // real-time seconds, ticks with the loop
    get fps() { return fpsVal; },
  };
  let shakeA = 0, shakeT = 0, flashT = 0, flashMax = 1, flashA = 0; const flashC = new T.Color();
  let fadeFrom = 0, fadeTo = 0, fadeDur = 1, fadeT = 1, fadeDone = null; const waits = [];
  setRes();

  // ---- loop ----
  let last = performance.now(), fpsN = 0, fpsT = last, fpsVal = 0;
  function loop(now) {
    requestAnimationFrame(loop);
    const rdt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now;
    core.rdt = rdt; core.dt = rdt * core.timeScale; core.time += core.dt; core.frame++;
    fpsN++; if (now - fpsT > 1000) { fpsVal = fpsN * 1000 / (now - fpsT); fpsN = 0; fpsT = now; }
    for (let i = waits.length - 1; i >= 0; i--) { if ((waits[i].t -= rdt) <= 0) { const w = waits[i]; waits.splice(i, 1); w.r(); } }
    if (fadeT < 1) { fadeT = Math.min(1, fadeT + rdt / fadeDur); core.fx.fade = fadeFrom + (fadeTo - fadeFrom) * fadeT; if (fadeT >= 1 && fadeDone) { const f = fadeDone; fadeDone = null; f(); } }
    try { if (NR.game) NR.game.update(core.dt, rdt); } catch (e) { console.error('[NR.game.update]', e); }
    if (!core.scene) return;
    // camera shake (applied on top of the player's camera pose for this frame only)
    let sx = 0, sy = 0;
    if (shakeT > 0) { shakeT -= rdt; sx = (Math.random() - 0.5) * shakeA; sy = (Math.random() - 0.5) * shakeA; camera.rotation.x += sy; camera.rotation.y += sx; }
    camera.updateMatrixWorld();
    if (core.frame % 2 === 0) renderer.shadowMap.needsUpdate = true;
    renderer.setRenderTarget(rt); renderer.render(core.scene, camera);
    if (core.vm && core.vm.scene.visible) { vmCam.projectionMatrix.copy(camera.projectionMatrix); vmCam.projectionMatrixInverse.copy(camera.projectionMatrixInverse); renderer.autoClear = false; renderer.clearDepth(); renderer.render(core.vm.scene, vmCam); renderer.autoClear = true; }
    if (core.shaft && core.shaft.on !== false) { shaftMat.uniforms.time.value = core.time; quad.material = shaftMat; renderer.setRenderTarget(srt); renderer.render(pScene, pCam); post.uniforms.shaftOn.value = 1; }
    else post.uniforms.shaftOn.value = 0;
    camera.rotation.x -= sy; camera.rotation.y -= sx;
    const u = post.uniforms; u.time.value = core.time; u.bw.value = settings.film === 'bwred' ? 1 : 0; // only the FILM setting picks B&W RED
    u.hurt.value = core.fx.hurt; u.scan.value = core.fx.scan; u.focus.value = core.fx.focus; u.fade.value = core.fx.fade;
    if (flashT > 0) { flashT -= rdt; u.flash.value.set(flashC.r, flashC.g, flashC.b, Math.max(0, flashT / flashMax) * flashA); } else u.flash.value.w = 0;
    quad.material = post; renderer.setRenderTarget(null); renderer.render(pScene, pCam);
  }
  core.startLoop = () => requestAnimationFrame(loop);
})();
