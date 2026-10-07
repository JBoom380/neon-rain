"""Quick probe: load src/dev.html at 390x844 touch, print console errors, screenshot. Usage: python tests/probe.py [js-to-run-after-load] [wait-ms]"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: print("PAGEERROR:", e))
        pg.on("console", lambda m: m.type in ("error", "warning") and print(m.type.upper() + ":", m.text[:300]))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html")
        pg.wait_for_function("window.READY === true", timeout=30000)
        pg.wait_for_timeout(int(sys.argv[2]) if len(sys.argv) > 2 else 2500)
        if len(sys.argv) > 1 and sys.argv[1]:
            print("eval:", pg.evaluate(sys.argv[1]))
            pg.wait_for_timeout(1500)
        print("state", pg.evaluate("NR.core.state"), "beat", pg.evaluate("NR.game.beat"), "fps", round(pg.evaluate("NR.core.fps"), 1))
        pg.screenshot(path=str(OUT / "probe.png"))
        b.close()
finally:
    srv.terminate()
