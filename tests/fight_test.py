"""Club gunfight balance check (?beat=clubfight) on 390x844 touch, using the slice test's autopilot.
Run 1 CARELESS: stands in the open, sprays wildly -> should lose at least one life.
Run 2 HUMAN: reaction delay, aim wobble, slower aim -> should win, maybe losing a life.
Usage: python tests/fight_test.py"""
import json, pathlib, re, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT_JS = re.search(r'PILOT_JS = """(.*?)"""', (ROOT / "tests" / "slice_test.py").read_text(encoding="utf-8"), re.S).group(1)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
res, errs = {}, []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu"])
        for mode in ("careless", "human"):
            pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
            pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=clubfight"); pg.wait_for_function("window.READY === true")
            pg.wait_for_timeout(600); pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
            pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
            pg.evaluate(PILOT_JS)
            pg.evaluate(f"window.__pilot.fight = true; window.__pilot.careless = {'true' if mode == 'careless' else 'false'}; NR.controls.lastDevice; NR.player.__dev = 1")
            pg.evaluate("window.__downs = 0; window.__hurt = 0; NR.bus.on('playerDown', () => window.__downs++); NR.bus.on('playerHurt', () => window.__hurt++)")
            t0 = time.time(); limit = 45 if mode == "careless" else 150
            while time.time() - t0 < limit:
                if pg.evaluate("NR.game.beat") in ("club_clear", "end"): break
                if mode == "careless" and pg.evaluate("window.__downs") >= 1: break
                for sel in ("#nru > .card.on", "#nru > .dlg.on", "#nru .over.on .btn.red"):
                    if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))")
                pg.wait_for_timeout(250)
            res[mode] = pg.evaluate("({ beat: NR.game.beat, downs: window.__downs, hurtHits: window.__hurt, shots: NR.player.shots, hits: NR.player.hits, heads: NR.player.heads })")
            res[mode]["secs"] = round(time.time() - t0)
            pg.screenshot(path=str(ROOT / "tests" / "shots" / f"fight_{mode}.png")); pg.close()
        b.close()
finally:
    srv.terminate()
print(json.dumps(res)); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
