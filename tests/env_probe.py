"""Dev probe for the env pass: load a level directly and print material/lightmap state, optional screenshot.
Usage: python tests/env_probe.py LEVEL [out.png] [js]"""
import pathlib, socket, subprocess, sys, time, json
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
lvl = sys.argv[1]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: print("PAGEERROR:", e)); pg.on("console", lambda m: m.type in ("error", "warning") and print(m.type, m.text[:300]))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true")
        pg.wait_for_timeout(500); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
        pg.evaluate(f"""(async () => {{ NR.game.titleCam = false; NR.core.fx.fade = 0; const L = NR.game.load('{lvl}'); await NR.env.ready['{lvl}']; NR.core.setState('PLAY'); }})()""")
        pg.wait_for_timeout(2500)
        print(json.dumps(pg.evaluate("""(() => { const out = []; const L = NR.game.level; if (L.env) L.env.traverse(o => { if (o.isMesh) out.push([o.name, o.material.type, o.material.name, !!o.material.map, !!o.material.lightMap, o.material.lightMapIntensity, o.material.color && o.material.color.getHexString(), Object.keys(o.geometry.attributes)]); }); return { n: out.length, out: out.slice(0, 20), boxes: L.boxes.length, covers: L.covers.length }; })()"""), indent=0))
        for js in sys.argv[3:]:
            print(">", js[:80], "=>", pg.evaluate(js)); pg.wait_for_timeout(400)
        pg.wait_for_timeout(800)
        print("fps", round(pg.evaluate("NR.core.fps")))
        if len(sys.argv) > 2: pg.screenshot(path=sys.argv[2])
        b.close()
finally:
    srv.terminate()
