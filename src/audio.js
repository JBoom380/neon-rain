// NEON RAIN audio: John's score (assets/music/tracks.json) on two crossfading decks with a VO duck, seamless rain loops per scene
// (OGG, MP3 fallback for iOS Safari), Media Session, and synthesized sfx (revolver, reload, lighter, heartbeat).
(function () {
  let ctx = null, master = null, sfxBus = null, unlocked = false, noiseBuf = null;
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
  function duck(v) { duckV = v; if (musicBus) musicBus.gain.setTargetAtTime(S().music * v, ctx.currentTime, 0.25); else { const c = current(); if (c) c.volume = S().music * v; } }
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
  async function ambience(layers) {
    if (!ensure()) return; const now = ctx.currentTime;
    for (const n of rainNow) { n.g.gain.cancelScheduledValues(now); n.g.gain.setValueAtTime(n.g.gain.value, now); n.g.gain.linearRampToValueAtTime(0.0001, now + 2); const src = n.src; setTimeout(() => { try { src.stop(); } catch (e) {} }, 2200); }
    rainNow = [];
    for (const [name, gain] of layers) {
      try {
        const buf = await rainBuf(name), src = ctx.createBufferSource(), g = ctx.createGain(); src.buffer = buf; src.loop = true;
        g.gain.value = 0.0001; src.connect(g); g.connect(sfxBus); src.start(0, Math.random() * buf.duration);
        g.gain.linearRampToValueAtTime(gain, ctx.currentTime + 2); rainNow.push({ src, g });
      } catch (e) { console.warn('rain loop failed', name, e); }
    }
  }
  function rainBed(on) { if (!on) ambience([]); }
  function playMusic(id) { return cue(id); }
  function unlock() {
    unlocked = true; ensure(); if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
    const c = current(); if (c && c.src) { const p = c.play(); if (p && p.catch) p.catch(() => {}); }
  }
  function setVolumes() { if (sfxBus) sfxBus.gain.value = S().sfx; if (musicBus) musicBus.gain.value = S().music * duckV; }
  function init() {
    const B = NR.bus;
    B.on('shot', () => fx.shot()); B.on('dryFire', () => fx.dry()); B.on('reload', () => fx.reload());
    B.on('nearMiss', () => fx.whizz()); B.on('hitEnemy', d => d.head ? fx.head() : fx.hitFlesh()); B.on('playerHurt', () => fx.hurt());
    B.on('enemyShot', d => { const P = NR.player; fx.enemyShot(P ? d.pos.distanceTo(P.pos) : 10); });
    B.on('smoke', () => { fx.lighter(); setTimeout(fx.inhale, 400); }); B.on('focus', () => fx.focus()); B.on('clue', () => fx.clue());
  }
  NR.audio = { init, fx, unlock, playMusic, cue, duck, rainBed, ambience, setVolumes, loadTracks, current, setOnEnded, trackOf, get tracks() { return tracks; }, get cueId() { return cueId; }, get deckGains() { return decks.map(d => d.gain ? +d.gain.gain.value.toFixed(3) : null); }, get unlocked() { return unlocked; } };
})();
