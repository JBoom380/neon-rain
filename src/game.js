// NEON RAIN game: the director. Loads levels, runs the slice beats (office -> alley -> Blue Orchid), SCAN and INTERACT,
// fights with lives and respawn, the case file, pause, and the end-of-slice card.
(function () {
  const T = THREE, C = NR.cfg, V3 = (x, y, z) => new T.Vector3(x, y, z);
  const core = NR.core, P = NR.player, S = NR.story, UI = NR.ui, A = NR.actors;
  const levels = {};
  const G = NR.game = {
    level: null, chars: [], waits: [], triggers: [], interacts: [], clues: [], beat: 'boot', lockMove: false, fight: null, scanProgress: 0,
    caseData: { clues: {}, notes: [], verdicts: {} }, t0: 0, lookTarget: null, prevState: 'PLAY',
  };
  const wait = s => core.wait(s);
  const waitFor = cond => new Promise(r => G.waits.push({ cond, r }));
  G.waitFor = waitFor;

  // ---------------------------------------------------------------- levels
  function load(name) {
    if (!levels[name]) levels[name] = NR.world.build[name](core.settings.quality);
    const L = levels[name]; G.level = L;
    for (const c of G.chars) c.remove(); G.chars = []; A.clear(); G.triggers = []; G.interacts = []; G.clues = [];
    core.setScene(L.scene, L.shaft); NR.fx.attach(L); P.setLevel(L);
    P.place(L.spawn.pos, L.spawn.yaw, 0);
    NR.audio.rainBed(true, L.outdoor ? 0.09 : 0.035);
    return L;
  }
  G.load = load;
  function yawPitchTo(p) { const e = P.eye(), dx = p.x - e.x, dy = p.y - e.y, dz = p.z - e.z; return [Math.atan2(-dx, -dz), Math.atan2(dy, Math.hypot(dx, dz))]; }
  function lookAt(p, secs) { G.lookTarget = p; G.lookRate = secs ? 3 / secs : 4; }
  function setState(s) { core.setState(s); UI.letterbox(s === 'CUTSCENE'); }
  async function scene(lines) { setState('CUTSCENE'); await UI.lines(lines); }

  // ---------------------------------------------------------------- interactables, clues, triggers
  function interact(o) { G.interacts.push(Object.assign({ r: 1.6, enabled: () => true }, o)); return o; }
  function trigger(test, fn) { G.triggers.push({ test, fn }); }
  function addClue(id, pos, mesh) {
    const glow = NR.world.glow(0xffb040, 0.55, pos.x, pos.y, pos.z, G.level.scene, 0); glow.material.depthTest = false; glow.renderOrder = 9;
    if (mesh) { mesh.position.copy(pos); G.level.scene.add(mesh); }
    const c = { id, pos: pos.clone(), mesh, glow, found: false, prog: 0 }; G.clues.push(c); return c;
  }
  function foundCount() { return Object.keys(G.caseData.clues).filter(k => S.clues[k]).length; }
  function note(t) { if (!G.caseData.notes.includes(t)) G.caseData.notes.push(t); save(); }
  function save() { try { localStorage.setItem(C.CASE_KEY, JSON.stringify(G.caseData)); } catch (e) {} }

  function updateScan(rdt) {
    G.scanProgress = 0;
    if (!G.clues.length) return;
    const e = P.eye(), f = P.fwd(), t = core.time;
    let target = null;
    for (const c of G.clues) {
      const d = c.pos.clone().sub(e), dist = d.length(); d.normalize();
      const vis = P.scanning && dist < 11;
      c.glow.material.opacity += ((vis ? (c.found && !(P.litT > 0 && !G.caseData.clues[c.id].think) ? 0.35 : 0.9 + Math.sin(t * 6) * 0.1) : 0) - c.glow.material.opacity) * Math.min(1, rdt * 8);
      c.glow.scale.setScalar(NR.clamp(dist * 0.12, 0.12, 0.45) + Math.sin(t * 4 + c.pos.x) * 0.03);
      if (!vis) { c.prog = 0; continue; }
      const can = !c.found || (P.litT > 0 && !G.caseData.clues[c.id].think);
      if (!can) continue;
      const ang = Math.acos(NR.clamp(d.dot(f), -1, 1));
      if (dist < 4.8 && ang < 0.2 + 0.25 / Math.max(1, dist) && G.level.los(e, c.pos.clone().addScaledVector(d, -0.15))) target = c; else c.prog = Math.max(0, c.prog - rdt * 2);
    }
    if (target) {
      target.prog += rdt / 0.75; G.scanProgress = Math.min(1, target.prog);
      if (target.prog >= 1) { target.prog = 0; clueFound(target); }
    }
  }
  function clueFound(c) {
    const info = S.clues[c.id], think = P.litT > 0, had = c.found;
    c.found = true; G.caseData.clues[c.id] = { think: think || (G.caseData.clues[c.id] && G.caseData.clues[c.id].think) };
    if (had && think) UI.toast('THINK', info.think, 6); else UI.toast('CLUE ' + foundCount() + '/3: ' + info.name.toUpperCase(), think ? info.note + '<br><i style="color:#ffb070">' + info.think + '</i>' : info.note, think ? 7 : 4.5);
    NR.bus.emit('clue', { id: c.id, think }); save(); refreshObjective();
  }
  function updateInteract() {
    let best = null, bd = 1e9; const e = P.eye(), f = P.fwd();
    if (core.state === 'PLAY') for (const it of G.interacts) {
      if (!it.enabled()) continue; const d = V3(it.pos.x - P.pos.x, 0, it.pos.z - P.pos.z), dist = d.length(); if (dist > it.r) continue;
      const to = it.pos.clone().sub(e).normalize(); const a = Math.acos(NR.clamp(to.dot(f), -1, 1)); if (a > 0.9 && dist > 0.9) continue;
      if (dist + a < bd) { bd = dist + a; best = it; }
    }
    G.focusInteract = best;
    NR.controls.setInteract(best ? best.label : null);
    const touchUI = core.isTouch || NR.controls.lastDevice === 'touch';
    UI.prompt(best && !touchUI ? 'E  ' + best.label : (P.armed && !touchUI && P.rounds === 0 ? 'R  RELOAD' : ''));
    return best;
  }

  // ---------------------------------------------------------------- fights, lives, respawn
  function startFight(spawnFn, checkpoint) {
    G.fight = { spawnFn, checkpoint: { pos: checkpoint.pos.clone(), yaw: checkpoint.yaw }, enemies: spawnFn() };
    return G.fight;
  }
  const alive = () => A.enemies.some(e => !e.dead);
  NR.bus.on('playerDown', async () => {
    if (!G.fight) { P.resetHealth(); return; }
    setState('DOWN'); NR.core.timeScale = 0.35; await wait(1.0);
    await core.fadeTo(1, 0.6); NR.core.timeScale = 1;
    if (P.lives <= 0) { await UI.gameOver(); P.lives = C.LIVES; }
    A.clear(); G.fight.enemies = G.fight.spawnFn(); for (const e of G.fight.enemies) if (e.state === 'idle' || e.state === 'dormant') e.alert();
    P.place(G.fight.checkpoint.pos, G.fight.checkpoint.yaw, 0); P.reset();
    UI.toast('LIVES ' + P.lives, 'Back on your feet. The rain did not wait.', 2.5);
    setState('PLAY'); await core.fadeTo(0, 0.6);
  });
  NR.bus.on('enemyDown', d => {
    const e = d.enemy; if (e.drops && Math.random() < e.drops) { P.pack = Math.min(C.PACK_MAX, P.pack + 1); UI.toast('+1 SMOKE', 'Lifted from his breast pocket.', 2); }
    if (d.head) UI.toast('HEAD SHOT', '', 1.0);
  });

  // ---------------------------------------------------------------- pause + case file
  G.pause = (on) => {
    if (on && core.state === 'PLAY') { G.prevState = 'PLAY'; NR.controls.exitLock(); setState('PAUSE'); UI.show('pause', true); }
    else if (!on && core.state === 'PAUSE') { UI.show('pause', false); setState('PLAY'); }
  };
  G.openCase = () => {
    if (!['PLAY', 'PAUSE'].includes(core.state)) return;
    G.caseFrom = core.state; NR.controls.exitLock(); UI.show('pause', false); setState('CASE'); UI.caseFile(true, G.caseData);
  };
  G.closeCase = () => { UI.caseFile(false); if (G.caseFrom === 'PAUSE') { setState('PAUSE'); UI.show('pause', true); } else setState('PLAY'); };
  function refreshObjective() { if (G.objFn) UI.objective(G.objFn()); }
  function objective(fn) { G.objFn = typeof fn === 'function' ? fn : () => fn; refreshObjective(); }

  // ================================================================ BEAT 1: the office
  async function office() {
    G.beat = 'office'; const L = load('office'); P.armed = false; P.hideGun = false; P.lives = C.LIVES;
    P.place(L.spawn.pos, 0.35, 0.05); setState('CUTSCENE'); core.fx.fade = 1;
    await UI.card(S.office.card, 2.4);
    lookAt(V3(0.85, 1.8, -4.6), 5); core.fadeTo(0, 1.6);
    await UI.lines(S.office.open);
    // the door opens
    NR.audio.fx.door(); const vela = await A.character('vela', L, V3(-1.0, 0, -6.1), 0); G.chars.push(vela);
    lookAt(V3(-1.0, 1.5, -4.6), 1.2);
    for (let k = 0; k <= 30; k++) { L.door.rotation.y = 1.15 * (k / 30) * (2 - k / 30); await wait(0.02); }
    const doorIdx = L.boxes.indexOf(L.doorCol); if (doorIdx >= 0) L.boxes.splice(doorIdx, 1);
    G.lookTarget = () => V3(vela.pos.x, 1.55, vela.pos.z);
    await UI.lines(S.office.enter);
    await vela.walkTo([V3(-1.0, 0, -4.2), V3(-1.5, 0, -2.4), V3(-1.5, 0, -0.65)], 1.0); // her mark: beside the desk, ~2 m from Harrow
    vela.faceTo(P.pos);
    G.beat = 'office_talk';
    await UI.lines(S.office.talk);
    // she lights his cigarette: the SMOKE tutorial
    // the lighting beat: frame her face, the flame between them
    G.beat = 'office_light'; G.lookTarget = () => V3(vela.pos.x, 1.5, vela.pos.z); G.lookRate = 3;
    const toP = V3(P.pos.x - vela.pos.x, 0, P.pos.z - vela.pos.z).normalize();
    const flame = NR.world.glow(0xffd080, 0.3, vela.pos.x + toP.x * 0.55, 1.52, vela.pos.z + toP.z * 0.55, L.scene, 1); flame.material.depthTest = false;
    const flameLight = new THREE.PointLight(0xffa040, 0, 3, 1.6); flameLight.position.copy(flame.position); L.scene.add(flameLight);
    await wait(0.6); NR.audio.fx.lighter(); core.flash(0xffa040, 0.4, 0.25); P.forceCig = true; P.pack += 1;
    for (let k = 0; k < 60; k++) { const f = 0.8 + Math.random() * 0.4; flame.scale.setScalar(0.22 * f + 0.08); flameLight.intensity = 6 * f; await wait(0.03); }
    L.scene.remove(flame); L.scene.remove(flameLight);
    G.beat = 'office_smoke'; G.lookTarget = null; G.lockMove = true; setState('PLAY');
    objective(core.isTouch || NR.controls.lastDevice === 'touch' ? 'Tap SMOKE. Take a drag.' : 'Press Q to SMOKE. Take a drag.');
    await waitFor(() => P.smoked >= 1); P.forceCig = false; objective('');
    await wait(1.2); setState('CUTSCENE'); G.lookTarget = () => V3(vela.pos.x, 1.55, vela.pos.z);
    await UI.lines(S.office.light); await UI.tutorial(S.office.smokeTut);
    await UI.lines(S.office.after);
    G.beat = 'office_leave';
    vela.walkTo([V3(-1.5, 0, -2.4), V3(-1.0, 0, -4.2), V3(-1.0, 0, -6.2)], 1.1).then(() => { vela.visible = false; });
    await UI.lines(S.office.leave); await waitFor(() => !vela.path);
    G.lookTarget = null; G.lockMove = false;
    // take the revolver, go
    let took = false;
    interact({ pos: V3(-0.12, 0.8, -0.35), r: 1.5, label: 'TAKE GUN', enabled: () => !took, use: async () => { took = true; L.deskGun.visible = false; P.armed = true; P.rounds = C.GUN_ROUNDS; NR.audio.fx.reload(); setState('CUTSCENE'); await UI.tutorial(S.office.gunTut); setState('PLAY'); objective('Miles is waiting. Go out the door.'); } });
    setState('PLAY'); G.beat = 'office_play'; objective('Take your revolver from the desk.');
    await waitFor(() => took && P.pos.z < -4.75);
    objective(''); setState('CUTSCENE'); await core.fadeTo(1, 0.8);
  }

  // ================================================================ BEAT 2: the alley
  async function alley() {
    G.beat = 'alley'; await UI.card(S.alley.card, 2.4);
    const L = load('alley'); P.armed = true; P.lives = C.LIVES; P.reset(); P.place(L.spawn.pos, 0, 0);
    setState('CUTSCENE'); lookAt(V3(0, 1.4, -20), 2); core.fadeTo(0, 1.2);
    A.corpse(L, L.bodyPos, 0.4); NR.fx.pool(L.bodyPos.clone().add(V3(0.1, 0, -0.5)), 'human'); NR.fx.pool(L.bodyPos.clone().add(V3(-0.2, 0, 0.2)), 'human');
    await UI.lines(S.alley.open); G.lookTarget = null;
    const spawnFn = () => [
      A.spawn(L, { type: 'thug', pos: V3(-2.4, 0, -13.6), yaw: 0, dormant: true, entry: [V3(-1.6, 0, -11)], drops: 0.5 }),
      A.spawn(L, { type: 'thug', pos: V3(2.9, 0, -17.0), yaw: -Math.PI / 2, dormant: true, flashlight: true, entry: [V3(2.0, 0, -16.2)], drops: 0.5 }),
      A.spawn(L, { type: 'gunman', style: 'thugGun', pos: V3(-0.9, 0, -30.8), yaw: 0, accuracy: 0.75, dmg: 10, drops: 1 }),
    ];
    startFight(spawnFn, { pos: L.spawn.pos, yaw: 0 });
    setState('PLAY'); G.beat = 'alley_play'; objective('Find Miles. The end of the alley.');
    let woke = false;
    trigger(() => P.pos.z < -6.5, () => { woke = true; for (const e of A.enemies) e.alert(); UI.toast('HARROW (V.O.)', S.alley.fight[0][1], 4); objective('Put them down.'); G.beat = 'alley_fight'; });
    await waitFor(() => woke && !alive());
    G.fight = null; UI.toast('HARROW (V.O.)', S.alley.clear[0][1], 4); objective('Check on Miles.'); G.beat = 'alley_clear';
    let checked = false;
    interact({ pos: L.bodyPos, r: 2.7, label: 'MILES', use: () => { checked = true; } });
    await waitFor(() => checked);
    setState('CUTSCENE'); lookAt(V3(L.bodyPos.x, 0.3, L.bodyPos.z), 1);
    await UI.lines(S.alley.body); note(S.alley.matchNote);
    await core.fadeTo(1, 0.9);
  }

  // ================================================================ BEAT 3: the Blue Orchid
  async function club() {
    G.beat = 'club'; await UI.card(S.club.card, 2.4);
    const L = load('club'); P.lives = C.LIVES; P.reset(); P.place(L.spawn.pos, 0, 0);
    const dol = new A.Painted('dolores', L, L.doloresPos, Math.atan2(-5.6, 12)); G.chars.push(dol);
    const fightOnly = new URLSearchParams(location.search).get('beat') === 'clubfight'; // dev: straight to the club gunfight
    let res = { verdict: 'ARTIFICIAL', offered: false };
    if (!fightOnly) {
    setState('CUTSCENE'); lookAt(V3(-1.5, 1.6, -19), 2); core.fadeTo(0, 1.2);
    await UI.lines(S.club.open); G.lookTarget = null;
    await UI.tutorial(S.club.scanTut);
    // clues
    const cm = (geo, color, emissive) => new T.Mesh(geo, new T.MeshStandardMaterial({ color, roughness: 0.4, emissive: emissive || 0 }));
    const holder = new T.Group(); const tip = cm(new T.CylinderGeometry(0.006, 0.006, 0.09, 8), 0x101010); tip.rotation.z = Math.PI / 2; holder.add(tip);
    const lip = cm(new T.CylinderGeometry(0.0065, 0.0065, 0.012, 8), 0xc01010, 0x400000); lip.rotation.z = Math.PI / 2; lip.position.x = 0.045; holder.add(lip);
    const tray = cm(new T.CylinderGeometry(0.07, 0.06, 0.02, 14), 0x6d6a60); tray.position.y = -0.012; holder.add(tray);
    addClue('holder', V3(6.6, 0.82, -13.4), holder);
    const ticket = cm(new T.BoxGeometry(0.16, 0.004, 0.07), 0xe8dcc0); addClue('ticket', V3(7.3, 0.81, -18.4), ticket);
    const shard = cm(new T.BoxGeometry(0.2, 0.004, 0.12), 0x9aa4a8); const milk = cm(new T.CircleGeometry(0.035, 10), 0xeeeadc, 0x3a3a34); milk.rotation.x = -Math.PI / 2; milk.position.y = 0.004; shard.add(milk);
    addClue('mirror', V3(7.45, 0.81, -19.95), shard);
    // cigarettes on the bar
    let tookPack = false; const pack = cm(new T.BoxGeometry(0.06, 0.02, 0.09), 0xe8e2d4); pack.position.set(-5.2, 1.18, -7.5); L.scene.add(pack);
    interact({ pos: V3(-5.0, 1.1, -7.5), r: 1.7, label: 'TAKE SMOKES', enabled: () => !tookPack, use: () => { tookPack = true; pack.visible = false; P.pack = Math.min(C.PACK_MAX, P.pack + 2); UI.toast('+2 SMOKES', 'Somebody left them on the bar. Somebody always does.', 2.5); } });
    setState('PLAY'); G.beat = 'club_scan';
    objective(() => foundCount() < 3 ? 'SCAN the club for clues (' + foundCount() + '/3)' : 'Talk to Dolores, by the dressing room.');
    let talked = false;
    interact({ pos: L.doloresPos, r: 2.2, label: 'TALK', enabled: () => !talked, use: async () => {
      if (foundCount() < 3) { setState('CUTSCENE'); await UI.lines(S.club.notYet); setState('PLAY'); return; }
      talked = true;
    } });
    await waitFor(() => talked);
    G.beat = 'club_meet'; setState('CUTSCENE'); G.lookTarget = () => V3(dol.pos.x, 1.6, dol.pos.z); dol.faceTo(P.pos);
    await UI.lines(S.club.meet); await UI.tutorial(S.club.interroTut);
    G.beat = 'interrogation'; setState('INTERRO'); NR.audio.duck(0.45);
    const found = {}; for (const k in G.caseData.clues) found[k] = true;
    res = await UI.interrogate('dolores', S.dolores, found);
    NR.audio.duck(1);
    G.caseData.verdicts.dolores = res.verdict; if (res.offered) note(S.dolores.offer.note); save();
    UI.toast('CASE FILE', 'Verdict on Dolores Delacroix: ' + res.verdict, 3);
    G.beat = 'verdict'; setState('CUTSCENE');
    await UI.lines(S.club.afterVerdict[res.verdict]); await UI.lines(S.club.warn);
    dol.walkTo([V3(6.4, 0, -17.6), V3(7.0, 0, -22.4)], 1.4).then(() => { dol.visible = false; });
    } else { dol.visible = false; P.place(V3(5.6, 0, -14.4), 0.9, 0); core.fadeTo(0, 0.4); }
    // Gale's men come in through the front and the kitchen
    const spawnFn = () => [
      A.spawn(L, { type: 'gunman', pos: V3(-0.4, 0, 0.6), dormant: true, entry: [V3(-0.6, 0, -1.8)], drops: 0.5 }),
      A.spawn(L, { type: 'gunman', pos: V3(0.5, 0, 0.6), dormant: true, entry: [V3(1.0, 0, -2.4)], drops: 0.5 }),
      A.spawn(L, { type: 'gunman', pos: V3(0.0, 0, 0.6), dormant: true, entry: [V3(0.2, 0, -3.0)], accuracy: 0.9 }),
      A.spawn(L, { type: 'gunman', kind: 'artificial', pos: V3(-7.7, 0, -16.0), dormant: true, entry: [V3(-6.4, 0, -16.0)], hp: 140, drops: 1 }),
      A.spawn(L, { type: 'gunman', pos: V3(-7.7, 0, -15.6), dormant: true, entry: [V3(-6.6, 0, -14.8)], drops: 0.5 }),
    ];
    NR.audio.fx.thump(); core.shake(0.02, 0.3);
    const fight = startFight(spawnFn, { pos: V3(5.6, 0, -14.4), yaw: 0.9 });
    for (const e of fight.enemies) e.alert();
    G.lookTarget = null; setState('PLAY'); G.beat = 'club_fight'; objective('Gale\'s men. Stay alive.');
    await wait(0.5); await waitFor(() => !alive());
    G.fight = null; G.beat = 'club_clear'; objective(''); await wait(3.2);
    setState('CUTSCENE'); await UI.lines(S.club.clear);
    await core.fadeTo(1, 1.0);
  }

  async function run() {
    await UI.gate();
    NR.audio.playMusic(NR.MUSIC.title);
    G.beat = 'title'; await UI.title();
    G.t0 = performance.now(); G.titleCam = false;
    await core.fadeTo(1, 0.6);
    const skip = new URLSearchParams(location.search).get('beat'); // dev: ?beat=alley or ?beat=club
    const toClub = skip === 'club' || skip === 'clubfight';
    if (skip !== 'alley' && !toClub) await office();
    P.armed = true; if (!toClub) await alley();
    await club();
    G.beat = 'end';
    const secs = Math.round((performance.now() - G.t0) / 1000);
    setState('END'); core.fadeTo(0.55, 0.8);
    UI.endCard({ clues: foundCount(), thinks: Object.values(G.caseData.clues).filter(c => c.think).length, verdict: G.caseData.verdicts.dolores, acc: P.shots ? Math.round(P.hits / P.shots * 100) : 0, heads: P.heads, pack: P.pack, time: Math.floor(secs / 60) + ':' + String(secs % 60).padStart(2, '0') });
  }

  // ---------------------------------------------------------------- per-frame
  const noInput = { mx: 0, my: 0, lookX: 0, lookY: 0, fire: false, reload: false, scan: false, smoke: false, interact: false };
  G.update = (dt, rdt) => {
    NR.controls.update();
    const st = core.state, inp = NR.controls.state;
    if (inp.pause && st === 'PLAY') G.pause(true); else if (inp.pause && st === 'PAUSE') G.pause(false);
    if (inp.caseFile) { if (st === 'PLAY' || st === 'PAUSE') G.openCase(); else if (st === 'CASE') G.closeCase(); }
    for (let i = G.waits.length - 1; i >= 0; i--) { let ok = false; try { ok = G.waits[i].cond(); } catch (e) { console.error(e); } if (ok) { const w = G.waits[i]; G.waits.splice(i, 1); w.r(); } }
    const frozen = st === 'PAUSE' || st === 'CASE' || st === 'INTERRO' || st === 'END';
    if (G.titleCam) { const cam = core.camera, t = core.time; cam.position.set(-0.35 + Math.sin(t * 0.1) * 0.12, 1.35, 1.1); cam.rotation.set(0.06 + Math.sin(t * 0.13) * 0.015, -0.12 + Math.sin(t * 0.08) * 0.06, 0); P.controlled = true; }
    else P.controlled = false;
    if (!frozen) {
      if (G.lookTarget && st !== 'PLAY') { const p = typeof G.lookTarget === 'function' ? G.lookTarget() : G.lookTarget; const [y, pt] = yawPitchTo(p); let dy = y - P.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); const k = Math.min(1, rdt * (G.lookRate || 4)); P.yaw += dy * k; P.pitch += (pt - P.pitch) * k; }
      let input = st === 'PLAY' ? inp : noInput;
      if (G.lockMove && st === 'PLAY') input = Object.assign({}, inp, { mx: 0, my: 0, fire: false, scan: false });
      P.update(dt, rdt, input);
      if (G.level) G.level.update(dt, core.time);
      for (const c of G.chars) c.update(dt, core.camera);
      if (st === 'PLAY' || st === 'DOWN') for (const e of A.enemies) e.update(dt, P);
      else for (const e of A.enemies) if (e.dead) e.update(dt, P);
      NR.fx.update(dt, rdt);
      if (st === 'PLAY') {
        updateScan(rdt);
        const it = updateInteract(); if (it && inp.interact) it.use();
        for (let i = G.triggers.length - 1; i >= 0; i--) if (G.triggers[i].test(P)) { const tr = G.triggers[i]; G.triggers.splice(i, 1); tr.fn(); }
      } else { NR.controls.setInteract(null); UI.prompt(''); G.scanProgress = 0; }
    }
    UI.update(rdt);
  };

  // ---------------------------------------------------------------- boot
  function boot() {
    UI.init(core); NR.controls.init(core); NR.audio.init();
    load('office'); G.titleCam = true; setState('TITLE');
    for (const who of ['vela', 'dolores']) A.preload(who);
    if (core.settings.chars === '3d') A.loadGLB(NR.ASSET + A.MODELS.vela).catch(() => {});
    core.startLoop();
    window.READY = true;
    run().catch(e => console.error('[NR.game.run]', e));
  }
  boot();
})();
