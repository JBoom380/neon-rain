// NEON RAIN player: first-person movement and look, revolver (6 shots, reload, head shots, light aim assist on touch),
// health (red screen edges, recovery in cover, 3 lives), cigarettes (FOCUS slow-mo / THINK / OFFER), SCAN, INTERACT.
(function () {
  const T = THREE, C = NR.cfg, V3 = (x, y, z) => new T.Vector3(x, y, z);
  const P = NR.player = {
    pos: V3(0, 0, 0), yaw: 0, pitch: 0, vel: V3(0, 0, 0), hp: C.HP, lives: C.LIVES, rounds: C.GUN_ROUNDS, armed: false,
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
  vm.scene.add(new T.AmbientLight(0x9098a8, 1.4)); const vmRim = new T.DirectionalLight(0x9fd0ff, 2.2); vmRim.position.set(1, 0.6, -1); vm.scene.add(vmRim); const vmKey = new T.DirectionalLight(0xffe8d0, 2.4); vmKey.position.set(-1, 1.5, 0.5); vm.scene.add(vmKey);
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
    if (!P.armed || P.reloadT > 0 || P.fireCd > 0) return;
    if (P.rounds <= 0) { NR.bus.emit('dryFire'); P.fireCd = 0.3; startReload(); return; }
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
    P.recoil = Math.min(1.2, P.recoil + (focus ? 0.45 : 1));
    P.pitch += (focus ? 0.012 : 0.035); P.yaw += (Math.random() - 0.5) * (focus ? 0.004 : 0.016);
    NR.fx.muzzle(o.clone().addScaledVector(d, 0.6), 1); vmFlash.intensity = 6; flashSpr.visible = true; flashT = 0.05;
    NR.core.shake(0.012, 0.08);
    NR.bus.emit('shot', { rounds: P.rounds });
    if (P.rounds === 0) setTimeout(() => { if (P.rounds === 0 && P.reloadT <= 0) startReload(); }, 380);
  }
  let flashT = 0;
  function startReload() { if (!P.armed || P.reloadT > 0 || P.rounds >= C.GUN_ROUNDS) return; P.reloadT = C.GUN_RELOAD; NR.bus.emit('reload'); }
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
    if (playing && P.armed) { if (input.fire) shoot(); if (input.reload) startReload(); }
    if (P.reloadT > 0) { P.reloadT -= rdt; if (P.reloadT <= 0) { P.rounds = C.GUN_ROUNDS; NR.bus.emit('reloaded'); } }
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
    const live = NR.core.state === 'PLAY' || NR.core.state === 'DOWN'; gunRig.visible = P.armed && !P.hideGun && live;
    const rel = P.reloadT > 0 ? Math.sin(Math.PI * (1 - P.reloadT / C.GUN_RELOAD)) : 0;
    gunRig.position.set(GUN_HOME.x + Math.sin(P.bob * 0.5) * 0.008 - rel * 0.06, GUN_HOME.y + Math.abs(Math.cos(P.bob * 0.5)) * 0.008 - rel * 0.05 + P.recoil * 0.015, GUN_HOME.z + P.recoil * 0.04);
    gunRig.rotation.set(P.recoil * 0.22 + rel * 0.5, 0.1, rel * 0.9);
    gun.userData.drum.rotation.y += rel > 0.1 ? rdt * 18 : 0;
    flashT -= rdt; if (flashT <= 0) { flashSpr.visible = false; vmFlash.intensity = 0; }
    const lit = !!(P.litT > 0 || P.focusT > 0 || P.forceCig);
    cigRig.visible = lit && (live || P.forceCig);
    if (lit) { const k = P.focusT > 0 ? 0.04 : 0; cigRig.position.set(CIG_HOME.x, CIG_HOME.y + k + Math.sin(P.bob * 0.5 + 1) * 0.006, CIG_HOME.z); emberGlow.material.opacity = 0.7 + Math.sin(NR.core.time * 9) * 0.3; }
  };
  P.reset = () => { P.rounds = C.GUN_ROUNDS; P.reloadT = 0; P.fireCd = 0; P.recoil = 0; P.litT = 0; P.focusT = 0; P.resetHealth(); };
})();
