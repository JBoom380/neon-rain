"""Landing-menu neon sign at 390x844 touch: startup, steady, a flicker frame -> tests/shots/neon_sign_title.png.
Also checks prefers-reduced-motion (steady glow, no flicker) and console errors. Usage: python tests/neon_sign_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
LIT = "Array.from(document.querySelectorAll('#nrneon .lt')).filter(l => !l.classList.contains('off')).length"
shots, info, errs = [], {}, []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(1200)
        pg.touchscreen.tap(195, 500); pg.wait_for_timeout(650)
        info["lit_at_startup"] = pg.evaluate(LIT); pg.screenshot(path=str(OUT / "neon_startup.png")); shots.append(("Startup: tubes catch one by one", "neon_startup.png"))
        pg.wait_for_function("NR.neon.started && " + LIT + " === 9", timeout=15000); pg.wait_for_timeout(600)
        for _ in range(100):
            if pg.evaluate("NR.neon.aState === 'on' && NR.neon.level > 0.85"): break
            pg.wait_for_timeout(50)
        pg.screenshot(path=str(OUT / "neon_steady.png")); shots.append(("Steady glow", "neon_steady.png"))
        info["light_steady"] = pg.evaluate("+NR.game.level.signLight.intensity.toFixed(1)")
        t0 = time.time()
        while time.time() - t0 < 60 and not pg.evaluate("NR.neon.aState === 'dead'"): pg.wait_for_timeout(30)
        pg.screenshot(path=str(OUT / "neon_flicker.png")); shots.append(("Flicker: the A in RAIN dies", "neon_flicker.png"))
        info["flicker_state"] = pg.evaluate("NR.neon.aState"); info["light_flicker"] = pg.evaluate("+NR.game.level.signLight.intensity.toFixed(1)")
        pg.close()
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True, is_mobile=True, reduced_motion="reduce")
        pg.on("pageerror", lambda e: errs.append("rm " + str(e)))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(800)
        pg.touchscreen.tap(195, 500); pg.wait_for_timeout(500)
        seen = set()
        for _ in range(40): seen.add((pg.evaluate(LIT), pg.evaluate("NR.neon.aState"))); pg.wait_for_timeout(120)
        info["reduced_motion_states"] = sorted(seen)
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (3 * (W + 12) + 12, H + 96), (14, 13, 12)); d = ImageDraw.Draw(img)
f1, fb = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 22)
d.text((12, 14), "NEON RAIN title: New York neon sign on the landing menu", fill=(234, 223, 202), font=fb)
for i, (label, fn) in enumerate(shots):
    x = 12 + i * (W + 12); img.paste(Image.open(OUT / fn).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), label, fill=(232, 176, 64), font=f1)
img.save(OUT / "neon_sign_title.png")
print(json.dumps(info)); print("ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
