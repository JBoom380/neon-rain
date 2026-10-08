"""Holster / draw: holstered by default (cigarette hand, no FIRE, no ammo pips), FIRE does nothing while holstered,
the GUN button draws (0.45 s) and holsters (0.4 s), G / 1 keys, vm.anim calls. Screens -> tests/shots/holster_states.png"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8); r, errs, shots = {}, [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        cdp = pg.context.new_cdp_session(pg)
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=club"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(600)
        pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        for _ in range(200):
            if pg.evaluate("NR.game.beat === 'club_scan' && NR.core.state === 'PLAY'"): break
            for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
                if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); break
            pg.wait_for_timeout(120)
        pg.evaluate("window.__a = []; NR.bus.on('vmAnim', d => window.__a.push(d.name)); NR.player.place(new THREE.Vector3(0.5,0,-5),0.15,0.02)"); pg.wait_for_timeout(600)
        vis = "(() => { const d = x => getComputedStyle(document.querySelector(x)).display; return { drawn: NR.player.drawn, fire: d('#nrc .fire'), gun: d('#nrc .gun'), pips: d('#nru .cyl'), cig: NR.player.vm.scene.children.some(c => c.visible && c !== null) }; })()"
        r["holstered_default"] = pg.evaluate(vis)
        pg.screenshot(path=str(OUT / "hol_holstered.png")); shots.append(("Holstered (default): cigarette hand, GUN button", "hol_holstered.png"))
        r0 = pg.evaluate("NR.player.rounds"); pg.evaluate("NR.controls.inject = { fire: true }"); pg.wait_for_timeout(500); pg.evaluate("NR.controls.inject.fire = false")
        r["fire_while_holstered_rounds_unchanged"] = pg.evaluate("NR.player.rounds") == r0
        L = pg.evaluate("(() => { const L = NR.controls.touchLayout, v = NR.core.view; return [v.left + L.gx, v.top + L.gy]; })()")
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": L[0], "y": L[1], "id": 5}]}); pg.wait_for_timeout(60); cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        pg.wait_for_timeout(200); r["mid_draw"] = pg.evaluate("[NR.player.drawn, +NR.player.drawT.toFixed(2)]")
        pg.wait_for_timeout(600); r["drawn"] = pg.evaluate(vis)
        pg.screenshot(path=str(OUT / "hol_drawn.png")); shots.append(("GUN tapped: pistol drawn, FIRE + ammo shown", "hol_drawn.png"))
        pg.keyboard.press("KeyG"); pg.wait_for_timeout(700); r["key_G_holsters"] = not pg.evaluate("NR.player.drawn")
        pg.keyboard.press("Digit1"); pg.wait_for_timeout(700); r["key_1_draws"] = pg.evaluate("NR.player.drawn")
        r["vm_anim_calls"] = pg.evaluate("window.__a")
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (2 * (W + 12) + 12, H + 96), (14, 13, 12)); d = ImageDraw.Draw(img)
f1, fb = ImageFont.truetype("arial.ttf", 17), ImageFont.truetype("arialbd.ttf", 22)
d.text((12, 14), "Holster / draw (GUN button)", fill=(234, 223, 202), font=fb)
for i, (lab, fn) in enumerate(shots):
    x = 12 + i * (W + 12); img.paste(Image.open(OUT / fn).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), lab, fill=(232, 176, 64), font=f1)
img.save(OUT / "holster_states.png"); print(json.dumps(r)); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
