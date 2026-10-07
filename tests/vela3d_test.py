"""3D Vela (CHARACTERS: 3D) in the office at 390x844 touch: walk-in, at the desk, the lighting beat; fps; console errors.
Writes tests/shots/women_in_game_3d.png. Usage: python tests/vela3d_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0; function f(now) { t.push(now - last); last = now; if (++n < 180) requestAnimationFrame(f); else { t.sort((a,b)=>a-b); r({ fps: +(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1), p95ms: +t[Math.floor(t.length*0.95)].toFixed(1) }); } } requestAnimationFrame(f); })"""
errs, shots, info = [], [], {}
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type in ("error", "warning") and errs.append(m.type + ": " + m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?chars=3d"); pg.wait_for_function("window.READY === true")
        pg.wait_for_timeout(800); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        want = [("walk", "3D Vela walks in ('walk' clip)", "NR.game.chars[0] && NR.game.chars[0].walking && NR.game.chars[0].pos.z > -3.0", 0),
                ("desk", "3D Vela at her mark ('idle' clip)", "NR.game.beat === 'office_talk'", 1500),
                ("light", "3D Vela: the lighting beat", "NR.game.beat === 'office_light' && NR.player.forceCig", 450)]
        t0 = time.time(); last = 0
        while want and time.time() - t0 < 150:
            key, label, cond, delay = want[0]
            if pg.evaluate(cond):
                pg.wait_for_timeout(delay); f = f"vela3d_{key}.png"; pg.screenshot(path=str(OUT / f)); shots.append((label, f)); want.pop(0)
                if key == "desk": info["fps_desk"] = pg.evaluate(FPS_JS); info["model"] = pg.evaluate("NR.game.chars[0].constructor.name")
                continue
            if time.time() - last > 1.6 and pg.evaluate("NR.core.state") == "CUTSCENE":
                for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
                    if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); last = time.time(); break
            pg.wait_for_timeout(100)
        # a close 3/4 at conversation distance, mid-frame
        pg.evaluate("(() => { const v = NR.game.chars[0]; NR.core.setState('CUTSCENE'); NR.game.lookTarget = () => new THREE.Vector3(v.pos.x, 1.45, v.pos.z); NR.player.place(new THREE.Vector3(v.pos.x + 1.0, 0, v.pos.z + 1.5), 0.6, 0); })()")
        pg.wait_for_timeout(1800); pg.screenshot(path=str(OUT / "vela3d_close.png")); shots.append(("3D Vela: 3/4 at conversation distance", "vela3d_close.png"))
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (len(shots) * (W + 12) + 12, H + 100), (14, 13, 12)); d = ImageDraw.Draw(img)
try: f, fb = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 22)
except Exception: f = fb = ImageFont.load_default()
d.text((12, 14), "NEON RAIN: 3D Vela (vela_game_v5.glb) in game lighting, B&W with red kept", fill=(234, 223, 202), font=fb)
for i, (label, fn) in enumerate(shots):
    x = 12 + i * (W + 12); img.paste(Image.open(OUT / fn).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), label, fill=(232, 176, 64), font=f)
img.save(OUT / "women_in_game_3d.png")
print(json.dumps(info)); print("ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
