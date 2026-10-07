// NEON RAIN controls: portrait twin-stick touch layout (floating move stick, right-thumb look drag, FIRE above the stick,
// RELOAD / SMOKE / SCAN / INTERACT on the right), plus WASD + mouse. Output: NR.controls.state, read once per frame.
(function () {
  const C = NR.cfg, clamp = NR.clamp, DEAD = 0.1;
  const state = { mx: 0, my: 0, lookX: 0, lookY: 0, fire: false, reload: false, scan: false, smoke: false, interact: false, caseFile: false, pause: false, any: false };
  const pend = { reload: false, smoke: false, interact: false, caseFile: false, pause: false, any: false, lookX: 0, lookY: 0 };
  let root = null, el = {}, shown = false, lastDevice = 'none', core = null;
  const L = { k: 1, R: 56, sx: 0, sy: 0, fx: 0, fy: 0, fr: 44, bx: 0, rr: 30, ry: 0, sy2: 0, cy: 0, iy: 0, ir: 36, w: 390, h: 844, top: 90 };
  function layout() {
    const v = core && core.view; if (!v) return; const w = v.w, h = v.h, k = clamp(w / 390, 0.8, 1.5), sb = safeBottom();
    Object.assign(L, { k, w, h, R: Math.round(56 * k), fr: Math.round(44 * k), rr: Math.round(31 * k), ir: Math.round(36 * k), top: Math.round(h * 0.11) });
    L.sx = Math.round(30 * k) + L.R; L.sy = h - Math.round(36 * k) - sb - L.R;
    L.fx = L.sx + Math.round(14 * k); L.fy = L.sy - L.R - Math.round(30 * k) - L.fr;
    L.bx = w - Math.round(18 * k) - L.rr; L.ry = h - Math.round(30 * k) - sb - L.rr;
    L.smy = L.ry - Math.round(74 * k); L.scy = L.smy - Math.round(74 * k); L.iy = L.scy - Math.round(70 * k) - L.ir;
    L.ix = w - Math.round(18 * k) - L.ir;
    if (!root) return;
    place(el.fire, L.fx, L.fy, L.fr); place(el.reload, L.bx, L.ry, L.rr); place(el.smoke, L.bx, L.smy, L.rr); place(el.scan, L.bx, L.scy, L.rr); place(el.interact, L.ix, L.iy, L.ir);
    el.base.style.width = el.base.style.height = L.R * 2 + 'px'; el.knob.style.width = el.knob.style.height = Math.round(52 * k) + 'px';
    root.style.fontSize = Math.round(11 * k) + 'px';
    if (stick.id === null) stickHome();
  }
  function place(e, cx, cy, r) { const s = e.style; s.left = (cx - r) + 'px'; s.top = (cy - r) + 'px'; s.width = s.height = r * 2 + 'px'; }
  function safeBottom() { try { const p = document.createElement('div'); p.style.cssText = 'position:fixed;bottom:0;height:env(safe-area-inset-bottom,0px);visibility:hidden'; document.body.appendChild(p); const v = p.offsetHeight || 0; p.remove(); return Math.min(34, v); } catch (e) { return 0; } }

  const CSS = `
#nrc{position:absolute;inset:0;pointer-events:none;z-index:5;display:none;font-family:"Courier New",monospace;font-weight:bold;letter-spacing:1px;user-select:none;-webkit-user-select:none}
#nrc.on{display:block}
#nrc .base{position:absolute;left:0;top:0;border-radius:50%;box-sizing:border-box;border:2px solid rgba(220,210,190,.35);background:radial-gradient(circle,rgba(0,0,0,.05) 0 55%,rgba(40,36,30,.32) 56%);opacity:.55}
#nrc .base.act{opacity:1;border-color:rgba(232,200,144,.8)}
#nrc .knob{position:absolute;left:0;top:0;border-radius:50%;box-sizing:border-box;border:2px solid rgba(232,200,144,.7);background:radial-gradient(circle at 40% 35%,rgba(232,200,144,.35),rgba(30,26,22,.6) 70%);opacity:.6}
#nrc .knob.act{opacity:1}
#nrc .btn{position:absolute;border-radius:50%;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#eadfca;border:2px solid rgba(234,223,202,.55);background:rgba(10,9,8,.42);text-shadow:0 1px 2px #000;transition:transform .06s;line-height:1.05}
#nrc .btn i{font-style:normal;font-size:1.5em}
#nrc .btn.dn{transform:scale(.92);background:rgba(234,223,202,.25)}
#nrc .fire{border:3px solid #b8241c;color:#ffd8cc;background:radial-gradient(circle,rgba(160,20,14,.45) 0 60%,rgba(10,6,6,.5) 61%);box-shadow:0 0 14px rgba(184,36,28,.55);font-size:1.15em}
#nrc .fire.dn{background:radial-gradient(circle,rgba(220,40,24,.75) 0 60%,rgba(40,6,6,.6) 61%)}
#nrc .scan.on{border-color:#e8b040;color:#ffe2a0;box-shadow:0 0 14px rgba(232,176,64,.8)}
#nrc .smoke b{font-size:.8em;color:#c8b898}
#nrc .interact{border-color:#e8c890;color:#fff1d6;box-shadow:0 0 14px rgba(232,200,144,.55);display:none;font-size:.95em}
#nrc .interact.show{display:flex;animation:nrcPulse 1.2s infinite}
#nrc .fire.empty{opacity:.55}
@keyframes nrcPulse{50%{box-shadow:0 0 22px rgba(232,200,144,.95)}}`;
  function build() {
    const ui = document.getElementById('ui'); const s = document.createElement('style'); s.textContent = CSS; document.head.appendChild(s);
    root = document.createElement('div'); root.id = 'nrc';
    root.innerHTML = '<div class="base"></div><div class="knob"></div><div class="btn fire"><span>FIRE</span></div><div class="btn reload"><i>&#x21bb;</i><span>RELOAD</span></div>' +
      '<div class="btn smoke"><span>SMOKE</span><b>6</b></div><div class="btn scan"><i>&#x25ce;</i><span>SCAN</span></div><div class="btn interact"><span>TALK</span></div>';
    ui.appendChild(root);
    for (const n of ['base', 'knob', 'fire', 'reload', 'smoke', 'scan', 'interact']) el[n] = root.querySelector('.' + n);
    el.smokeN = el.smoke.querySelector('b'); el.interLabel = el.interact.querySelector('span');
  }

  // ---- touch ----
  const stick = { id: null, bx: 0, by: 0, x: 0, y: 0, mx: 0, my: 0 };
  function stickHome() { stick.bx = stick.x = L.sx; stick.by = stick.y = L.sy; stick.mx = stick.my = 0; }
  function stickCalc() {
    let dx = stick.x - stick.bx, dy = stick.y - stick.by, len = Math.hypot(dx, dy); const lim = L.R * 1.1;
    if (len > lim) { const f = (len - lim) / len; stick.bx += dx * f; stick.by += dy * f; dx = stick.x - stick.bx; dy = stick.y - stick.by; len = Math.hypot(dx, dy); }
    const raw = Math.min(1, len / L.R), m = raw < DEAD ? 0 : (raw - DEAD) / (1 - DEAD);
    stick.mx = len > 0 ? dx / len * m : 0; stick.my = len > 0 ? -dy / len * m : 0;
  }
  const owner = new Map(); const look = new Map(); let fireTouches = 0, scanTouches = 0;
  const inPlay = () => core && core.state === 'PLAY';
  const isTarget = t => t && t.closest && t.closest('button,a,input,select,label,[data-tap]');
  const local = t => { const v = core.view; return [t.clientX - v.left, t.clientY - v.top]; };
  const near = (x, y, cx, cy, r) => Math.hypot(x - cx, y - cy) < r;
  function onStart(e) {
    lastDevice = 'touch'; pend.any = true; if (!inPlay()) return;
    for (const t of e.changedTouches) {
      if (isTarget(t.target)) continue;
      const [x, y] = local(t); let k = null;
      if (near(x, y, L.fx, L.fy, L.fr * 1.25)) { k = 'fire'; fireTouches++; }
      else if (near(x, y, L.bx, L.ry, L.rr * 1.2)) { k = 'reload'; pend.reload = true; }
      else if (near(x, y, L.bx, L.smy, L.rr * 1.2)) { k = 'smoke'; pend.smoke = true; }
      else if (near(x, y, L.bx, L.scy, L.rr * 1.2)) { k = 'scan'; scanTouches++; }
      else if (el.interact.classList.contains('show') && near(x, y, L.ix, L.iy, L.ir * 1.25)) { k = 'interact'; pend.interact = true; }
      else if (x < L.w * 0.5 && y > L.h * 0.5 && stick.id === null) { k = 'stick'; stick.id = t.identifier; stick.bx = clamp(x, L.R, L.w * 0.5 - L.R * 0.4); stick.by = clamp(y, L.h * 0.5 + L.R * 0.5, L.h - L.R * 0.8); stick.x = x; stick.y = y; stickCalc(); }
      else if (y > L.top) { k = 'look'; look.set(t.identifier, [x, y]); }
      if (k) { owner.set(t.identifier, k); if (el[k]) el[k].classList.add('dn'); }
    }
    if (e.cancelable) e.preventDefault();
  }
  function onMove(e) {
    for (const t of e.changedTouches) {
      const k = owner.get(t.identifier); if (!k) continue;
      const [x, y] = local(t);
      if (k === 'stick') { stick.x = x; stick.y = y; stickCalc(); }
      else if (k === 'look' || k === 'fire') { // FIRE can be dragged to aim too
        const p = look.get(t.identifier) || [x, y]; const s = C.LOOK_TOUCH * (core.settings.sens || 1);
        pend.lookX += (x - p[0]) * s; pend.lookY += (y - p[1]) * s; look.set(t.identifier, [x, y]);
      }
    }
    if (e.cancelable) e.preventDefault();
  }
  function onEnd(e) {
    for (const t of e.changedTouches) {
      const k = owner.get(t.identifier); if (!k) continue; owner.delete(t.identifier); look.delete(t.identifier);
      if (k === 'stick') { stick.id = null; stickHome(); }
      if (k === 'fire') fireTouches = Math.max(0, fireTouches - 1);
      if (k === 'scan') scanTouches = Math.max(0, scanTouches - 1);
      if (el[k] && ![...owner.values()].includes(k)) el[k].classList.remove('dn');
    }
  }
  function release() { owner.clear(); look.clear(); fireTouches = scanTouches = 0; stick.id = null; stickHome(); if (root) root.querySelectorAll('.dn').forEach(x => x.classList.remove('dn')); }

  // ---- keyboard + mouse ----
  const keys = new Set(); let mouseFire = false, locked = false;
  const GAME = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyR', 'KeyF', 'KeyQ', 'KeyE', 'Tab', 'KeyC', 'Space']);
  function onKey(e) {
    lastDevice = 'keys'; if (GAME.has(e.code) && inPlay()) e.preventDefault(); if (e.repeat) return; keys.add(e.code); pend.any = true;
    if (!inPlay()) return;
    if (e.code === 'KeyR') pend.reload = true; else if (e.code === 'KeyQ') pend.smoke = true; else if (e.code === 'KeyE') pend.interact = true;
    else if (e.code === 'Tab' || e.code === 'KeyC') pend.caseFile = true; else if (e.code === 'Escape' || e.code === 'KeyP') pend.pause = true;
  }
  function onMouseMove(e) { if (!inPlay()) return; if (locked || (e.buttons & 2)) { const s = C.LOOK_MOUSE * (core.settings.sens || 1); pend.lookX += e.movementX * s; pend.lookY += e.movementY * s; } }
  function onMouseDown(e) {
    if (e.target && isTarget(e.target)) return; pend.any = true;
    if (!inPlay() || lastDevice === 'touch' && e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) return;
    if (e.pointerType === 'touch') return;
    lastDevice = 'mouse';
    if (!locked && e.button === 0 && !core.isTouch) { try { const p = document.getElementById('game').requestPointerLock(); if (p && p.catch) p.catch(() => {}); } catch (err) {} }
    if (e.button === 0) mouseFire = true;
  }
  document.addEventListener('pointerlockchange', () => { locked = !!document.pointerLockElement; if (!locked && inPlay() && lastDevice === 'mouse') pend.pause = true; });

  function init(c) {
    core = c; build();
    const o = { passive: false };
    addEventListener('touchstart', onStart, o); addEventListener('touchmove', onMove, o); addEventListener('touchend', onEnd, o); addEventListener('touchcancel', onEnd, o);
    addEventListener('keydown', onKey, true); addEventListener('keyup', e => keys.delete(e.code), true);
    addEventListener('mousemove', onMouseMove); addEventListener('mousedown', onMouseDown); addEventListener('mouseup', e => { if (e.button === 0) mouseFire = false; });
    addEventListener('contextmenu', e => e.preventDefault());
    addEventListener('blur', () => { keys.clear(); release(); mouseFire = false; });
    document.addEventListener('visibilitychange', () => { if (document.hidden) { keys.clear(); release(); if (inPlay()) pend.pause = true; } });
    NR.bus.on('resize', layout); NR.bus.on('state', () => { release(); mouseFire = false; });
    layout();
  }
  function exitLock() { if (document.pointerLockElement) try { document.exitPointerLock(); } catch (e) {} }
  const kd = (a, b) => keys.has(a) || keys.has(b);
  function update() {
    const play = inPlay();
    const showTouch = play && (core.isTouch || lastDevice === 'touch');
    if (showTouch !== shown && root) { shown = showTouch; root.classList.toggle('on', shown); if (shown) layout(); }
    if (play) {
      const kx = (kd('KeyD', 'ArrowRight') ? 1 : 0) - (kd('KeyA', 'ArrowLeft') ? 1 : 0), ky = (kd('KeyW', 'ArrowUp') ? 1 : 0) - (kd('KeyS', 'ArrowDown') ? 1 : 0);
      state.mx = clamp(stick.mx + kx, -1, 1); state.my = clamp(stick.my + ky, -1, 1);
      state.lookX = pend.lookX; state.lookY = pend.lookY;
      state.fire = fireTouches > 0 || mouseFire; state.scan = scanTouches > 0 || keys.has('KeyF');
    } else { state.mx = state.my = state.lookX = state.lookY = 0; state.fire = state.scan = false; }
    pend.lookX = pend.lookY = 0;
    state.reload = play && pend.reload; state.smoke = play && pend.smoke; state.interact = play && pend.interact; state.caseFile = pend.caseFile; state.pause = pend.pause; state.any = pend.any;
    pend.reload = pend.smoke = pend.interact = pend.caseFile = pend.pause = pend.any = false;
    if (NR.controls.inject && play) { const j = NR.controls.inject; for (const k in j) { if (k === 'lookX' || k === 'lookY') state[k] += j[k]; else state[k] = state[k] || j[k]; } j.lookX = j.lookY = 0; j.reload = j.smoke = j.interact = false; } // test autopilot
    if (shown) draw();
  }
  let vKnob = '', vBase = '';
  function draw() {
    const act = stick.id !== null; el.base.classList.toggle('act', act); el.knob.classList.toggle('act', act);
    const b = 'translate3d(' + (stick.bx - L.R) + 'px,' + (stick.by - L.R) + 'px,0)'; if (b !== vBase) { vBase = b; el.base.style.transform = b; }
    let kx = stick.bx, ky = stick.by; if (act) { const dx = stick.x - stick.bx, dy = stick.y - stick.by, l = Math.hypot(dx, dy), m = Math.min(l, L.R); if (l > 0) { kx += dx / l * m; ky += dy / l * m; } }
    const kr = Math.round(26 * L.k), kn = 'translate3d(' + Math.round(kx - kr) + 'px,' + Math.round(ky - kr) + 'px,0)'; if (kn !== vKnob) { vKnob = kn; el.knob.style.transform = kn; }
    const P = NR.player; el.smokeN.textContent = P.pack; el.scan.classList.toggle('on', state.scan); el.fire.classList.toggle('empty', P.rounds === 0);
    el.fire.style.display = el.reload.style.display = P.armed ? 'flex' : 'none';
  }
  function setInteract(label) { if (!root) return; const on = !!label; el.interact.classList.toggle('show', on); if (on && el.interLabel.textContent !== label) el.interLabel.textContent = label; }
  NR.controls = { state, init, update, layout, setInteract, exitLock, release, get lastDevice() { return lastDevice; }, get touchLayout() { return L; }, get root() { return root; } };
})();
