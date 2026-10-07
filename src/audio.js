// NEON RAIN audio: placeholder music (SkyRunner's RAINY SAX) + synthesized sfx (revolver, reload, lighter, rain bed, heartbeat).
(function () {
  let ctx = null, master = null, sfxBus = null, rainGain = null, music = null, unlocked = false, noiseBuf = null;
  const S = () => NR.core.settings;
  function ensure() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
    ctx = new AC(); master = ctx.createGain(); master.gain.value = 1; master.connect(ctx.destination);
    sfxBus = ctx.createGain(); sfxBus.gain.value = S().sfx; sfxBus.connect(master);
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate); const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    return ctx;
  }
  function noise(dur, filterType, freq, q, gain, attack, decay, when, dest) {
    if (!ensure()) return; const t = (when || ctx.currentTime);
    const src = ctx.createBufferSource(); src.buffer = noiseBuf; src.loop = true;
    const f = ctx.createBiquadFilter(); f.type = filterType; f.frequency.value = freq; f.Q.value = q || 0.7;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + (attack || 0.002)); g.gain.exponentialRampToValueAtTime(0.0001, t + (attack || 0.002) + decay);
    src.connect(f); f.connect(g); g.connect(dest || sfxBus); src.start(t, Math.random()); src.stop(t + dur + decay + 0.05);
    return { f, g };
  }
  function tone(freq, type, gain, decay, when, slide) {
    if (!ensure()) return; const t = when || ctx.currentTime;
    const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(freq, t); if (slide) o.frequency.exponentialRampToValueAtTime(slide, t + decay);
    const g = ctx.createGain(); g.gain.setValueAtTime(gain, t); g.gain.exponentialRampToValueAtTime(0.0001, t + decay);
    o.connect(g); g.connect(sfxBus); o.start(t); o.stop(t + decay + 0.05);
  }
  const fx = {
    shot() { if (!ensure()) return; const t = ctx.currentTime; noise(0.05, 'lowpass', 3800, 0.5, 0.9, 0.001, 0.22, t); noise(0.2, 'lowpass', 600, 0.7, 0.7, 0.002, 0.5, t); tone(110, 'sine', 0.8, 0.25, t, 40); noise(0.4, 'bandpass', 900, 0.4, 0.08, 0.05, 0.9, t + 0.05); },
    enemyShot(dist) { if (!ensure()) return; const v = Math.max(0.12, 0.5 - dist * 0.015); noise(0.04, 'lowpass', 2600, 0.5, v, 0.001, 0.18); tone(140, 'sine', v * 0.6, 0.18, null, 50); },
    dry() { tone(2400, 'square', 0.08, 0.03); },
    reload() { if (!ensure()) return; const t = ctx.currentTime; tone(1800, 'square', 0.06, 0.03, t); noise(0.3, 'bandpass', 3500, 3, 0.12, 0.01, 0.35, t + 0.2); for (let i = 0; i < 6; i++) tone(2600 + i * 40, 'square', 0.04, 0.02, t + 0.55 + i * 0.07); tone(1500, 'square', 0.09, 0.04, t + 1.4); },
    hitFlesh() { noise(0.03, 'lowpass', 900, 0.8, 0.5, 0.001, 0.12); },
    head() { tone(2100, 'triangle', 0.15, 0.12); noise(0.03, 'lowpass', 1200, 0.8, 0.5, 0.001, 0.12); },
    hurt() { tone(70, 'sine', 0.7, 0.3, null, 40); noise(0.05, 'lowpass', 500, 0.7, 0.4, 0.001, 0.2); },
    lighter() { if (!ensure()) return; const t = ctx.currentTime; tone(3200, 'square', 0.05, 0.02, t); noise(0.08, 'highpass', 4000, 0.7, 0.2, 0.002, 0.08, t + 0.03); noise(0.6, 'bandpass', 700, 0.6, 0.12, 0.08, 0.6, t + 0.08); },
    inhale() { noise(0.8, 'bandpass', 1400, 0.8, 0.07, 0.3, 0.8); },
    focus() { if (!ensure()) return; const t = ctx.currentTime; tone(220, 'sine', 0.25, 1.2, t, 70); noise(1.0, 'lowpass', 300, 0.7, 0.2, 0.05, 1.2, t); },
    clue() { if (!ensure()) return; const t = ctx.currentTime; tone(660, 'triangle', 0.12, 0.4, t); tone(990, 'triangle', 0.1, 0.5, t + 0.09); },
    whizz() { if (!ensure()) return; const n = noise(0.18, 'bandpass', 2600, 6, 0.18, 0.03, 0.18); if (n) n.f.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 0.2); },
    heel() { tone(2600 + Math.random() * 300, 'triangle', 0.05, 0.03); noise(0.02, 'highpass', 3000, 0.7, 0.06, 0.001, 0.04); },
    step() { noise(0.02, 'lowpass', 500, 0.7, 0.12, 0.001, 0.08); },
    type() { tone(1800 + Math.random() * 400, 'square', 0.015, 0.012); },
    door() { noise(0.6, 'bandpass', 250, 2, 0.25, 0.05, 0.6); tone(90, 'sawtooth', 0.04, 0.5, null, 70); },
    thump() { tone(55, 'sine', 0.9, 0.5, null, 30); noise(0.1, 'lowpass', 300, 0.7, 0.5, 0.001, 0.3); },
    heartbeat(rate) { if (!ensure()) return; const t = ctx.currentTime; tone(60, 'sine', 0.35, 0.12, t, 40); tone(55, 'sine', 0.25, 0.12, t + 60 / rate * 0.32, 40); },
  };
  function rainBed(on, level) {
    if (!ensure()) return;
    if (!rainGain) { const src = ctx.createBufferSource(); src.buffer = noiseBuf; src.loop = true; const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 2200; f.Q.value = 0.4; rainGain = ctx.createGain(); rainGain.gain.value = 0; src.connect(f); f.connect(rainGain); rainGain.connect(sfxBus); src.start(); }
    rainGain.gain.setTargetAtTime(on ? (level || 0.06) : 0, ctx.currentTime, 0.6);
  }
  function playMusic(url) {
    if (!music) { music = new Audio(); music.loop = true; music.preload = 'auto'; }
    music.volume = S().music;
    if (music.dataset.src !== url) { music.src = url; music.dataset.src = url; }
    if (unlocked) { const p = music.play(); if (p && p.catch) p.catch(() => {}); }
  }
  function duck(v) { if (music) music.volume = S().music * v; }
  function unlock() {
    unlocked = true; ensure(); if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
    if (music && music.src) { const p = music.play(); if (p && p.catch) p.catch(() => {}); }
  }
  function setVolumes() { if (sfxBus) sfxBus.gain.value = S().sfx; if (music) music.volume = S().music; }
  function init() {
    const B = NR.bus;
    B.on('shot', () => fx.shot()); B.on('dryFire', () => fx.dry()); B.on('reload', () => fx.reload());
    B.on('nearMiss', () => fx.whizz()); B.on('hitEnemy', d => d.head ? fx.head() : fx.hitFlesh()); B.on('playerHurt', () => fx.hurt());
    B.on('enemyShot', d => { const P = NR.player; fx.enemyShot(P ? d.pos.distanceTo(P.pos) : 10); });
    B.on('smoke', () => { fx.lighter(); setTimeout(fx.inhale, 400); }); B.on('focus', () => fx.focus()); B.on('clue', () => fx.clue());
  }
  NR.audio = { init, fx, unlock, playMusic, duck, rainBed, setVolumes, get unlocked() { return unlocked; } };
})();
