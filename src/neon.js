// NEON RAIN title sign: a 1940s New York neon sign in SVG. Double-line block tube letters (red, white-hot core),
// a white cursive script line, a dark sign box with brackets and bolts, glow spill on the wall behind, a red light
// in the 3D scene that follows the sign's brightness, a startup sequence (tubes light letter by letter with a click),
// an irregular flicker (the A in RAIN sputters and sometimes dies), and a hum. prefers-reduced-motion: steady glow.
(function () {
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // block letter outlines on a 60 x 80 grid (each subpath is one tube run)
  const G = {
    N: { w: 60, p: [[[0, 0], [14, 0], [46, 50], [46, 0], [60, 0], [60, 80], [46, 80], [14, 30], [14, 80], [0, 80]]] },
    E: { w: 54, p: [[[0, 0], [54, 0], [54, 13], [14, 13], [14, 33], [44, 33], [44, 46], [14, 46], [14, 67], [54, 67], [54, 80], [0, 80]]] },
    O: { w: 60, round: true },
    R: { w: 60, p: [[[0, 0], [42, 0], [56, 8], [58, 22], [56, 36], [46, 44], [60, 80], [45, 80], [33, 46], [14, 46], [14, 80], [0, 80]], [[14, 13], [38, 13], [43, 17], [44, 24], [42, 31], [38, 34], [14, 34]]] },
    A: { w: 60, p: [[[22, 0], [38, 0], [60, 80], [45, 80], [40, 62], [20, 62], [15, 80], [0, 80]], [[24, 49], [36, 49], [30, 23]]] },
    I: { w: 16, p: [[[0, 0], [16, 0], [16, 80], [0, 80]]] },
  };
  const S = 0.78, GAP = 10;
  function letterD(ch, x0, y0) {
    const g = G[ch];
    if (g.round) { // O: rounded outer and inner tube
      const rr = (x, y, w, h, r) => `M${x + r},${y}H${x + w - r}A${r},${r} 0 0 1 ${x + w},${y + r}V${y + h - r}A${r},${r} 0 0 1 ${x + w - r},${y + h}H${x + r}A${r},${r} 0 0 1 ${x},${y + h - r}V${y + r}A${r},${r} 0 0 1 ${x + r},${y}Z`;
      return rr(x0, y0, 60 * S, 80 * S, 24 * S) + rr(x0 + 14 * S, y0 + 14 * S, 32 * S, 52 * S, 11 * S);
    }
    return g.p.map(run => 'M' + run.map(([x, y]) => (x0 + x * S).toFixed(1) + ',' + (y0 + y * S).toFixed(1)).join('L') + 'Z').join('');
  }
  function word(w, cy) {
    const width = [...w].reduce((a, c) => a + G[c].w * S, 0) + GAP * (w.length - 1); let x = 170 - width / 2; const out = [];
    for (const c of w) { out.push(letterD(c, x, cy)); x += G[c].w * S + GAP; }
    return out;
  }
  const RED = '#ff3a22', CORE = '#ffe6d6', DARK = '#140c0a';
  function tube(d, id) { // concentric strokes: glow, red, white-hot core, red, dark gap = two parallel lit tubes
    return `<g class="lt" id="${id}"><path class="dull" d="${d}"/><g class="lit"><path class="gl" d="${d}"/><path d="${d}" stroke="${RED}" stroke-width="8"/><path d="${d}" stroke="${CORE}" stroke-width="6.2"/><path d="${d}" stroke="${RED}" stroke-width="4.6"/></g><path d="${d}" stroke="${DARK}" stroke-width="3"/></g>`;
  }
  const CSS = `
#nrneon{position:relative;width:80%;max-width:400px;margin:0 auto}
#nrneon .spill{position:absolute;left:-30%;right:-30%;top:-25%;bottom:-35%;background:radial-gradient(ellipse at 50% 45%,rgba(255,40,20,.34),rgba(255,40,20,.12) 40%,transparent 68%);pointer-events:none;opacity:0;mix-blend-mode:screen}
#nrneon svg{position:relative;display:block;width:100%;height:auto;overflow:visible}
#nrneon text{fill:none}
#nrneon text.plate{fill:#8a8070;font-family:"Courier New",monospace;font-size:9px;letter-spacing:4px}
#nrneon path{fill:none;stroke-linejoin:round;stroke-linecap:round}
#nrneon .dull{stroke:#4a1a14;stroke-width:8}
#nrneon .gl{stroke:#ff2a14;stroke-width:12;filter:url(#nrblur);opacity:.85}
#nrneon .lt .lit{transition:opacity .03s}
#nrneon .lt.off .lit{opacity:0}
#nrneon .lt.dim .lit{opacity:.45}
#nrneon .lt .lit{filter:drop-shadow(0 0 3px rgba(255,60,30,.9)) drop-shadow(0 0 10px rgba(255,30,10,.6))}
#nrneon .nscript .lit{filter:drop-shadow(0 0 3px rgba(255,240,225,.95)) drop-shadow(0 0 9px rgba(255,220,200,.5))}
#nrneon .nscript text{font-family:"Snell Roundhand","Segoe Script","Brush Script MT","Lucida Handwriting",cursive;font-size:33px;font-style:italic}
#nrneon .nscript .dull{stroke:#3a3430;stroke-width:3.2}
#nrneon .case{position:absolute;left:0;right:0;bottom:-26px;text-align:center;font-family:"Courier New",monospace;font-size:11px;letter-spacing:.42em;color:#b8ac98;text-shadow:0 1px 3px #000}`;
  let root = null, letters = [], script = null, spill = null, level = 0, running = false, started = false, raf = 0;
  function mount(container) {
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    const l1 = word('NEON', 36), l2 = word('RAIN', 116);
    const ids = ['N1', 'E1', 'O1', 'N2', 'R2', 'A2', 'I2', 'N3'];
    const bolts = [[22, 22], [318, 22], [22, 262], [318, 262]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.2" fill="#6a6560"/><path d="M${x - 2},${y}H${x + 2}" stroke="#2a2724" stroke-width="1"/>`).join('');
    const svg = `<svg viewBox="0 -24 340 312" aria-label="NEON RAIN, The Glass Saint">
      <defs><filter id="nrblur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>
        <linearGradient id="nrbox" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#26221f"/><stop offset=".5" stop-color="#141210"/><stop offset="1" stop-color="#0a0908"/></linearGradient></defs>
      <path d="M90,-24V12M250,-24V12" stroke="#3a3632" stroke-width="5"/><rect x="78" y="6" width="24" height="10" fill="#2a2724"/><rect x="238" y="6" width="24" height="10" fill="#2a2724"/>
      <rect x="10" y="12" width="320" height="262" rx="10" fill="url(#nrbox)" stroke="#3e3934" stroke-width="3"/>
      <rect x="18" y="20" width="304" height="246" rx="6" fill="none" stroke="#221e1b" stroke-width="2"/>${bolts}
      ${[...l1, ...l2].map((d, i) => tube(d, ids[i])).join('')}
      <g class="lt nscript" id="S1"><text class="dull" x="170" y="246" text-anchor="middle" textLength="250" lengthAdjust="spacingAndGlyphs">The Glass Saint</text>
        <g class="lit"><text x="170" y="246" text-anchor="middle" textLength="250" lengthAdjust="spacingAndGlyphs" fill="none" stroke="#ffd9c4" stroke-width="3.2" opacity=".55">The Glass Saint</text><text x="170" y="246" text-anchor="middle" textLength="250" lengthAdjust="spacingAndGlyphs" fill="none" stroke="#fffaf4" stroke-width="1.4">The Glass Saint</text></g></g>
      <text class="plate" x="170" y="267" text-anchor="middle">CASE 01</text>
      </svg>`;
    container.innerHTML = '<div id="nrneon"><div class="spill"></div>' + svg + '</div>';
    root = container.querySelector('#nrneon'); spill = root.querySelector('.spill');
    letters = ids.map(id => root.querySelector('#' + id)); script = root.querySelector('#S1');
    for (const l of [...letters, script]) l.classList.add('off');
  }
  const A = () => NR.audio && NR.audio.fx;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  async function start() {
    if (started) return; started = true; running = true;
    if (A() && A().neonHum) A().neonHum(true);
    if (RM) { for (const l of [...letters, script]) l.classList.remove('off'); level = 1; tick(); return; }
    // startup: each tube catches with a click and a short sputter, then the script, then the whole sign sags once
    for (const l of [...letters, script]) {
      await wait(140 + Math.random() * 120); if (A()) A().neonClick();
      for (let k = 0; k < 2 + (Math.random() * 3 | 0); k++) { l.classList.remove('off'); await wait(30 + Math.random() * 50); l.classList.add('off'); await wait(30 + Math.random() * 70); }
      l.classList.remove('off');
    }
    root.style.transition = 'opacity .12s'; root.style.opacity = .55; await wait(160); root.style.opacity = 1;
    tick();
  }
  // flicker: the A in RAIN sputters and sometimes dies for a beat; the whole sign dips now and then with a tick
  let aState = 'on', aT = 0, dipT = 0, last = performance.now();
  function tick() {
    cancelAnimationFrame(raf);
    const step = (now) => {
      raf = requestAnimationFrame(step); if (!running) return;
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      let lv = 1;
      if (!RM) {
        const a = letters[5];
        aT -= dt;
        if (aState === 'on' && Math.random() < dt * 0.35) { aState = Math.random() < 0.25 ? 'dead' : 'sputter'; aT = aState === 'dead' ? 0.7 + Math.random() * 0.9 : 0.25 + Math.random() * 0.5; if (A()) A().neonTick(); }
        if (aState === 'sputter') { const on = Math.random() < 0.55; a.classList.toggle('off', !on); a.classList.toggle('dim', on && Math.random() < 0.4); if (Math.random() < dt * 8 && A()) A().neonTick(); }
        if (aState === 'dead') a.classList.add('off');
        if (aT <= 0 && aState !== 'on') { aState = 'on'; a.classList.remove('off', 'dim'); }
        dipT -= dt; if (dipT <= 0 && Math.random() < dt * 0.12) { dipT = 0.07 + Math.random() * 0.08; if (A()) A().neonTick(); }
        if (dipT > 0) lv = 0.6;
        if (aState !== 'on') lv *= 0.9;
        root.style.opacity = lv;
      }
      level = lv * (0.9 + Math.sin(now / 90) * 0.02);
      spill.style.opacity = (level * 0.95).toFixed(3);
    };
    raf = requestAnimationFrame(step);
  }
  function stop() { running = false; cancelAnimationFrame(raf); level = 0; if (A() && A().neonHum) A().neonHum(false); }
  NR.neon = { mount, start, stop, get level() { return running ? level : 0; }, get started() { return started; }, get aState() { return aState; }, reducedMotion: RM };
})();
