"""Vela walk check: in the club, she walks toward the camera then across; 8 frames each -> tests/shots/vela_walk_sheet.png"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True, is_mobile=True)
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=clubfight"); pg.wait_for_function("window.READY === true")
        pg.wait_for_timeout(500); pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        pg.wait_for_function("NR.game.beat === 'club_fight'", timeout=30000)
        pg.evaluate("""(() => { NR.actors.clear(); NR.core.setState('CUTSCENE'); NR.player.place(new THREE.Vector3(0, 0, -4), 0, -0.12);
          const v = new NR.actors.Painted('vela', NR.game.level, new THREE.Vector3(0.2, 0, -10), 0); NR.game.chars.push(v); window.__v = v;
          v.walkTo([new THREE.Vector3(0.2, 0, -6.5)], 1.0).then(() => v.walkTo([new THREE.Vector3(2.4, 0, -6.5)], 1.0)); })()""")
        rows = []
        for phase in range(2):
            pg.wait_for_timeout(700 if phase == 0 else 2400)
            fr = []
            for k in range(8):
                f = OUT / f"vw_{phase}_{k}.png"; pg.screenshot(path=str(f), clip={"x": 90 + phase * 90, "y": 200, "width": 210, "height": 420}); fr.append(f); pg.wait_for_timeout(90)
            rows.append(fr)
        b.close()
    W = Image.new("RGB", (8 * 210, 2 * 420))
    for r, fr in enumerate(rows):
        for k, f in enumerate(fr): W.paste(Image.open(f), (k * 210, r * 420)); f.unlink()
    W.save(OUT / "vela_walk_sheet.png"); print("ok")
finally:
    srv.terminate()
