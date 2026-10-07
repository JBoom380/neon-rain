// NEON RAIN audio: John's score (assets/music/tracks.json) on two crossfading decks with a VO duck, seamless rain loops per scene
// (OGG, MP3 fallback for iOS Safari), Media Session, and synthesized sfx (revolver, reload, lighter, heartbeat).
(function () {
  let ctx = null, master = null, sfxBus = null, unlocked = false, noiseBuf = null, humNodes = null;
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
    neonClick() { if (!ensure()) return; const t = ctx.currentTime; tone(1800, 'square', 0.05, 0.015, t); noise(0.03, 'highpass', 2500, 0.7, 0.12, 0.001, 0.05, t); tone(95, 'sawtooth', 0.05, 0.18, t + 0.01, 60); },
    neonTick() { noise(0.02, 'bandpass', 3200, 2, 0.06, 0.001, 0.035); tone(120, 'sawtooth', 0.025, 0.08, null, 90); },
    neonHum(on) { if (!ensure()) return; if (on && !humNodes) { const g = ctx.createGain(); g.gain.value = 0; const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 420;
        const o1 = ctx.createOscillator(); o1.type = 'sawtooth'; o1.frequency.value = 60; const o2 = ctx.createOscillator(); o2.type = 'sine'; o2.frequency.value = 120; const g2 = ctx.createGain(); g2.gain.value = 0.6;
        o1.connect(f); o2.connect(g2); g2.connect(f); f.connect(g); g.connect(sfxBus); o1.start(); o2.start(); g.gain.setTargetAtTime(0.022, ctx.currentTime, 0.4); humNodes = { g, o1, o2 }; }
      else if (!on && humNodes) { const h = humNodes; humNodes = null; h.g.gain.setTargetAtTime(0, ctx.currentTime, 0.3); setTimeout(() => { try { h.o1.stop(); h.o2.stop(); } catch (e) {} }, 1500); } },
    whizz() { if (!ensure()) return; const n = noise(0.18, 'bandpass', 2600, 6, 0.18, 0.03, 0.18); if (n) n.f.frequency.exponentialRampToValueAtTime(900, ctx.currentTime + 0.2); },
    heel() { tone(2600 + Math.random() * 300, 'triangle', 0.05, 0.03); noise(0.02, 'highpass', 3000, 0.7, 0.06, 0.001, 0.04); },
    step() { noise(0.02, 'lowpass', 500, 0.7, 0.12, 0.001, 0.08); },
    type() { tone(1800 + Math.random() * 400, 'square', 0.015, 0.012); },
    door() { noise(0.6, 'bandpass', 250, 2, 0.25, 0.05, 0.6); tone(90, 'sawtooth', 0.04, 0.5, null, 70); },
    thump() { tone(55, 'sine', 0.9, 0.5, null, 30); noise(0.1, 'lowpass', 300, 0.7, 0.5, 0.001, 0.3); },
    heartbeat(rate) { if (!ensure()) return; const t = ctx.currentTime; tone(60, 'sine', 0.35, 0.12, t, 40); tone(55, 'sine', 0.25, 0.12, t + 60 / rate * 0.32, 40); },
  };
  // ---------------------------------------------------------------- music: two decks, 1.5 s crossfade, VO duck
  let musicBus = null, duckV = 1; const decks = []; let deckOn = -1, cueId = null, tracks = null, onEnded = null, loopMode = true;
  const FALLBACK_TRACKS = { album: 'NEON RAIN: The Glass Saint', tracks: [] };
  function loadTracks() {
    if (tracks) return Promise.resolve(tracks);
    return fetch(NR.ASSET + 'music/tracks.json').then(r => r.json()).catch(() => FALLBACK_TRACKS).then(j => (tracks = j));
  }
  function deck(i) {
    if (decks[i]) return decks[i];
    const el = new Audio(); el.preload = 'auto'; el.crossOrigin = 'anonymous'; el.loop = true;
    const d = { el, gain: null };
    if (ensure()) { const src = ctx.createMediaElementSource(el); d.gain = ctx.createGain(); d.gain.gain.value = 0; src.connect(d.gain); d.gain.connect(musicBusNode()); }
    el.addEventListener('ended', () => { if (decks[deckOn] === d && onEnded) onEnded(); });
    return (decks[i] = d);
  }
  function musicBusNode() { if (!musicBus) { musicBus = ctx.createGain(); musicBus.gain.value = S().music; musicBus.connect(master); } return musicBus; }
  function trackOf(id) { return tracks && tracks.tracks.find(t => t.id === id); }
  // play cue `id` (a tracks.json id); fades the other deck out over `fade` seconds
  async function cue(id, fade = 1.5, opts = {}) {
    await loadTracks(); const t = trackOf(id); if (!t) return;
    if (id === cueId && !opts.restart) return; cueId = id; loopMode = opts.loop !== false;
    const next = deckOn === 0 ? 1 : 0, d = deck(next), old = decks[deckOn];
    d.el.loop = loopMode; d.el.src = NR.ASSET + 'music/' + t.file; try { d.el.currentTime = opts.at || 0; } catch (e) {}
    if (unlocked) { const p = d.el.play(); if (p && p.catch) p.catch(() => {}); }
    const now = ctx ? ctx.currentTime : 0;
    if (d.gain) { d.gain.gain.cancelScheduledValues(now); d.gain.gain.setValueAtTime(0.0001, now); d.gain.gain.linearRampToValueAtTime(1, now + fade); } else d.el.volume = S().music;
    if (old && old !== d) { if (old.gain) { old.gain.gain.cancelScheduledValues(now); old.gain.gain.setValueAtTime(old.gain.gain.value, now); old.gain.gain.linearRampToValueAtTime(0.0001, now + fade); } const oe = old.el; setTimeout(() => { if (decks[deckOn] !== old) oe.pause(); }, fade * 1000 + 80); }
    deckOn = next; mediaSession(t); NR.bus.emit('music', { id, title: t.title });
    try { const heard = JSON.parse(localStorage.getItem('neonRainFps.heard') || '[]'); if (!heard.includes(id)) { heard.push(id); localStorage.setItem('neonRainFps.heard', JSON.stringify(heard)); } } catch (e) {}
  }
  function current() { const d = decks[deckOn]; return d ? d.el : null; }
  function setOnEnded(f) { onEnded = f; }
  function duck(v) { duckV = v; if (musicBus) musicBus.gain.setTargetAtTime(S().music * v, ctx.currentTime, 0.25); else { const c = current(); if (c) c.volume = S().music * v; } rainLevel(); }
  function mediaSession(t) {
    if (!('mediaSession' in navigator) || !t) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({ title: t.title, artist: 'NEON RAIN', album: (tracks && tracks.album) || 'NEON RAIN', artwork: [{ src: NR.ASSET + 'og-office.jpg', sizes: '1200x630', type: 'image/jpeg' }] });
      const J = NR.jukebox;
      const h = { play: () => { const c = current(); if (c) c.play(); }, pause: () => { const c = current(); if (c) c.pause(); }, previoustrack: () => J && J.prev(), nexttrack: () => J && J.next(),
        seekto: (e) => { const c = current(); if (c && e.seekTime != null) c.currentTime = e.seekTime; } };
      for (const k in h) navigator.mediaSession.setActionHandler(k, h[k]);
    } catch (e) {}
  }
  // ---------------------------------------------------------------- rain ambience: seamless AudioBuffer loops, 2 s crossfade
  const rainBufs = {}; let rainNow = [];
  const RAIN_EXT = (() => { try { return new Audio().canPlayType('audio/ogg; codecs="vorbis"') ? '.ogg' : '.mp3'; } catch (e) { return '.mp3'; } })();
  function rainBuf(name) { if (!rainBufs[name]) rainBufs[name] = fetch(NR.ASSET + 'rain/' + name + RAIN_EXT).then(r => r.arrayBuffer()).then(b => new Promise((res, rej) => ctx.decodeAudioData(b, res, rej))); return rainBufs[name]; }
  // layers: [[name, gain], ...]
  // Rain sits behind the score: its own bus, lowpassed (muffled; ~1 kHz inside the club), a high-shelf cut, and widened:
  // each loop plays as two copies half a loop apart, panned hard left and hard right, so nothing sits in the centre.
  // Level ~0.16 of the music bus, -3 dB more under VO, a little louder when no music plays.
  let rainBus = null, rainLP = null, rainHS = null, rainMeter = null, musicMeter = null;
  const RAIN_BASE = 0.16, RAIN_SILENT = 0.3, RAIN_VO = 0.7;
  function rainChain() {
    if (rainBus) return; rainLP = ctx.createBiquadFilter(); rainLP.type = 'lowpass'; rainLP.frequency.value = 2200; rainLP.Q.value = 0.5;
    rainHS = ctx.createBiquadFilter(); rainHS.type = 'highshelf'; rainHS.frequency.value = 3000; rainHS.gain.value = -9;
    rainBus = ctx.createGain(); rainBus.gain.value = RAIN_BASE * S().sfx; rainLP.connect(rainHS); rainHS.connect(rainBus); rainBus.connect(master);
  }
  function rainLevel() {
    if (!rainBus) return; const c = current(), silent = !c || c.paused || c.ended;
    const v = (silent ? RAIN_SILENT : RAIN_BASE) * (duckV < 1 ? RAIN_VO : 1) * S().sfx;
    rainBus.gain.setTargetAtTime(v, ctx.currentTime, 0.5);
  }
  setInterval(() => { if (ctx) rainLevel(); }, 500);
  // layers: [[name, gain], ...]; an optional layers.lp sets the lowpass cutoff (Hz)
  async function ambience(layers) {
    if (!ensure()) return; rainChain(); const now = ctx.currentTime;
    rainLP.frequency.setTargetAtTime(layers.lp || 2200, now, 0.5);
    for (const n of rainNow) { n.g.gain.cancelScheduledValues(now); n.g.gain.setValueAtTime(n.g.gain.value, now); n.g.gain.linearRampToValueAtTime(0.0001, now + 2); const srcs = n.srcs; setTimeout(() => { for (const x of srcs) { try { x.stop(); } catch (e) {} } }, 2200); }
    rainNow = [];
    for (const [name, gain] of layers) {
      try {
        const buf = await rainBuf(name), g = ctx.createGain(), srcs = [], off = Math.random() * buf.duration;
        g.gain.value = 0.0001; g.connect(rainLP);
        for (const [pan, shift] of [[-1, 0], [1, 0.5]]) { const src = ctx.createBufferSource(), p = ctx.createStereoPanner(); src.buffer = buf; src.loop = true; p.pan.value = pan; src.connect(p); p.connect(g); src.start(0, (off + shift * buf.duration) % buf.duration); srcs.push(src); }
        g.gain.linearRampToValueAtTime(gain * 0.5, ctx.currentTime + 2); rainNow.push({ srcs, g });
      } catch (e) { console.warn('rain loop failed', name, e); }
    }
    rainLevel();
  }
  // dev meter: RMS (dBFS) of the rain bus and the music bus over `secs` seconds
  function meter(secs = 10) {
    if (!ensure() || !rainBus) return Promise.resolve(null);
    if (!rainMeter) { rainMeter = ctx.createAnalyser(); rainMeter.fftSize = 2048; rainBus.connect(rainMeter); musicMeter = ctx.createAnalyser(); musicMeter.fftSize = 2048; musicBusNode().connect(musicMeter); }
    const buf = new Float32Array(2048); let rs = 0, ms = 0, n = 0;
    return new Promise(res => { const iv = setInterval(() => { rainMeter.getFloatTimeDomainData(buf); for (const v of buf) rs += v * v; musicMeter.getFloatTimeDomainData(buf); for (const v of buf) ms += v * v; n += 2048; }, 50);
      setTimeout(() => { clearInterval(iv); const db = x => +(10 * Math.log10(x / n + 1e-12)).toFixed(1); res({ rain: db(rs), music: db(ms), gap: +(db(ms) - db(rs)).toFixed(1) }); }, secs * 1000); });
  }
  function rainBed(on) { if (!on) ambience([]); }
  function playMusic(id) { return cue(id); }
  function unlock() {
    unlocked = true; ensure(); if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
    const c = current(); if (c && c.src) { const p = c.play(); if (p && p.catch) p.catch(() => {}); }
  }
  function setVolumes() { rainLevel(); if (sfxBus) sfxBus.gain.value = S().sfx; if (musicBus) musicBus.gain.value = S().music * duckV; }
  function init() {
    const B = NR.bus;
    B.on('shot', () => fx.shot()); B.on('dryFire', () => fx.dry()); B.on('reload', () => fx.reload());
    B.on('nearMiss', () => fx.whizz()); B.on('hitEnemy', d => d.head ? fx.head() : fx.hitFlesh()); B.on('playerHurt', () => fx.hurt());
    B.on('enemyShot', d => { const P = NR.player; fx.enemyShot(P ? d.pos.distanceTo(P.pos) : 10); });
    B.on('smoke', () => { fx.lighter(); setTimeout(fx.inhale, 400); }); B.on('focus', () => fx.focus()); B.on('clue', () => fx.clue());
  }
  NR.audio = { meter, init, fx, unlock, playMusic, cue, duck, rainBed, ambience, setVolumes, loadTracks, current, setOnEnded, trackOf, get tracks() { return tracks; }, get cueId() { return cueId; }, get deckGains() { return decks.map(d => d.gain ? +d.gain.gain.value.toFixed(3) : null); }, get unlocked() { return unlocked; } };
})();
