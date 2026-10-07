"""Rain-vs-music mix: 10 s RMS of the rain bus and the music bus per scene (landing, office, alley, club), and once under VO.
Target: rain at least 15 dB under the music. Usage: python tests/rain_mix_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
res, errs = {}, []
def advance_until(pg, cond, t=90, fast=True):
    t0 = time.time()
    while time.time() - t0 < t:
        if pg.evaluate(cond): return True
        for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
            if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); break
        pg.wait_for_timeout(150)
    raise RuntimeError("timeout " + cond)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--use-angle=d3d11", "--enable-gpu"])
        for scene, q, cond in (("landing", "", None), ("office", "", "NR.game.beat === 'office_smoke' && NR.core.state === 'PLAY'"), ("alley", "?beat=alley", "NR.game.beat === 'alley_play'"), ("club", "?beat=club", "NR.game.beat === 'club_scan'")):
            pg = b.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
            pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html{q}"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(600)
            pg.touchscreen.tap(195, 500); pg.wait_for_timeout(1500)
            if cond:
                pg.evaluate("NR.ui.fast = true; document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
                advance_until(pg, cond)
            pg.wait_for_timeout(2600)
            r = pg.evaluate("NR.audio.meter(10)"); r["cue"] = pg.evaluate("NR.audio.cueId"); res[scene] = r
            if scene == "club":  # under VO: show a dialogue line and hold it
                pg.evaluate("NR.ui.fast = false; NR.core.setState('CUTSCENE'); void NR.ui.say('HARROW (V.O.)', 'The rain had been at my window for three days, and it wanted in. So did everybody else in this city, and most of them had better reasons than the rain did.'); 0")
                pg.wait_for_timeout(1500); r2 = pg.evaluate("NR.audio.meter(8)"); r2["cue"] = pg.evaluate("NR.audio.cueId"); res["club_under_VO"] = r2
            pg.close()
        b.close()
finally:
    srv.terminate()
print(json.dumps(res)); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
