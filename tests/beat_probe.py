"""Dev probe: jump to a beat (?beat=alley|club), run JS steps, screenshot. Usage: python tests/beat_probe.py BEAT "js;js" out.png [waitms]"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: print("PAGEERROR:", e)); pg.on("console", lambda m: m.type == "error" and print("ERR:", m.text[:300]))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat={sys.argv[1]}"); pg.wait_for_function("window.READY === true")
        pg.wait_for_timeout(800); pg.evaluate("NR.ui.fast = true")
        pg.touchscreen.tap(195, 500); pg.wait_for_timeout(500)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        for _ in range(200):
            st = pg.evaluate("NR.core.state")
            if st == "PLAY": break
            for sel in ("#nru .tut.on", "#nru .dlg.on", "#nru .card.on"):
                if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); break
            pg.wait_for_timeout(120)
        for js in [x for x in sys.argv[2].split(";;") if x.strip()]:
            print(">", js[:80], "=>", pg.evaluate(js)); pg.wait_for_timeout(300)
        pg.wait_for_timeout(int(sys.argv[4]) if len(sys.argv) > 4 else 1200)
        print("beat", pg.evaluate("NR.game.beat"), "state", pg.evaluate("NR.core.state"), "fps", round(pg.evaluate("NR.core.fps")))
        pg.screenshot(path=sys.argv[3]); b.close()
finally:
    srv.terminate()
