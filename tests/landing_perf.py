"""Landing-menu fps profile at 390x844 @2x: baseline, then with parts switched off to find the cost."""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
FPS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0; function f(now) { t.push(now - last); last = now; if (++n < 150) requestAnimationFrame(f); else r(+(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1)); } requestAnimationFrame(f); })"""
STEPS = [("baseline", ""), ("neon sign hidden", "document.getElementById('nrneon').style.display='none'"), ("neon back", "document.getElementById('nrneon').style.display=''"),
         ("canvas hidden (no WebGL cost on compositor)", "document.getElementById('game').style.visibility='hidden'"), ("canvas back", "document.getElementById('game').style.visibility=''"),
         ("shafts off", "NR.core.shaft && (NR.core.shaft.on = false)"), ("shadows off", "NR.core.renderer.shadowMap.enabled = false"),
         ("quality low", "NR.core.setQuality('low')")]
out = {}
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.goto(f"http://127.0.0.1:{PORT}/" + (sys.argv[1] if len(sys.argv) > 1 else "src/dev.html")); pg.wait_for_function("window.READY === true"); out["ready_at_ms"] = round(pg.evaluate("performance.now()")); pg.evaluate("window.__lf = []; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lf.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({ type: 'longtask', buffered: true })"); pg.wait_for_timeout(1000)
        out["tap_at_ms"] = round(pg.evaluate("performance.now()")); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(1200)
        out["at_1.2s_after_tap"] = pg.evaluate(FPS); out["long_frames"] = pg.evaluate("window.__lf || null"); pg.wait_for_timeout(4000)
        out["info"] = pg.evaluate("(() => { const i = NR.core.renderer.info; return { calls: i.render.calls, tris: i.render.triangles, geos: i.memory.geometries, tex: i.memory.textures, view: NR.core.view, pr: NR.core.renderer.getPixelRatio(), size: [NR.core.renderer.domElement.width, NR.core.renderer.domElement.height], q: NR.core.settings.quality }; })()")
        for name, js in STEPS:
            if js: pg.evaluate(js); pg.wait_for_timeout(500)
            out[name] = pg.evaluate(FPS)
        b.close()
finally:
    srv.terminate()
print(json.dumps(out, indent=0))
