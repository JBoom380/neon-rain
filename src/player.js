// NEON RAIN player: first-person movement and look, .45 pistol (7 + 1, spare magazines, slide lock, head shots, light aim assist on touch),
// health (red screen edges, recovery in cover, 3 lives), cigarettes (FOCUS slow-mo / THINK / OFFER), SCAN, INTERACT.
(function () {
  const T = THREE, C = NR.cfg, V3 = (x, y, z) => new T.Vector3(x, y, z);
  const P = NR.player = {
    pos: V3(0, 0, 0), yaw: 0, pitch: 0, vel: V3(0, 0, 0), hp: C.HP, lives: C.LIVES, rounds: C.GUN_ROUNDS, drawn: false, drawT: 0, drawDur: 0, mags: C.MAGS_START, slideLock: false, reloadDur: C.GUN_RELOAD, reloadEmpty: false, armed: false,
    reloadT: 0, fireCd: 0, pack: C.PACK_START, litT: 0, focusT: 0, scanning: false, moving: false, lastHitT: 99, recoil: 0, bob: 0,
    shots: 0, hits: 0, heads: 0, smoked: 0, god: false, inCover: false, focus: 0, controlled: false, lookLock: null,
  };
  const core = () => NR.core;
  let L = null;
  P.setLevel = (lvl) => { L = lvl; };
  P.place = (pos, yaw, pitch) => { P.pos.copy(pos); P.yaw = yaw || 0; P.pitch = pitch || 0; P.vel.set(0, 0, 0); };
  P.resetHealth = () => { P.hp = C.HP; P.lastHitT = 99; P.focusT = 0; NR.core.timeScale = 1; };

  // ---------------------------------------------------------------- view models (rendered in their own pass, no wall clipping)
  const vm = { scene: new T.Scene() };
  // warm practicals only: amber incandescent key, sodium fill, teal neon rim (no red: the grade keeps reds as blood)
  vm.scene.add(new T.HemisphereLight(0xc8ae98, 0x2a1408, 2.2));
  const vmKey = new T.DirectionalLight(0xffd8b0, 3.4); vmKey.position.set(-0.6, 1.6, 0.9); vm.scene.add(vmKey);
  const vmRim = new T.DirectionalLight(0x2ad0c0, 1.8); vmRim.position.set(1.2, 0.5, -1); vm.scene.add(vmRim); // teal neon rim
  const vmSpec = new T.DirectionalLight(0xffd0a0, 0.9); vmSpec.position.set(0.15, 1.0, -1.6); vm.scene.add(vmSpec); // front-top: spec streak along the slide
  const vmRed = new T.DirectionalLight(0xff9a50, 1.1); vmRed.position.set(-1.2, 0.6, -1.0); vm.scene.add(vmRed);
  { // tiny warm environment for the blued steel's reflections (PMREM of a dark room with an amber lamp and neon strips)
    const es = new T.Scene(); es.background = new T.Color(0x0a0705);
    const strip = (c, w, h, x, y, z) => { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: c, side: T.DoubleSide })); m.position.set(x, y, z); m.lookAt(0, 0, 0); es.add(m); };
    strip(0xffa050, 3, 2, -2, 3, 1); strip(0x30e0d0, 0.4, 4, 3, 0.5, -2); strip(0xc06030, 0.4, 3, -3, 0, -2); strip(0x5a3a20, 8, 1, 0, -2, 0);
    try { const pm = new T.PMREMGenerator(NR.core.renderer); vm.scene.environment = pm.fromScene(es, 0.03).texture; pm.dispose(); } catch (e) { console.warn('[vm env]', e); }
  }
  const vmFlash = new T.PointLight(0xffb050, 0, 2, 1.5); vmFlash.position.set(0.15, -0.05, -0.6); vm.scene.add(vmFlash);
  const gunRig = new T.Group(); vm.scene.add(gunRig);
  const gun = NR.fx.revolverModel(); gun.scale.setScalar(1.0); gunRig.add(gun);
  const sleeve = new T.Mesh(new T.BoxGeometry(0.09, 0.09, 0.32), new T.MeshLambertMaterial({ color: 0x2c2a26 })); sleeve.position.set(0.0, -0.075, 0.27); gunRig.add(sleeve);
  const glove = new T.Mesh(new T.BoxGeometry(0.06, 0.07, 0.09), new T.MeshLambertMaterial({ color: 0x141210 })); glove.position.set(0, -0.045, 0.1); gunRig.add(glove);
  const flashSpr = NR.world.glow(0xffd090, 0.22, 0, 0.035, -0.29, gun); flashSpr.visible = false; flashSpr.renderOrder = 5;
  const GUN_HOME = V3(0.046, -0.08, -0.3);
  gunRig.position.copy(GUN_HOME); gunRig.scale.setScalar(0.5);
  // cigarette hand (left)
  const cigRig = new T.Group(); vm.scene.add(cigRig);
  const hand = new T.Mesh(new T.BoxGeometry(0.07, 0.08, 0.09), new T.MeshLambertMaterial({ color: 0x141210 })); cigRig.add(hand);
  const sleeve2 = new T.Mesh(new T.BoxGeometry(0.1, 0.1, 0.3), new T.MeshLambertMaterial({ color: 0x2c2a26 })); sleeve2.position.set(-0.01, -0.03, 0.18); cigRig.add(sleeve2);
  const cig = new T.Mesh(new T.CylinderGeometry(0.0045, 0.0045, 0.075, 8), new T.MeshLambertMaterial({ color: 0xeee8dc })); cig.rotation.z = Math.PI / 2 - 0.3; cig.position.set(0.05, 0.035, -0.02); cigRig.add(cig);
  const ember = new T.Mesh(new T.SphereGeometry(0.006, 8, 6), new T.MeshBasicMaterial({ color: 0xff5a10 })); ember.position.set(0.085, 0.045, -0.02); cigRig.add(ember);
  const emberGlow = NR.world.glow(0xff6020, 0.018, 0.087, 0.046, -0.02, cigRig);
  const cigSmoke = NR.fx.smoke(70, V3(0.087, 0.05, -0.02), { rise: 0.16, spread: 0.03, size: 9, alpha: 0.3, life: 3, depthTest: false, tint: 0xe8e0d8 }); cigRig.add(cigSmoke);
  const CIG_HOME = V3(-0.06, -0.085, -0.26);
  cigRig.position.copy(CIG_HOME); cigRig.rotation.set(0.1, 0.4, 0.2); cigRig.scale.setScalar(0.6); cigRig.visible = false;
  vm.scene.visible = true; NR.core.vm = vm; P.vm = vm;
  // vm.anim('draw' | 'holster'): hook for the modelled view-model animations (set vm.onAnim to play them)
  vm.anim = (name) => { NR.bus.emit('vmAnim', { name }); if (vm.onAnim) { try { vm.onAnim(name); } catch (e) { console.error(e); } } };
  // GUN: draw (0.45 s) / holster (0.4 s); holstered is the default, and every cutscene holsters
  P.toggleGun = () => { if (!P.armed || P.drawT > 0 || P.reloadT > 0) return; P.drawn = !P.drawn; P.drawDur = P.drawT = P.drawn ? 0.45 : 0.4; vm.anim(P.drawn ? 'draw' : 'holster'); NR.bus.emit(P.drawn ? 'draw' : 'holster'); };
  P.holster = () => { P.drawn = false; P.drawT = 0; };

  // modelled viewmodel (tools/env/viewmodel.py): 1911-pattern .45 in the right hand, cigarette in the left. Code models above
  // stay as the fallback until the GLB arrives.
  const vmp = { drum: gun.userData.drum, slide: null, fireT: 9, casings: [], manualReload: 0, forceLock: false };
  const VM_GUN = { pos: V3(0.068, -0.108, -0.37), rot: V3(0.05, 0.1, 0.1) }, VM_CIG = { pos: V3(-0.06, -0.125, -0.27), rot: V3(0.6, -0.45, 0.35) };
  if (NR.gltf) NR.fx.vmAsset = NR.gltf.load(NR.ASSET + 'models/vm_1911.glb').then(({ scene }) => {
    const N = k => scene.getObjectByName(k), rigR = N('rig_r'), rigL = N('rig_l'), muz = N('muzzle'), slide = N('slide'), mag = N('magazine'), hammer = N('hammer'), eject = N('eject'), casing = N('casing'), tip = N('cig_tip');
    const lefts = { cig: N('hand_l'), cup: N('hand_l_cup'), relax: N('hand_l_relax') }, cigNode = N('cig');
    // left-hand pose variants: 'cig' (between index and middle), 'cup' (shielding a match), 'relax' (empty)
    P.setLeftHand = (k) => { for (const n in lefts) if (lefts[n]) lefts[n].visible = n === k; if (cigNode) cigNode.visible = k === 'cig'; P.leftPose = k; };
    P.setLeftHand('cig');
    if (!rigR || !rigL || !muz || !slide || !mag || !hammer || !eject || !casing || !tip) throw new Error('vm_1911.glb: nodes missing');
    scene.traverse(o => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; const mn = o.material.name || ''; if (/steel/.test(mn)) { o.material.roughness = 0.36; o.material.envMapIntensity = 2.4; } else if (/brass/.test(mn)) { o.material.envMapIntensity = 3; o.material.roughness = 0.28; o.material.emissive.setHex(0x2a1604); } else if (o.material.metalness > 0.5) o.material.envMapIntensity = 2.6; } });
    if (NR.fx.useRevolverAsset) NR.fx.useRevolverAsset(N('pistol')); // the desk pistol uses the same model
    // gun: full scale, lower right
    gun.visible = false; sleeve.visible = false; glove.visible = false;
    gunRig.scale.setScalar(1); GUN_HOME.copy(VM_GUN.pos); gunRig.add(rigR); rigR.rotation.set(VM_GUN.rot.x, VM_GUN.rot.y, VM_GUN.rot.z);
    muz.add(flashSpr); flashSpr.position.set(0, 0, -0.01); flashSpr.scale.setScalar(0.12);
    Object.assign(vmp, { slide, mag, hammer, eject, slideZ: slide.position.z, magPos: mag.position.clone() });
    casing.parent.remove(casing); casing.position.set(0, 0, 0);
    for (let i = 0; i < 4; i++) { const c = casing.clone(true); c.visible = false; vm.scene.add(c); vmp.casings.push({ o: c, v: V3(0, 0, 0), w: V3(0, 0, 0), t: 0 }); }
    // cigarette hand: lower left, ember + smoke on the modelled tip
    hand.visible = false; sleeve2.visible = false; cig.visible = false; ember.visible = false;
    cigRig.scale.setScalar(1); cigRig.rotation.set(0, 0, 0); CIG_HOME.copy(VM_CIG.pos); cigRig.add(rigL); rigL.rotation.set(VM_CIG.rot.x, VM_CIG.rot.y, VM_CIG.rot.z);
    vmp.rigL = rigL; vmp.rigLRest = rigL.quaternion.clone(); vmp.tip = tip; tip.add(emberLight);
    vmp.filterLocal = tip.position.clone().addScaledVector(V3(0, 0.912, -0.41), -0.083); // filter end of the cigarette in rig space
    LIPS.pos.copy(LIPS.at).sub(vmp.filterLocal.clone().applyQuaternion(LIPS.q));
    tip.add(emberGlow); emberGlow.position.set(0, 0, 0); emberGlow.scale.setScalar(0.034);
    // ember: a small orange-red tip kept under the grade's halation threshold (no star/plus artefact), soft glow around it
    scene.traverse(o => { if (o.isMesh && /ember/.test(o.material.name)) { o.material = vmp.emberMat = new T.MeshBasicMaterial({ color: new T.Color(0.82, 0.24, 0.05) }); } });
    tip.add(cigSmoke); cigSmoke.position.set(-0.087, -0.05, 0.02);
    P.vmGLB = true;
  }).catch(e => console.warn('[vm glb]', e));

  // 1911 animation: slide cycles on each shot and ejects a casing to the right; slide locks back on the last round; reload
  // drops the magazine, inserts a fresh one and drops the slide. Driven by the 'shot' event, P.rounds, P.slideLock, P.reloadT.
  const MAG_DOWN = V3(0, -0.985, 0.17), SLIDE_TRAVEL = 0.024, _ew = V3(0, 0, 0);
  function ejectCasing() {
    if (!vmp.casings.length) return; const c = vmp.casings.find(k => k.t <= 0) || vmp.casings[0];
    vmp.eject.getWorldPosition(_ew); c.o.position.copy(_ew); c.o.visible = true; c.t = 0.75;
    c.v.set(-0.08 + Math.random() * 0.08, 1.25 + Math.random() * 0.25, 0.05 + Math.random() * 0.06); c.o.scale.setScalar(2.0); c.o.rotation.set(0, 0, 0); c.w.set((Math.random() - 0.5) * 6, 8 + Math.random() * 4, (Math.random() - 0.5) * 4); // up and over the slide: stays on a portrait screen
  }
  NR.bus.on('shot', () => { if (!vmp.slide) return; vmp.fireT = 0; vmp.ejectPending = true; });
  function animPistol(rdt) {
    vmp.fireT += rdt;
    const empty = vmp.forceLock || (P.slideLock !== undefined ? !!P.slideLock : P.rounds <= 0);
    const dur = P.reloadDur || C.GUN_RELOAD;
    if (vmp.manualReload > 0) vmp.manualReload -= rdt;
    const rt = P.reloadT > 0 ? P.reloadT : vmp.manualReload;
    const f = rt > 0 ? 1 - rt / dur : -1; // reload progress 0..1
    let s = 0; const t = vmp.fireT;
    if (t < 0.045) s = t / 0.045; else if (t < 0.12) s = 1 - (t - 0.045) / 0.075;
    if (vmp.ejectPending && t > 0.03) { vmp.ejectPending = false; ejectCasing(); }
    if (empty && t >= 0.045) s = 1;                  // slide stays back on the last round
    if (f >= 0 && f < 0.8 && (empty || vmp.lockedAtReload)) { s = 1; vmp.lockedAtReload = true; }
    if (f >= 0.8 && vmp.lockedAtReload) s = Math.max(0, 1 - (f - 0.8) / 0.04); // slide release snaps it home
    if (f < 0) { vmp.lockedAtReload = false; if (vmp.forceLock && vmp.manualReload <= 0 && vmp.reloadDone) vmp.forceLock = false; }
    vmp.slide.position.z = vmp.slideZ + s * SLIDE_TRAVEL;
    vmp.hammer.rotation.x = -0.15 * s;
    // magazine: out (0..0.22), gone (..0.45), in (..0.72)
    let d = 0, vis = true;
    if (f >= 0) { if (f < 0.22) d = Math.pow(f / 0.22, 2) * 0.2; else if (f < 0.45) vis = false; else if (f < 0.72) d = Math.pow(1 - (f - 0.45) / 0.27, 2) * 0.14; }
    vmp.mag.visible = vis; vmp.mag.position.copy(vmp.magPos).addScaledVector(MAG_DOWN, d);
    if (f >= 0.8) vmp.reloadDone = true;
    for (const c of vmp.casings) if (c.t > 0) {
      c.t -= rdt; c.v.y -= 6.5 * rdt; c.o.position.addScaledVector(c.v, rdt); c.o.rotation.x += c.w.x * rdt; c.o.rotation.y += c.w.y * rdt; c.o.rotation.z += c.w.z * rdt;
      if (c.t <= 0) c.o.visible = false;
    }
  }
  // test / director hook: P.vm.anim('fire' | 'lastShot' | 'reload' | 'idle')
  vm.anim = (name) => {
    if (!vmp.slide) return false;
    if (name === 'fire' || name === 'lastShot') { vmp.fireT = 0; vmp.ejectPending = true; P.recoil = Math.min(1.2, P.recoil + 1); flashSpr.visible = true; vmFlash.intensity = 6; flashT = 0.05; if (name === 'lastShot') { vmp.forceLock = true; vmp.reloadDone = false; } }
    else if (name === 'reload') { vmp.manualReload = P.reloadDur || C.GUN_RELOAD; vmp.reloadDone = false; }
    else if (name === 'idle') { vmp.fireT = 9; vmp.forceLock = false; vmp.manualReload = 0; }
    return true;
  };

  // ---- smoking + holster layer: P.vm.anim('draw' | 'holster' | 'drag' | 'idleSmoke'); state flags P.vm.drawn, P.vm.busy.
  // The toggle that calls draw/holster belongs to the game logic; P.vm.cigDefault keeps the lit cigarette in the left hand.
  const vs = vm.state = { drawT: P.drawn ? 1 : 0, drawFrom: 0, drawTo: P.drawn ? 1 : 0, drawDur: 0.45, drawClock: 9, dragT: -1, boost: 0 };
  vm.drawn = !!P.drawn; vm.busy = false; vm.cigDefault = true;
  // drag fx: warm ember light, a screen-bottom glow + vignette overlay, a paper crackle, and an exhale plume of soft sprites
  const emberLight = new T.PointLight(0xff7020, 0, 0.7, 2);
  const glowOv = document.createElement('div');
  Object.assign(glowOv.style, { position: 'absolute', pointerEvents: 'none', opacity: '0', zIndex: '1',
    background: 'radial-gradient(ellipse 75% 40% at 50% 104%, rgba(255,128,40,0.62), rgba(255,96,24,0.16) 55%, rgba(0,0,0,0) 78%), radial-gradient(ellipse 80% 70% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)' });
  { const ui = document.getElementById('ui'); (ui ? ui.parentNode : document.body).insertBefore(glowOv, ui || null); }
  let ac = null;
  function crackle(dur) { // tobacco/paper crackle: sparse filtered clicks over a soft hiss
    try {
      ac = ac || new (window.AudioContext || window.webkitAudioContext)(); if (ac.state === 'suspended') ac.resume();
      const n = Math.floor(ac.sampleRate * dur), buf = ac.createBuffer(1, n, ac.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * 0.05 * Math.sin(Math.PI * i / n);
      for (let k = 0; k < 70; k++) { const at = Math.floor(Math.random() * (n - 400)), a = 0.4 + Math.random() * 0.6; for (let j = 0; j < 300; j++) d[at + j] += (Math.random() * 2 - 1) * a * Math.exp(-j / 40); }
      const src = ac.createBufferSource(); src.buffer = buf; const f = ac.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 3200; f.Q.value = 0.6;
      const g = ac.createGain(); g.gain.value = 0.32 * ((NR.core.settings.sfx == null) ? 0.8 : NR.core.settings.sfx);
      src.connect(f); f.connect(g); g.connect(ac.destination); src.start();
    } catch (e) { /* audio is optional */ }
  }
  const puffTex = NR.fx.canvasTex(64, 64, (g, w, h) => { const r = g.createRadialGradient(32, 32, 2, 32, 32, 31); r.addColorStop(0, 'rgba(255,255,255,0.9)'); r.addColorStop(0.45, 'rgba(255,255,255,0.35)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 40; i++) { g.fillStyle = `rgba(0,0,0,${Math.random() * 0.12})`; g.beginPath(); g.arc(Math.random() * 64, Math.random() * 64, 2 + Math.random() * 7, 0, 7); g.fill(); } });
  const puffs = [];
  for (let i = 0; i < 34; i++) { const sp = new T.Sprite(new T.SpriteMaterial({ map: puffTex, color: 0xb8b2aa, transparent: true, depthTest: false, depthWrite: false, opacity: 0 })); sp.visible = false; sp.renderOrder = 20; vm.scene.add(sp); puffs.push({ sp, v: V3(0, 0, 0), t: 0, life: 1, s0: 0.03, s1: 0.2, a: 0.3 }); }
  function puff(wisp) {
    const p = puffs.find(q => q.t <= 0); if (!p) return;
    p.t = p.life = wisp ? 0.9 + Math.random() * 0.4 : 1.4 + Math.random() * 0.5;
    p.sp.position.set((Math.random() - 0.5) * 0.02, -0.088, -0.16 - Math.random() * 0.02);
    p.v.set(0.012 + Math.random() * 0.02 + (wisp ? (Math.random() - 0.3) * 0.05 : 0), wisp ? 0.11 + Math.random() * 0.05 : 0.07 + Math.random() * 0.04, -0.05 - Math.random() * 0.04);
    p.s0 = wisp ? 0.012 : 0.03; p.s1 = wisp ? 0.07 : 0.2 + Math.random() * 0.08; p.a = wisp ? 0.18 : 0.22; p.sp.material.rotation = Math.random() * 6.28; p.sp.visible = true;
  }
  function updatePuffs(rdt) {
    for (const p of puffs) { if (p.t <= 0) continue; p.t -= rdt; const k = 1 - p.t / p.life;
      p.sp.position.addScaledVector(p.v, rdt); p.v.y *= 1 - rdt * 0.6; p.v.z *= 1 - rdt * 0.8;
      const sc = p.s0 + (p.s1 - p.s0) * Math.sqrt(k); p.sp.scale.set(sc, sc, 1); p.sp.material.rotation += rdt * 0.25;
      p.sp.material.opacity = p.a * Math.min(1, k / 0.12) * (1 - k) * (1 - k * 0.3); if (p.t <= 0) p.sp.visible = false; }
  }
  const ease = t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  const easeOutBack = t => { const c = 1.4; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  const animGun = vm.anim;
  vm.anim = (name) => {
    if (name === 'draw' || name === 'holster') {
      const to = name === 'draw' ? 1 : 0; if (vs.drawTo === to) return true;
      vs.drawFrom = vs.drawT; vs.drawTo = to; vs.drawDur = to ? 0.45 : 0.4; vs.drawClock = 0; vm.drawn = !!to; vm.busy = true;
      if (P.drawn !== !!to) { P.drawn = !!to; P.drawDur = P.drawT = vs.drawDur; } // called directly (tests/director), not via P.toggleGun
      return true;
    }
    if (name === 'drag') { vs.dragT = 0; vm.busy = true; return true; }
    if (name === 'idleSmoke') { vs.dragT = -1; vm.cigDefault = true; return true; }
    return animGun(name);
  };
  // drag pose: palm to the face, filter end at the lips just below the lens, lit end pointing away; hand partly below the frame
  const LIPS = { at: V3(0.01, -0.088, -0.075), pos: V3(0.016, -0.163, -0.1), q: new T.Quaternion().setFromEuler(new T.Euler(-1.35, 0.1, Math.PI / 2 + 0.25, 'ZYX')) }, EDGE = V3(-0.035, -0.035, 0), _q = new T.Quaternion();
  function animSmoke(rdt, live) {
    // draw / holster: the right hand drops under the coat to the hip holster and comes back up with the pistol
    if (vs.drawClock < vs.drawDur) {
      vs.drawClock += rdt; const k = Math.min(1, vs.drawClock / vs.drawDur);
      vs.drawT = vs.drawTo ? vs.drawFrom + (1 - vs.drawFrom) * easeOutBack(k) : vs.drawFrom * (1 - ease(k));
    }
    const dh = 1 - Math.min(1, Math.max(0, vs.drawT));
    gunRig.visible = gunRig.visible && dh < 0.85;
    gunRig.position.x += dh * 0.06; gunRig.position.y -= dh * 0.34; gunRig.position.z -= dh * 0.04; // down and away: the coat sleeve never swings into the lens
    gunRig.rotation.x -= dh * 0.55; gunRig.rotation.z -= dh * 0.35;
    // drag (0-0.5 raise, 0.5-1.4 hold: ember flares + crackle, 1.4-1.9 lower, 1.9-3.5 exhale plume from the bottom of the screen)
    let dk = 0, idleOn = 1; vs.boost = 0;
    if (vs.dragT >= 0) {
      const t0 = vs.dragT, t = (vs.dragT += rdt);
      dk = t < 0.5 ? ease(t / 0.5) : t < 1.4 ? 1 : t < 1.9 ? 1 - ease((t - 1.4) / 0.5) : 0;
      vs.boost = t > 0.45 && t < 1.45 ? Math.pow(Math.sin(Math.min(1, (t - 0.45) / 1.0) * Math.PI), 0.7) : 0;
      if (t0 < 0.5 && t >= 0.5) { crackle(0.9); if (NR.audio && NR.audio.fx && NR.audio.fx.inhale) NR.audio.fx.inhale(); }
      if (t > 1.9 && t < 2.65) { vs.puffClock = (vs.puffClock || 0) + rdt; while (vs.puffClock > 0.03) { vs.puffClock -= 0.03; puff(Math.random() < 0.3); } }
      idleOn = t < 0.4 ? 1 - t / 0.4 : t < 3.0 ? 0 : Math.min(1, (t - 3.0) / 0.5);
      if (t > 3.6) { vs.dragT = -1; vs.puffClock = 0; }
    }
    updatePuffs(rdt);
    cigSmoke.material.uniforms.on.value = idleOn;
    emberLight.intensity = 0.05 * vs.boost;
    if (vs.boost > 0.01 || glowOv.style.opacity !== '0') { const v = NR.core.view; if (v) Object.assign(glowOv.style, { left: v.left + 'px', top: v.top + 'px', width: v.w + 'px', height: v.h + 'px' }); glowOv.style.opacity = (0.85 * vs.boost).toFixed(3); }
    if (!P.controlled && dk > 0) NR.core.camera.rotation.x -= 0.07 * dk; // the head dips ~4 degrees to meet the hand
    vm.busy = vs.drawClock < vs.drawDur || vs.dragT >= 0; vm.drawn = !!P.drawn;
    if (!P.armed && vs.drawT > 0 && vs.drawClock >= vs.drawDur) { vs.drawT = 0; vs.drawTo = 0; } // disarmed by the story
    const lit = !!(P.litT > 0 || P.focusT > 0 || P.forceCig);
    const show = (lit && (live || P.forceCig)) || (vm.cigDefault && P.vmGLB && live) || dk > 0;
    cigRig.visible = show;
    if (!show) return;
    const gunUp = gunRig.visible ? Math.min(1, vs.drawT) : 0, t = NR.core.time, k = P.focusT > 0 ? 0.04 : 0;
    cigRig.position.set(CIG_HOME.x + EDGE.x * gunUp + Math.sin(t * 0.5) * 0.003, CIG_HOME.y + EDGE.y * gunUp + k + Math.sin(P.bob * 0.5 + 1) * 0.006 + Math.sin(t * 0.8) * 0.002, CIG_HOME.z);
    if (P.vmGLB && vmp.rigL) {
      cigRig.position.lerp(LIPS.pos, dk); cigRig.rotation.set(0, 0, Math.sin(t * 0.7) * 0.02 * (1 - dk));
      _q.copy(vmp.rigLRest).slerp(LIPS.q, dk); vmp.rigL.quaternion.copy(_q);
    }
    emberGlow.material.opacity = Math.min(1, 0.26 + Math.sin(t * 9) * 0.08 + vs.boost * 0.55);
    if (P.vmGLB) emberGlow.scale.setScalar(0.034 * (1 + 0.8 * vs.boost));
    if (vmp.emberMat) vmp.emberMat.color.setRGB(0.82 + 0.18 * vs.boost, 0.24 + 0.36 * vs.boost, 0.05 + 0.12 * vs.boost);
  }

  // ---------------------------------------------------------------- combat helpers
  function enemiesAlert() { return NR.actors.enemies.some(e => !e.dead && e.state !== 'dormant' && e.state !== 'idle'); }
  P.inCombat = enemiesAlert;
  const fwd = () => { const cp = Math.cos(P.pitch); return V3(-Math.sin(P.yaw) * cp, Math.sin(P.pitch), -Math.cos(P.yaw) * cp); };
  P.fwd = fwd;
  P.eye = () => V3(P.pos.x, P.pos.y + C.EYE, P.pos.z);
  // nearest enemy aim point inside a cone around the view direction (with line of sight)
  function assistTarget(cone) {
    const o = P.eye(), f = fwd(); let best = null, ba = cone;
    for (const e of NR.actors.enemies) {
      if (e.dead || e.state === 'dormant') continue;
      for (const [pt, head] of [[e.headC, true], [V3(e.pos.x + e.peekOff.x, 1.15 - 0.45 * e.crouch, e.pos.z + e.peekOff.z), false]]) {
        const d = pt.clone().sub(o), dist = d.length(); d.normalize(); const a = Math.acos(NR.clamp(d.dot(f), -1, 1));
        const lim = head ? cone * 0.45 : cone; if (a < lim && a < ba + (head ? 0.01 : 0) && dist < 40 && L.los(o, pt)) { ba = a; best = { pt, dir: d, head, e }; }
      }
    }
    return best;
  }
  P.assistTarget = assistTarget;
  function shoot() {
    if (!P.armed || !P.drawn || P.drawT > 0 || P.reloadT > 0 || P.fireCd > 0) return;
    if (P.rounds <= 0) { NR.bus.emit('dryFire'); P.fireCd = 0.28; P.slideLock = true; return; } // slide locked back: click, then RELOAD is prompted
    P.rounds--; P.fireCd = C.GUN_RATE; P.shots++;
    const o = P.eye(); let d = fwd();
    const focus = P.focusT > 0;
    const spread = focus ? 0 : (P.moving ? 0.014 : 0.004) + P.recoil * 0.03;
    d.x += (Math.random() - 0.5) * spread; d.y += (Math.random() - 0.5) * spread; d.z += (Math.random() - 0.5) * spread; d.normalize();
    if (NR.core.isTouch || NR.controls.lastDevice === 'touch') { const a = assistTarget(C.ASSIST_CONE * (focus ? 1.4 : 1)); if (a) d.lerp(a.dir, 0.65).normalize(); } // light bullet magnetism
    let best = null, wh = L.ray(o, d, C.GUN_RANGE), maxT = wh ? wh.t : C.GUN_RANGE;
    for (const e of NR.actors.enemies) { const h = e.hitTest(o, d, maxT); if (h && (!best || h.t < best.t)) best = Object.assign(h, { e }); }
    const muzzleW = o.clone().addScaledVector(d, 0.5).add(V3(0, -0.12, 0));
    if (best) {
      P.hits++; if (best.head) P.heads++;
      const killed = best.e.damage(C.GUN_DMG * (best.head ? C.HEAD_MULT : 1) * (focus ? 1.25 : 1), best.point, d, best.head);
      NR.bus.emit('hitEnemy', { head: best.head, killed });
      NR.fx.tracer(muzzleW, best.point);
    } else {
      const end = wh ? wh.point : o.clone().addScaledVector(d, C.GUN_RANGE);
      NR.fx.tracer(muzzleW, end); if (wh) NR.fx.impact(wh.point, wh.normal);
    }
    // any shot alerts every enemy who can hear it
    for (const e of NR.actors.enemies) if (!e.dead && e.state === 'idle') e.alert();
    P.recoil = Math.min(1.4, P.recoil + (focus ? 0.5 : 1.1));
    P.pitch += (focus ? 0.018 : 0.05); P.yaw += (Math.random() - 0.5) * (focus ? 0.005 : 0.02); // .45: stronger muzzle rise
    NR.fx.muzzle(o.clone().addScaledVector(d, 0.6), 1); vmFlash.intensity = 6; flashSpr.visible = true; flashT = 0.05;
    NR.core.shake(0.012, 0.08);
    if (P.rounds === 0) { P.slideLock = true; NR.bus.emit('slideLock'); }
    NR.bus.emit('shot', { rounds: P.rounds });
  }
  let flashT = 0;
  function startReload() {
    if (!P.armed || !P.drawn || P.drawT > 0 || P.reloadT > 0 || P.rounds >= C.GUN_MAG + 1) return;
    if (P.mags <= 0) { NR.bus.emit('noMags'); return; }
    P.reloadEmpty = P.rounds === 0; P.reloadDur = P.reloadEmpty ? C.GUN_RELOAD_EMPTY : C.GUN_RELOAD; P.reloadT = P.reloadDur;
    NR.bus.emit('reload', { empty: P.reloadEmpty, dur: P.reloadDur });
  }
  // spare magazines come off the men you drop (always one when you have none)
  NR.bus.on('enemyDown', () => { if (P.mags < C.MAGS_MAX && (P.mags === 0 || Math.random() < 0.45)) { P.mags++; NR.bus.emit('magPickup', { mags: P.mags }); } });
  P.reload = startReload;
  function smoke() {
    if (P.pack <= 0) { NR.bus.emit('noSmokes'); return false; }
    P.pack--; P.smoked++; P.litT = C.SMOKE_LIT;
    const combat = enemiesAlert();
    if (combat) { P.focusT = C.FOCUS_TIME; NR.bus.emit('focus', {}); }
    NR.bus.emit('smoke', { combat, pack: P.pack });
    return true;
  }
  P.smoke = smoke;
  P.hurt = (d) => {
    if (P.god || P.hp <= 0) return;
    P.hp = Math.max(0, P.hp - d.dmg); P.lastHitT = 0; NR.core.flash(0x700000, 0.25, 0.25); NR.core.shake(0.02, 0.15);
    NR.bus.emit('playerHurt', { hp: P.hp, from: d.from });
    if (P.hp <= 0) { P.lives--; NR.bus.emit('playerDown', { lives: P.lives }); }
  };
  NR.bus.on('playerHit', d => { if (NR.core.state === 'PLAY') P.hurt(d); });

  // ---------------------------------------------------------------- per-frame
  P.update = (dt, rdt, input) => {
    const cam = NR.core.camera, playing = NR.core.state === 'PLAY';
    // look (real time; slows with the world in focus a bit less than the world)
    if (playing) {
      let lx = input.lookX, ly = input.lookY;
      if ((NR.controls.lastDevice === 'touch') && P.armed) { const a = assistTarget(0.04); if (a) { lx *= C.ASSIST_FRICTION; ly *= C.ASSIST_FRICTION; } }
      P.yaw -= lx; P.pitch = NR.clamp(P.pitch - ly, -1.25, 1.25);
    }
    // move
    const mx = playing ? input.mx : 0, my = playing ? input.my : 0, mag = Math.min(1, Math.hypot(mx, my));
    const sy = Math.sin(P.yaw), cy = Math.cos(P.yaw);
    const want = V3((mx * cy - my * sy), 0, (-mx * sy - my * cy)).multiplyScalar(C.WALK);
    P.vel.lerp(want, Math.min(1, rdt * 12));
    P.moving = P.vel.lengthSq() > 0.6;
    if (L && playing) { P.pos.addScaledVector(P.vel, rdt); const g = L.collide(P.pos, C.RADIUS, P.pos.y, true); P.pos.y += (g - P.pos.y) * Math.min(1, rdt * 14); }
    P.bob += rdt * (P.moving ? 9 : 0) * mag;
    // weapon
    P.fireCd = Math.max(0, P.fireCd - rdt);
    if (playing && P.armed) { if (input.gun) P.toggleGun(); if (input.fire) shoot(); if (input.reload) startReload(); }
    if (P.drawT > 0) P.drawT = Math.max(0, P.drawT - rdt);
    if (P.reloadT > 0) { P.reloadT -= rdt; if (P.reloadT <= 0) { P.rounds = C.GUN_MAG + (P.reloadEmpty ? 0 : 1); P.mags--; P.slideLock = false; NR.bus.emit('reloaded', { rounds: P.rounds }); } } // 7+1 keeps the chambered round; from empty, 7
    P.recoil = Math.max(0, P.recoil - rdt * 3.2);
    if (playing && input.smoke) smoke();
    // cigarette + focus (real time)
    if (P.litT > 0) P.litT -= rdt;
    if (P.focusT > 0) { P.focusT -= rdt; if (P.focusT <= 0) NR.bus.emit('focusEnd'); }
    P.focus = P.focusT > 0 ? 1 : 0;
    const ts = P.focusT > 0 ? C.FOCUS_SCALE : 1; NR.core.timeScale += (ts - NR.core.timeScale) * Math.min(1, rdt * 10);
    NR.core.fx.focus += ((P.focusT > 0 ? 1 : 0) - NR.core.fx.focus) * Math.min(1, rdt * 6);
    // scan
    P.scanning = playing && input.scan;
    NR.core.fx.scan += ((P.scanning ? 1 : 0) - NR.core.fx.scan) * Math.min(1, rdt * 8);
    // health: recover after a pause, faster when no enemy can see you (cover)
    P.lastHitT += rdt;
    if (playing && P.hp > 0 && P.hp < C.HP && P.lastHitT > C.REGEN_DELAY) {
      const e = P.eye(); P.inCover = !NR.actors.enemies.some(en => !en.dead && en.state !== 'dormant' && en.state !== 'idle' && L.los(en.eye, e));
      P.hp = Math.min(C.HP, P.hp + (P.inCover ? C.REGEN_COVER : C.REGEN) * rdt);
    }
    const hurtT = Math.pow(1 - P.hp / C.HP, 0.8) + (P.lastHitT < 0.3 ? (0.3 - P.lastHitT) : 0);
    NR.core.fx.hurt += (hurtT - NR.core.fx.hurt) * Math.min(1, rdt * 8);
    // camera
    if (!P.controlled) { cam.position.set(P.pos.x, P.pos.y + C.EYE + Math.sin(P.bob) * 0.025, P.pos.z); cam.rotation.set(P.pitch + P.recoil * 0.02, P.yaw, 0); }
    // view models
    const live = NR.core.state === 'PLAY' || NR.core.state === 'DOWN'; gunRig.visible = P.armed && !P.hideGun && live && (P.drawn || P.drawT > 0);
    const dk = P.drawT > 0 ? (P.drawn ? 1 - P.drawT / P.drawDur : P.drawT / P.drawDur) : 1; // 0 = down out of frame, 1 = up
    const rel = P.reloadT > 0 ? Math.sin(Math.PI * (1 - P.reloadT / P.reloadDur)) : 0;
    gunRig.position.set(GUN_HOME.x + Math.sin(P.bob * 0.5) * 0.008 - rel * (vmp.slide ? 0.045 : 0.06), GUN_HOME.y + Math.abs(Math.cos(P.bob * 0.5)) * 0.008 + rel * (vmp.slide ? 0.02 : -0.05) + P.recoil * 0.015, GUN_HOME.z + P.recoil * 0.04 + rel * (vmp.slide ? 0.02 : 0));
    if (vmp.slide) { gunRig.rotation.set(P.recoil * 0.3 + rel * 0.2, rel * 0.25, -rel * 0.65); animPistol(rdt); } else { // (1911 reload: low, muzzle up-left, magwell toward the camera)
      gunRig.rotation.set(P.recoil * 0.22 + rel * 0.5, 0.1, rel * 0.9);
      vmp.drum.rotation.y += rel > 0.1 ? rdt * 18 : 0;
    }
    flashT -= rdt; if (flashT <= 0) { flashSpr.visible = false; vmFlash.intensity = 0; }
    animSmoke(rdt, live);
  };
  P.reset = () => { P.rounds = C.GUN_ROUNDS; P.mags = Math.max(P.mags, C.MAGS_START); P.slideLock = false; P.reloadT = 0; P.fireCd = 0; P.recoil = 0; P.litT = 0; P.focusT = 0; P.resetHealth(); };
})();
