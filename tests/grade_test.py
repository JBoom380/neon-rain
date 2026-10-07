"""FILM grade comparison at 390x844: NOIR COLOR (default) vs B&W RED on the landing menu, the office (Vela), the alley
and the club. Writes tests/shots/grade_noir_color.png. Usage: python tests/grade_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
pairs, errs, info = [], [], {}
def adv(pg, cond, t=90):
    t0 = time.time()
    while time.time() - t0 < t:
        if pg.evaluate(cond): return
        for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
            if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); break
        pg.wait_for_timeout(120)
    raise RuntimeError(cond)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        for name, q, cond, js in (("Landing menu", "", None, None),
                                  ("Office: Vela", "", "NR.game.beat === 'office_light' && NR.player.forceCig", None),
                                  ("Alley", "?beat=alley", "NR.game.beat === 'alley_play'", "NR.player.place(new THREE.Vector3(0,0,-4),0,0.02)"),
                                  ("Club", "?beat=club", "NR.game.beat === 'club_scan'", "NR.player.place(new THREE.Vector3(0.5,0,-5),0.15,0.04)")):
            pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
            pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html{q}"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(600)
            pg.touchscreen.tap(195, 500); pg.wait_for_timeout(4500 if not cond else 800)
            if cond:
                pg.evaluate("NR.ui.fast = true; document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
                adv(pg, cond); pg.wait_for_timeout(200 if 'office' in cond else 900)
            if js: pg.evaluate(js); pg.wait_for_timeout(700)
            info[name] = pg.evaluate("NR.core.settings.film")
            row = []
            for film in ("noir", "bwred"):
                pg.evaluate(f"NR.core.settings.film = '{film}'; NR.core.settings.bw = {'true' if film == 'bwred' else 'false'}"); pg.wait_for_timeout(250)
                f = f"grade_{len(pairs)}_{film}.png"; pg.screenshot(path=str(OUT / f)); row.append(f)
            pairs.append((name, row)); pg.close()
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (len(pairs) * 2 * (W + 8) + 16, H + 96), (14, 13, 12)); d = ImageDraw.Draw(img)
f1, fb = ImageFont.truetype("arial.ttf", 18), ImageFont.truetype("arialbd.ttf", 22)
d.text((12, 14), "FILM grade: NOIR COLOR (default) vs B&W RED", fill=(234, 223, 202), font=fb)
x = 12
for name, row in pairs:
    for f, lab in zip(row, ("NOIR COLOR", "B&W RED")):
        img.paste(Image.open(OUT / f).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), name + ": " + lab, fill=(232, 176, 64), font=f1); x += W + 8
img.save(OUT / "grade_noir_color.png")
print(json.dumps(info)); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
