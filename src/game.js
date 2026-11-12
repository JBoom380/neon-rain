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
    if (NR.audio.unlocked) NR.audio.ambience(NR.RAIN[name] || []); // no audio work before TAP TO ENTER (AudioContext setup stalls the first frames)
    return L;
  }
  G.load = load;
  function yawPitchTo(p) { const e = P.eye(), dx = p.x - e.x, dy = p.y - e.y, dz = p.z - e.z; return [Math.atan2(-dx, -dz), Math.atan2(dy, Math.hypot(dx, dz))]; }
  function lookAt(p, secs) { G.lookTarget = p; G.lookRate = secs ? 3 / secs : 4; }
  function setState(s) { if (s === 'CUTSCENE' && NR.player.holster) NR.player.holster(); core.setState(s); UI.letterbox(s === 'CUTSCENE'); }
  // a V.O. line over play: the toast stays for the length of the take, the score ducks under it
  function voToast(line) { UI.toast(line[0], line[1], 4); NR.audio.speak(line[1]).then(v => { if (!v) return; UI.toast(line[0], line[1], v.dur + 0.6); NR.audio.duck(0.3); v.done.then(() => { if (!NR.audio.voiceOn) NR.audio.duck(1); }); }); }
  // enemy barks: generated takes, one at a time, never over a story line
  const BARKS = { alley: ['Go left! Flank him!', 'Cut him off!', 'He is alone! Rush him!'], club: ['Behind the booth! Flush him out!', 'Keep him pinned!', 'He is reloading! Move!'] };
  function bark(text, who) { if (NR.audio.voiceOn) return; NR.audio.speak(text).then(v => { if (v && who) UI.toast(who, text, v.dur + 0.4); }); }
  async function scene(lines) { setState('CUTSCENE'); await UI.lines(lines); }

  // ---------------------------------------------------------------- interactables, clues, triggers
  function interact(o) { G.interacts.push(Object.assign({ r: 1.6, enabled: () => true }, o)); return o; }
  function trigger(test, fn) { G.triggers.push({ test, fn }); }
  function addClue(id, pos, mesh) {
    // the scan mark is a thin amber ring around the clue, not a soft disc over it
    if (!G.ringTex) G.ringTex = NR.world.tex(128, 128, (g, w, h) => { g.clearRect(0, 0, w, h); g.strokeStyle = '#fff'; g.lineWidth = 5; g.beginPath(); g.arc(64, 64, 54, 0, 7); g.stroke(); g.lineWidth = 2; g.globalAlpha = 0.5; g.beginPath(); g.arc(64, 64, 46, 0, 7); g.stroke(); });
    const glow = new T.Sprite(new T.SpriteMaterial({ map: G.ringTex, color: 0xffb040, transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false, depthTest: false })); glow.position.copy(pos); glow.renderOrder = 9; G.level.scene.add(glow);
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
      c.glow.scale.setScalar(NR.clamp(dist * 0.2, 0.3, 0.55) + Math.sin(t * 4 + c.pos.x) * 0.012);
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
  NR.bus.on('magPickup', d => UI.toast('+1 MAGAZINE', 'Off his belt. Magazines: ' + d.mags, 1.8));
  NR.bus.on('noMags', () => UI.toast('NO MAGAZINES', 'Take one off a man you dropped.', 2));
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
    G.beat = 'office'; NR.audio.preVoice('office'); NR.audio.cue('01'); const L = load('office'); P.armed = false; P.hideGun = false; P.lives = C.LIVES;
    P.place(L.spawn.pos, 0.35, 0.05); setState('CUTSCENE'); core.fx.fade = 1;
    await UI.card(S.office.card, 2.4);
    lookAt(V3(0.85, 1.8, -4.6), 5); core.fadeTo(0, 1.6); NR.audio.cue('02');
    await UI.lines(S.office.open);
    // the door opens
    NR.audio.fx.door(); NR.audio.cue('03'); const vela = await A.character('vela', L, V3(-1.0, 0, -6.1), 0); G.chars.push(vela);
    // Vela comes in as a backlit silhouette: no key or ambient light, a thin rim from the hall; the desk beat lights her again
    const velaLight = (on) => { const u = vela.mat && vela.mat.uniforms, pf = vela.perf && vela.perf.u; if (!u) return;
      if (on) { if (!vela.litSaved) vela.litSaved = { a: u.ambient.value.clone(), k: u.key.value.clone(), w: u.warm.value.clone(), g: u.keyGain.value, c: u.rimCol.value.clone() };
        u.ambient.value.setRGB(0, 0, 0); u.key.value.setRGB(0, 0, 0); u.warm.value.setRGB(0, 0, 0); u.keyGain.value = 0; u.rimCol.value.setRGB(0.72, 0.88, 1.0); vela.silh = { rim: 2.4 };
        if (pf) { pf.rimK.value = 2.2; pf.rimC.value.setRGB(0.72, 0.88, 1.0); } }
      else if (vela.litSaved) { const s = vela.litSaved; u.ambient.value.copy(s.a); u.key.value.copy(s.k); u.warm.value.copy(s.w); u.keyGain.value = s.g; u.rimCol.value.copy(s.c); vela.silh = null;
        if (pf) { pf.rimK.value = 0; pf.rimC.value.set(0xffe2b0); } } };
    velaLight(true);
    lookAt(V3(-1.0, 1.5, -4.6), 1.2);
    for (let k = 0; k <= 30; k++) { L.door.rotation.y = 1.15 * (k / 30) * (2 - k / 30); await wait(0.02); }
    velaLight(true);
    const doorIdx = L.boxes.indexOf(L.doorCol); if (doorIdx >= 0) L.boxes.splice(doorIdx, 1);
    G.lookTarget = () => V3(vela.pos.x, 1.55, vela.pos.z);
    await UI.lines(S.office.enter);
    waitFor(() => vela.pos.z > -4.9).then(() => velaLight(false)); // a silhouette in the door for about 1.2 s, then she steps into the room light and her face shows
    await vela.walkTo([V3(-1.0, 0, -4.2), V3(-1.5, 0, -2.4), V3(-1.5, 0, -0.65)], 1.0); // her mark: beside the desk, ~2 m from Harrow
    velaLight(false);
    vela.faceTo(P.pos);
    G.beat = 'office_talk';
    await UI.lines(S.office.talk);
    // she lights his cigarette: the SMOKE tutorial
    // the lighting beat: frame her face, the flame between them
    G.beat = 'office_light'; G.lookTarget = () => V3(vela.pos.x, 1.5, vela.pos.z); G.lookRate = 3;
    const toP = V3(P.pos.x - vela.pos.x, 0, P.pos.z - vela.pos.z).normalize();
    const fd = Math.max(0.6, Math.hypot(P.pos.x - vela.pos.x, P.pos.z - vela.pos.z) - 0.55); const flame = NR.world.glow(0xffd080, 0.3, vela.pos.x + toP.x * fd, 1.3, vela.pos.z + toP.z * fd, L.scene, 1); // the flame is at his cigarette, low between them (at her head height it read as a halo) flame.material.depthTest = false;
    const flameLight = new THREE.PointLight(0xffa040, 0, 3, 1.6); flameLight.position.copy(flame.position); L.scene.add(flameLight);
    await wait(0.6); NR.audio.fx.lighter(); core.flash(0xffa040, 0.4, 0.25); P.forceCig = true; P.pack += 1;
    for (let k = 0; k < 60; k++) { const f = 0.8 + Math.random() * 0.4; flame.scale.setScalar(0.1 * f + 0.04); flameLight.intensity = 6 * f; await wait(0.03); }
    L.scene.remove(flame); L.scene.remove(flameLight);
    G.beat = 'office_smoke'; G.lookTarget = null; G.lockMove = true; setState('PLAY');
    objective(core.isTouch || NR.controls.lastDevice === 'touch' ? 'Tap SMOKE. Take a drag.' : 'Press Q to SMOKE. Take a drag.');
    await waitFor(() => P.smoked >= 1); P.forceCig = false; objective('');
    await wait(1.2); setState('CUTSCENE'); G.lookTarget = () => V3(vela.pos.x, 1.55, vela.pos.z);
    await UI.lines(S.office.light); await UI.tutorial(S.office.smokeTut);
    await UI.lines(S.office.after);
    G.beat = 'office_leave';
    vela.walkTo([V3(-1.5, 0, -2.4), V3(-1.0, 0, -4.2), V3(-1.0, 0, -6.2)], 1.1, { stop: false }).then(() => { vela.visible = false; });
    await UI.lines(S.office.leave); await waitFor(() => !vela.path);
    G.lookTarget = null; G.lockMove = false; NR.audio.cue('02');
    // take the pistol, go
    let took = false;
    interact({ pos: V3(-0.12, 0.8, -0.35), r: 1.5, label: 'TAKE GUN', enabled: () => !took, use: async () => { took = true; L.deskGun.visible = false; P.armed = true; P.rounds = C.GUN_ROUNDS; NR.audio.fx.reload(); setState('CUTSCENE'); await UI.tutorial(S.office.gunTut); setState('PLAY'); objective('GUN draws and holsters. Then go: Miles is waiting.'); } });
    setState('PLAY'); G.beat = 'office_play'; objective('Take your pistol from the desk.');
    await waitFor(() => took && P.pos.z < -4.75);
    objective(''); setState('CUTSCENE'); await core.fadeTo(1, 0.8);
  }

  // ================================================================ BEAT 2: the alley
  async function alley() {
    G.beat = 'alley'; NR.audio.preVoice('alley'); NR.audio.cue('01'); await UI.eye(); await UI.card(S.alley.card, 2.4);
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
    trigger(() => P.pos.z < -6.5, () => { woke = true; for (const e of A.enemies) e.alert(); NR.audio.cue('07'); NR.audio.preVoice('bark_alley'); bark('There he is! Take him!', 'THUG'); setTimeout(() => voToast(S.alley.fight[0]), 1900); objective('Put them down.'); G.beat = 'alley_fight'; });
    await waitFor(() => woke && !alive());
    G.fight = null; NR.audio.cue('02'); voToast(S.alley.clear[0]); objective('Check on Miles.'); G.beat = 'alley_clear';
    let checked = false;
    interact({ pos: L.bodyPos, r: 2.7, label: 'MILES', use: () => { checked = true; } });
    await waitFor(() => checked);
    // the camera cuts to his side, by the head: the face and the fallen hat are in frame (from the feet the chest hides the head)
    setState('CUTSCENE'); await core.fadeTo(1, 0.25); { const cp = V3(L.bodyPos.x + 1.3, 0, L.bodyPos.z - 1.4), tp = V3(L.bodyPos.x, 0.2, L.bodyPos.z - 0.6); P.place(cp, 0, 0); const yp = yawPitchTo(tp); P.place(cp, yp[0], yp[1]); G.lookTarget = tp; G.lookRate = 4; } core.fadeTo(0, 0.5);
    await UI.lines(S.alley.body); note(S.alley.matchNote);
    await core.fadeTo(1, 0.9);
  }

  // ================================================================ BEAT 3: the Blue Orchid
  async function club() {
    G.beat = 'club'; NR.audio.preVoice('club'); NR.audio.preVoice('dol'); NR.audio.cue('01'); await UI.eye(); await UI.card(S.club.card, 2.4);
    const L = load('club'); P.lives = C.LIVES; P.reset(); P.place(L.spawn.pos, 0, 0);
    const dol = new A.Painted('dolores', L, L.doloresPos, Math.atan2(-5.6, 12)); G.chars.push(dol);
    // glamour light: she stands out of the stage spot, so she gets her own soft key and a thin warm rim; she turns to Harrow when he is near
    { const u = dol.mat.uniforms; u.ambient.value.setRGB(0.54, 0.43, 0.36); u.rimGain.value = 0.55; u.rimCol.value.setRGB(1.0, 0.86, 0.66); } G.glam = dol;
    const fightOnly = new URLSearchParams(location.search).get('beat') === 'clubfight'; // dev: straight to the club gunfight
    let res = { verdict: 'ARTIFICIAL', offered: false };
    if (!fightOnly) {
    setState('CUTSCENE'); lookAt(V3(-1.5, 1.6, -19), 2); core.fadeTo(0, 1.2);
    await UI.lines(S.club.open); G.lookTarget = null;
    await UI.tutorial(S.club.scanTut);
    // clues
    const cm = (geo, color, emissive) => new T.Mesh(geo, new T.MeshStandardMaterial({ color, roughness: 0.4, emissive: emissive || 0 }));
    // the holder tip: a black cigarette-holder end with a gold band, propped on the rim of the ashtray, a ring of bright red lipstick on the mouth end
    const holder = new T.Group(); const tray = cm(new T.CylinderGeometry(0.075, 0.062, 0.022, 20), 0x9a968a, 0x34322c); tray.position.y = -0.012; holder.add(tray);
    { const well = new T.Mesh(new T.CylinderGeometry(0.058, 0.058, 0.004, 20), new T.MeshStandardMaterial({ color: 0x4a4640, roughness: 0.9, emissive: 0x16140f })); well.position.y = -0.0005; holder.add(well);
      const tipG = new T.Group(); tipG.position.set(0.02, 0.03, 0.0); tipG.rotation.set(0, 0.6, 0.32); tipG.scale.setScalar(1.7); holder.add(tipG);
      const part = (r0, r1, len, x, col, em) => { const m = new T.Mesh(new T.CylinderGeometry(r0, r1, len, 14), em ? new T.MeshBasicMaterial({ color: em }) : new T.MeshStandardMaterial({ color: col, roughness: 0.35, emissive: 0x141210 })); m.rotation.z = Math.PI / 2; m.position.x = x; tipG.add(m); };
      part(0.0030, 0.0042, 0.11, 0.0, 0x1a1816); part(0.0048, 0.0048, 0.007, -0.047, 0, 0xd8a840); part(0.0022, 0.0030, 0.026, 0.068, 0x1a1816); part(0.0034, 0.0037, 0.013, 0.058, 0, 0xe01224); } // slender and tapered: a holder, not a cigar
    addClue('holder', V3(6.6, 0.82, -13.4), holder);
    const ticket = cm(new T.BoxGeometry(0.16, 0.004, 0.07), 0xe8dcc0); { const tt = NR.world.tex(512, 224, (g, w, h) => { g.fillStyle = '#e6d8b4'; g.fillRect(0, 0, w, h); g.strokeStyle = '#6a2418'; g.lineWidth = 6; g.strokeRect(12, 12, w - 24, h - 24); g.setLineDash([10, 8]); g.lineWidth = 3; g.beginPath(); g.moveTo(w * 0.74, 14); g.lineTo(w * 0.74, h - 14); g.stroke(); g.setLineDash([]); g.fillStyle = '#6a2418'; g.textAlign = 'center'; g.font = 'bold 44px Georgia'; g.fillText('NIGHT FERRY', w * 0.38, 78); g.font = 'bold 30px Courier New'; g.fillStyle = '#1e1a14'; g.fillText('ONE WAY', w * 0.38, 128); g.font = '22px Courier New'; g.fillText('PIER 9  ·  PAID CASH', w * 0.38, 172); g.save(); g.translate(w * 0.87, h / 2); g.rotate(-Math.PI / 2); g.font = 'bold 26px Courier New'; g.fillText('No. 0417', 0, 8); g.restore(); }); const face = new T.Mesh(new T.PlaneGeometry(0.16, 0.07), new T.MeshStandardMaterial({ map: tt, roughness: 0.8 })); face.rotation.x = -Math.PI / 2; face.position.y = 0.0026; ticket.add(face); ticket.rotation.y = 0.35; ticket.scale.setScalar(1.5); } addClue('ticket', V3(7.3, 0.81, -18.4), ticket);
    // the mirror shard: silvered glass (its own cool grey, so the warm room light does not turn it to paper), a bright streak of reflection, sharp dark edges, a crack, a pale milky smear
    const shard = (() => { const pts = [[-0.11, -0.05], [0.02, -0.075], [0.12, -0.01], [0.06, 0.07], [-0.07, 0.045]], sh = new T.Shape(); pts.forEach(([x, y], k) => k ? sh.lineTo(x, y) : sh.moveTo(x, y));
      const gt = NR.world.tex(256, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#06080a'); gr.addColorStop(0.40, '#0c1014'); gr.addColorStop(0.455, '#d8e6f2'); gr.addColorStop(0.49, '#f4fbff'); gr.addColorStop(0.52, '#16202a'); gr.addColorStop(1, '#040506'); g.fillStyle = gr; g.fillRect(0, 0, w, h); g.fillStyle = 'rgba(190,210,225,0.35)'; g.beginPath(); g.moveTo(0, 214); g.lineTo(256, 150); g.lineTo(256, 154); g.lineTo(0, 219); g.fill(); }); // a mirror in a dark room: near-black glass, one sharp streak of light
      const geo = new T.ShapeGeometry(sh); const uv = geo.attributes.uv; for (let k = 0; k < uv.count; k++) uv.setXY(k, (uv.getX(k) + 0.12) / 0.24, (uv.getY(k) + 0.08) / 0.16); geo.rotateX(-Math.PI / 2);
      const m = new T.Group(), glass = new T.Mesh(geo, new T.MeshBasicMaterial({ map: gt })); glass.position.y = 0.0042; m.add(glass);
      const back = new T.Mesh(new T.ExtrudeGeometry(sh, { depth: 0.004, bevelEnabled: false }), new T.MeshBasicMaterial({ color: 0x14181c })); back.geometry.rotateX(-Math.PI / 2); m.add(back);
      const seg = (x0, z0, x1, z1, wd, col) => { const c = new T.Mesh(new T.BoxGeometry(Math.hypot(x1 - x0, z1 - z0), 0.0006, wd), new T.MeshBasicMaterial({ color: col })); c.position.set((x0 + x1) / 2, 0.0048, (z0 + z1) / 2); c.rotation.y = -Math.atan2(z1 - z0, x1 - x0); m.add(c); };
      pts.forEach(([x, y], k) => { const [x2, y2] = pts[(k + 1) % pts.length]; seg(x, -y, x2, -y2, 0.0024, 0xd0d8e0); }); // a thin silver bevel for (const [x0, z0, x1, z1] of [[-0.1, 0.04, 0.03, -0.02], [0.03, -0.02, 0.1, 0.0], [0.03, -0.02, 0.0, -0.06]]) seg(x0, z0, x1, z1, 0.002, 0xc4d0d8);
      m.scale.setScalar(1.4); return m; })(); const milk = new T.Mesh(new T.PlaneGeometry(0.13, 0.075), new T.MeshBasicMaterial({ transparent: true, depthWrite: false, map: NR.world.tex(256, 148, (g, w, h) => { g.clearRect(0, 0, w, h); let sd = 5; const rn = () => (sd = (sd * 16807) % 2147483647) / 2147483647; g.filter = 'blur(5px)'; g.fillStyle = 'rgba(240,238,228,0.55)'; g.beginPath(); g.ellipse(70, 78, 44, 30, -0.2, 0, 7); g.fill(); g.filter = 'blur(2px)'; g.fillStyle = 'rgba(248,246,238,0.95)'; g.beginPath(); g.ellipse(64, 80, 30, 21, -0.25, 0, 7); g.fill(); g.lineCap = 'round'; for (let i = 0; i < 9; i++) { const y0 = 58 + i * 5 + rn() * 3, len = 90 + rn() * 80; g.strokeStyle = `rgba(244,242,232,${0.25 + rn() * 0.45})`; g.lineWidth = 2 + rn() * 5; g.filter = 'blur(' + (1 + rn() * 2).toFixed(1) + 'px)'; g.beginPath(); g.moveTo(70, y0 + 14); g.quadraticCurveTo(70 + len * 0.5, y0 + 4 - rn() * 8, 70 + len, y0 - 10 - rn() * 10); g.stroke(); } g.filter = 'none'; }) })); milk.rotation.x = -Math.PI / 2; milk.position.set(0.012, 0.0056, 0.012); milk.rotation.z = 0.5; shard.add(milk);
    addClue('mirror', V3(7.45, 0.81, -19.95), shard);
    // cigarettes on the bar
    let tookPack = false; const pack = cm(new T.BoxGeometry(0.06, 0.02, 0.09), 0xe8e2d4); pack.position.set(-5.2, 1.18, -7.5); L.scene.add(pack);
    interact({ pos: V3(-5.0, 1.1, -7.5), r: 1.7, label: 'TAKE SMOKES', enabled: () => !tookPack, use: () => { tookPack = true; pack.visible = false; P.pack = Math.min(C.PACK_MAX, P.pack + 2); UI.toast('+2 SMOKES', 'Somebody left them on the bar. Somebody always does.', 2.5); } });
    setState('PLAY'); G.beat = 'club_scan'; NR.audio.cue('04');
    // Dolores's song plays from the stage: 05 near the stage, the house band (04) elsewhere
    G.musicZone = () => { const d = Math.hypot(P.pos.x + 1.5, P.pos.z + 19.5); const near = NR.audio.cueId === '05' ? d < 8.5 : d < 7; NR.audio.cue(near ? '05' : '04'); };
    objective(() => foundCount() < 3 ? 'SCAN the club for clues (' + foundCount() + '/3)' : 'Talk to Dolores, by the dressing room.');
    let talked = false;
    interact({ pos: L.doloresPos, r: 2.2, label: 'TALK', enabled: () => !talked, use: async () => {
      if (foundCount() < 3) { setState('CUTSCENE'); await UI.lines(S.club.notYet); setState('PLAY'); return; }
      talked = true;
    } });
    await waitFor(() => talked);
    G.beat = 'club_meet'; G.musicZone = null; setState('CUTSCENE'); G.lookTarget = () => V3(dol.pos.x, 1.6, dol.pos.z); dol.faceTo(P.pos);
    await UI.lines(S.club.meet); await UI.tutorial(S.club.interroTut);
    G.beat = 'interrogation'; setState('INTERRO'); NR.audio.cue('06');
    const found = {}; for (const k in G.caseData.clues) found[k] = true;
    res = await UI.interrogate('dolores', S.dolores, found);

    G.caseData.verdicts.dolores = res.verdict; if (res.offered) note(S.dolores.offer.note); save();
    UI.toast('CASE FILE', 'Verdict on Dolores Delacroix: ' + res.verdict, 3);
    G.beat = 'verdict'; setState('CUTSCENE');
    await UI.lines(S.club.afterVerdict[res.verdict]); await UI.lines(S.club.warn);
    // she turns to go, then looks back at him over her shoulder (the three-quarter back painting, her face to the lens) before she leaves
    G.glam = null; (async () => { const back = () => { dol.yaw = Math.atan2(P.pos.x - dol.pos.x, P.pos.z - dol.pos.z) + 2.36; }; const t0 = core.time; while (core.time - t0 < 2.6) { back(); await wait(0.05); }
      await dol.walkTo([V3(6.4, 0, -17.6), V3(7.0, 0, -22.4)], 1.4); dol.visible = false; })();
    } else { dol.visible = false; P.place(V3(5.6, 0, -14.4), 0.9, 0); core.fadeTo(0, 0.4); }
    G.musicZone = null;
    // Gale's men come in through the front and the kitchen
    const spawnFn = () => [
      A.spawn(L, { type: 'gunman', pos: V3(-0.4, 0, 0.6), dormant: true, entry: [V3(-0.6, 0, -1.8)], drops: 0.5 }),
      A.spawn(L, { type: 'gunman', pos: V3(0.5, 0, 0.6), dormant: true, entry: [V3(1.0, 0, -2.4)], drops: 0.5 }),
      A.spawn(L, { type: 'gunman', pos: V3(0.0, 0, 0.6), dormant: true, entry: [V3(0.2, 0, -3.0)], accuracy: 0.9 }),
      A.spawn(L, { type: 'gunman', kind: 'artificial', pos: V3(-7.7, 0, -16.0), dormant: true, entry: [V3(-6.4, 0, -16.0)], hp: 140, drops: 1 }),
      A.spawn(L, { type: 'gunman', pos: V3(-7.7, 0, -15.6), dormant: true, entry: [V3(-6.6, 0, -14.8)], drops: 0.5 }),
    ];
    NR.audio.fx.thump(); core.shake(0.02, 0.3); G.musicZone = null; NR.audio.cue('07', 0.8); NR.audio.preVoice('bark_club'); setTimeout(() => bark('Mister Gale says hello, Harrow.', 'GUNMAN'), 700);
    const fight = startFight(spawnFn, { pos: V3(5.6, 0, -14.4), yaw: 0.9 });
    for (const e of fight.enemies) e.alert();
    G.lookTarget = null; setState('PLAY'); G.beat = 'club_fight'; objective('Gale\'s men. Stay alive.');
    await wait(0.5); await waitFor(() => !alive());
    G.fight = null; G.beat = 'club_clear'; objective(''); await wait(2.2);
    // the camera cuts to the artificial man on the floor: a spot 2.1 m from him with a clear line to the body and to the pale pool
    setState('CUTSCENE'); { const art = A.enemies.find(e => e.kind === 'artificial');
      if (art) { await core.fadeTo(1, 0.25); const B = art.cr && art.cr.bones, wp = b => b.getWorldPosition(V3(0, 0, 0));
        if (B && B.head) { const hd = wp(B.head), hip = wp(B.hips), ft = wp(B.thighL).lerp(wp(B.thighR), 0.5), ax = V3(hip.x - hd.x, 0, hip.z - hd.z).normalize(); // axis: head -> feet
          const mid = hd.clone().lerp(hip, 0.62); mid.y = 0.15; const pts = [hd, hip, wp(B.thighL), wp(B.thighR), wp(B.spine2), wp(B.handL), wp(B.handR), mid]; for (const q of pts) q.y = Math.max(q.y, 0.12);
          const env = []; L.scene.traverse(o => { if (o.isMesh && (o.name === 'PROPS' || o.name === 'SHELL')) env.push(o); });
          const rc = new T.Raycaster(), sees = (eye, pt) => { const d = pt.clone().sub(eye), len = d.length(); rc.set(eye, d.divideScalar(len)); rc.far = len - 0.12; return !rc.intersectObjects(env, false).length; };
          // an overhead shot from above his feet: the body runs up the tall screen, the head at the top, the face to the lens
          let best = null, bs = -1; for (const back of [0.95, 0.55, 1.35]) for (const tw of [0, 0.35, -0.35, 0.7, -0.7]) for (const hgt of [2.45, 2.1]) { if (bs === pts.length) break;
            const dx = ax.x * Math.cos(tw) - ax.z * Math.sin(tw), dz = ax.x * Math.sin(tw) + ax.z * Math.cos(tw), eye = V3(mid.x + dx * back, hgt, mid.z + dz * back), sc = pts.filter(q => sees(eye, q)).length; if (sc > bs) { bs = sc; best = eye; } }
          if (best && bs >= 6) { const cam = core.camera; G.camFov0 = cam.fov; cam.fov = 46; cam.updateProjectionMatrix(); const tgt = mid.clone().lerp(ft, 0.2); tgt.y = 0.1; G.camOverride = { pos: best, tgt };
            const key = new T.PointLight(0xfff0e2, 10, 7, 1.4); key.position.set(best.x, best.y - 0.2, best.z); L.scene.add(key); G.camKey = key; G.milkCam = bs; } }
        core.fadeTo(0, 0.5); } }
    await UI.lines(S.club.clear); G.lookTarget = null;
    await core.fadeTo(1, 1.0); if (G.camOverride) { G.camOverride = null; core.camera.fov = G.camFov0; core.camera.updateProjectionMatrix(); if (G.camKey) L.scene.remove(G.camKey); }
    await core.fadeTo(1, 1.0);
  }

  async function run() {
    if (NR.JUKEBOX_ONLY) { try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) {} NR.neon.start(); G.beat = 'title'; await UI.title(); return; }
    await UI.gate();
    NR.audio.cue('04'); NR.audio.ambience(NR.RAIN.club); NR.neon.start();
    G.beat = 'title'; await UI.title(); NR.audio.setOnEnded(null); NR.neon.stop();
    G.t0 = performance.now(); G.titleCam = false;
    await core.fadeTo(1, 0.6); await UI.eye(); // signature transition: the city in an eye
    const skip = new URLSearchParams(location.search).get('beat'); // dev: ?beat=alley or ?beat=club
    const toClub = skip === 'club' || skip === 'clubfight';
    if (skip !== 'alley' && !toClub) await office();
    P.armed = true; if (!toClub) await alley();
    await club();
    G.beat = 'end';
    const secs = Math.round((performance.now() - G.t0) / 1000);
    setState('END'); core.fadeTo(0.55, 0.8); NR.audio.cue('09', 1.5, { loop: false });
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
    if (G.titleCam) { const cam = core.camera, t = core.time; cam.position.set(0.6 + Math.sin(t * 0.07) * 0.7, 1.7 + Math.sin(t * 0.11) * 0.06, -9.5 - Math.sin(t * 0.05) * 1.0); cam.rotation.set(0.1 + Math.sin(t * 0.13) * 0.01, 0.2 + Math.sin(t * 0.06) * 0.04, 0); P.controlled = true; if (G.level && G.level.signLight) G.level.signLight.intensity = NR.neon.level * 26; }
    else if (G.camOverride) { core.camera.position.copy(G.camOverride.pos); core.camera.up.set(0, 1, 0); core.camera.lookAt(G.camOverride.tgt); P.controlled = true; }
    else { P.controlled = false; if (levels.club && levels.club.signLight && levels.club.signLight.intensity) levels.club.signLight.intensity = 0; }
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
        if (G.musicZone && core.frame % 15 === 0) G.musicZone();
        if (G.glam && G.glam.visible && !G.glam.path) { const g = G.glam, d = Math.hypot(P.pos.x - g.pos.x, P.pos.z - g.pos.z); if (d < 10) { const ty = Math.atan2(P.pos.x - g.pos.x, P.pos.z - g.pos.z); let dy = ty - g.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); g.yaw += dy * Math.min(1, dt * 2.5); } }
        if (G.fight && true) { G.barkT = (G.barkT == null ? 7 : G.barkT) - dt; if (G.barkT <= 0) { G.barkT = 8 + Math.random() * 6; const pool = BARKS[G.beat.indexOf('alley') === 0 ? 'alley' : 'club']; if (A.enemies.filter(e => !e.dead && e.state !== 'dormant').length >= 1) bark(pool[Math.floor(Math.random() * pool.length)]); } }
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
    load('club'); G.titleCam = true; setState('TITLE'); // landing menu: the Blue Orchid stage, empty mic in the spotlight
    for (const who of ['vela', 'dolores']) A.preload(who);
    if (core.settings.chars === '3d') A.loadGLB(NR.ASSET + A.MODELS.vela).catch(() => {});
    core.startLoop();
    run().catch(e => console.error('[NR.game.run]', e));
    // READY (and TAP TO ENTER) once the landing scene's async models have loaded and every program is compiled,
    // so no shader compile stalls the menu after the tap
    const t0 = performance.now(); let quiet = 0;
    (function settle() {
      const busy = NR.gltf && NR.gltf.pending > 0;
      quiet = busy ? 0 : quiet + 1;
      if (quiet >= 3 || performance.now() - t0 > 12000) {
        try { core.renderer.compile(core.scene, core.camera); if (core.vm) core.renderer.compile(core.vm.scene, core.camera); } catch (e) {}
        requestAnimationFrame(() => requestAnimationFrame(() => { window.READY = true; }));
      } else setTimeout(settle, 150);
    })();
  }
  boot();
})();
