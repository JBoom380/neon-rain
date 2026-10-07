"""Viewmodel check on a 390x844 touch screen: the modelled revolver in the gloved hand (idle, reload with the cylinder
swung out) and the cigarette hand, in the alley. Writes tests/shots/vm_pass_v1.png (side by side). Usage: python tests/vm_test.py"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
errs, shots = [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: m.type in ("error", "warning") and "[vm" in m.text and errs.append(m.text) or (m.type == "error" and errs.append(m.text)))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=alley"); pg.wait_for_function("window.READY === true", timeout=30000)
        ev = pg.evaluate
        pg.wait_for_timeout(1500); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(1200)
        def center(sel):
            return ev(f"(() => {{ const e = document.querySelector('{sel}'); if (!e) return null; const b = e.getBoundingClientRect(); return b.width ? [b.x + b.width/2, b.y + b.height/2] : null; }})()")
        c = center("#nru .title .btn.red")
        if c: pg.touchscreen.tap(*c)
        t0 = time.time()
        while time.time() - t0 < 90:
            if ev("NR.game.beat === 'alley_play' && NR.core.state === 'PLAY'"): break
            for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
                c = center(sel)
                if c: pg.touchscreen.tap(*c); break
            pg.wait_for_timeout(200)
        pg.wait_for_function("NR.player.vmGLB === true", timeout=20000)
        ev("NR.player.god = true; NR.player.yaw = 0.0; NR.player.pitch = -0.05")
        pg.wait_for_timeout(800)
        def shot(name, label):
            f = OUT / f"vm_{name}.png"; pg.screenshot(path=str(f)); shots.append((label, f))
        shot("gun", "Revolver in the right hand (alley)")
        import os
        if os.environ.get("VMDBG"):
            ev("NR.player.vm.scene.getObjectByName('sleeve_r').visible = false"); pg.wait_for_timeout(200); shot("dbg_nosleeve", "no sleeve")
            ev("NR.player.vm.scene.getObjectByName('sleeve_r').visible = true")
            print(ev("JSON.stringify(NR.player.vm.scene.children.map(c => [c.type, c.name, c.visible, c.children.length]))"))
        ev("NR.player.reloadT = NR.cfg.GUN_RELOAD * 0.5"); pg.wait_for_timeout(120); ev("NR.player.reloadT = NR.cfg.GUN_RELOAD * 0.5"); pg.wait_for_timeout(30)
        shot("reload", "Reload: cylinder swung out")
        pg.wait_for_timeout(1200)
        ev("NR.player.forceCig = true; NR.player.armed = false"); pg.wait_for_timeout(1500)
        shot("cig", "Cigarette hand")
        ev("NR.player.setLeftHand('cup')"); pg.wait_for_timeout(300); shot("cup", "Left hand cupped (match)")
        ev("NR.player.setLeftHand('relax')"); pg.wait_for_timeout(300); shot("relax", "Left hand relaxed")
        ev("NR.player.setLeftHand('cig')")
        ev("NR.core.settings.bw = false; NR.player.armed = true"); pg.wait_for_timeout(600)
        shot("color", "Both hands, colour grade")
        b.close()
finally:
    srv.terminate()
W, H = 390 * 2, 844 * 2
sheet = Image.new("RGB", (W * len(shots) // 2, H // 2 + 30), "black"); d = ImageDraw.Draw(sheet)
for i, (label, f) in enumerate(shots):
    sheet.paste(Image.open(f).convert("RGB").resize((W // 2, H // 2)), (i * W // 2, 30)); d.text((i * W // 2 + 8, 8), label, fill="white")
sheet.save(OUT / "vm_pass_v1.png")
print("errors:", errs or "none"); print("wrote", OUT / "vm_pass_v1.png")
