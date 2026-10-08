"""Eye transition (menu -> case intertitle) at 390x844: 3 frames of the push-in -> tests/shots/eye_transition.png"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8); shots, errs = [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(800)
        pg.touchscreen.tap(195, 500); pg.wait_for_timeout(1500)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        pg.wait_for_function("document.querySelector('#nreye.on')", timeout=10000)
        for k, (ms, lab) in enumerate(((900, "Eye: fade in"), (1500, "Push-in, city lights drift in the iris"), (1000, "Hand-off to the case intertitle"))):
            pg.wait_for_timeout(ms); f = f"eye_{k}.png"; pg.screenshot(path=str(OUT / f)); shots.append((lab, f))
        pg.wait_for_function("document.querySelector('#nru > .card.on')", timeout=10000); info = "card after eye: ok"
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (3 * (W + 12) + 12, H + 96), (14, 13, 12)); d = ImageDraw.Draw(img)
f1, fb = ImageFont.truetype("arial.ttf", 19), ImageFont.truetype("arialbd.ttf", 22)
d.text((12, 14), "NEON RAIN: eye transition, menu to case intertitle", fill=(234, 223, 202), font=fb)
for i, (lab, fn) in enumerate(shots):
    x = 12 + i * (W + 12); img.paste(Image.open(OUT / fn).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), lab, fill=(232, 176, 64), font=f1)
img.save(OUT / "eye_transition.png"); print(info, "ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
