// NEON RAIN shared config: tuning, asset paths, rng, event bus. See SPEC.md.
window.NR = window.NR || {};
NR.cfg = {
  EYE: 1.62, RADIUS: 0.32, WALK: 3.4, LOOK_TOUCH: 0.0062, LOOK_MOUSE: 0.0022,
  HP: 100, REGEN_DELAY: 3.2, REGEN: 14, REGEN_COVER: 34, LIVES: 3,
  GUN_ROUNDS: 6, GUN_RATE: 0.34, GUN_RELOAD: 1.55, GUN_DMG: 34, HEAD_MULT: 2, GUN_RANGE: 60,
  PACK_START: 6, PACK_MAX: 12, SMOKE_LIT: 12, FOCUS_TIME: 3, FOCUS_SCALE: 0.4,
  ASSIST_CONE: 0.045, ASSIST_FRICTION: 0.72,
  SETTINGS_KEY: 'neonRainFps.settings', CASE_KEY: 'neonRainFps.case',
};
NR.ASSET = document.querySelector('script[src="config.js"]') ? '../assets/' : 'assets/'; // dev.html lives in src/
NR.RAIN = { office: [['rain_05_int_window_close', 2.0]], alley: [['rain_13_ext_alley_gutter', 0.9], ['rain_10_ext_heavy_downpour', 0.6]], club: [['rain_09_int_heavy_rain_through_walls', 2.0]] }; // ambience per scene
NR.RAIN.club.lp = 1000; NR.RAIN.office.lp = 2000; NR.RAIN.alley.lp = 2400; // muffled rain: lowpass cutoff per scene
NR.SPRITE = (who, name) => NR.ASSET + 'sprites/' + who + '_' + name + '.webp';
NR.CLOSE = (who, mood) => NR.ASSET + 'sprites/' + who + '_close_' + mood + '.jpg';
NR.rng = (seed) => { let s = (seed >>> 0) || 1; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
NR.bus = (() => { const h = {}; return {
  on(e, f) { (h[e] = h[e] || []).push(f); }, off(e, f) { h[e] = (h[e] || []).filter(x => x !== f); },
  emit(e, d) { for (const f of (h[e] || []).slice()) { try { f(d); } catch (err) { console.error('[NR.bus ' + e + ']', err); } } },
}; })();
NR.clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
