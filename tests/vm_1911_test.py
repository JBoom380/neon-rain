"""1911 viewmodel check on a 390x844 touch screen (alley): idle, fire with the casing in the air, slide locked on the last
round, reload mid-swap -> tests/shots/vm_1911.png; then fire x3, empty lock, reload recorded -> tests/shots/vm_1911.mp4 (5 s).
Shots go through the real weapon logic (NR.controls.inject fire, P.reload). Usage: python tests/vm_1911_test.py"""
import pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
VID = OUT / "_vm_video"; shutil.rmtree(VID, ignore_errors=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
errs, shots = [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True,
                            record_video_dir=str(VID), record_video_size={"width": 390, "height": 844})
        pg = ctx.new_page(); T0 = time.time()
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: (m.type == "error" or "[vm" in m.text) and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=alley"); pg.wait_for_function("window.READY === true", timeout=30000)
        ev = pg.evaluate; wait = pg.wait_for_timeout
        wait(1500); pg.touchscreen.tap(195, 500); wait(1200)
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
            wait(200)
        pg.wait_for_function("NR.player.vmGLB === true", timeout=20000)
        ev("NR.player.god = true; NR.player.yaw = 0.0; NR.player.pitch = -0.04; NR.controls.inject = NR.controls.inject || { mx: 0, my: 0, lookX: 0, lookY: 0, fire: false }")
        def fire():
            ev("NR.controls.inject.fire = true"); wait(50); ev("NR.controls.inject.fire = false")
        def shot(name, label):
            f = OUT / f"vm1911_{name}.png"; pg.screenshot(path=str(f)); shots.append((label, f))
        # ---- stills
        wait(800); shot("idle", "Idle")
        ev("NR.player.rounds = 3; NR.player.slideLock = false; NR.player.reloadT = 0")
        ev("NR.controls.inject.fire = true"); pg.wait_for_function("NR.player.rounds < 3", timeout=3000, polling=8); ev("NR.controls.inject.fire = false")
        for k in range(4):
            wait(45); pg.screenshot(path=str(OUT / f"vm1911_fire_{k}.png"))
        shots.append(("Fire: slide back, casing out", OUT / "vm1911_fire_1.png"))
        wait(450); fire(); wait(450); fire(); wait(400)
        shot("locked", "Last round: slide locked")
        ev("NR.player.reload()")
        pg.wait_for_function("NR.player.reloadT > 0 && 1 - NR.player.reloadT / NR.player.reloadDur >= 0.56", timeout=5000, polling=16)
        shot("reload", "Reload: new magazine going in")
        pg.wait_for_function("NR.player.reloadT <= 0", timeout=5000); wait(600)
        # ---- video pass: fire x3, empty lock, reload
        ev("NR.player.rounds = 3; NR.player.slideLock = false"); wait(700)
        V0 = time.time() - T0
        for k in range(3): fire(); wait(430)
        wait(350); ev("NR.player.reload()"); wait(2400)
        V1 = time.time() - T0
        print("rounds after:", ev("NR.player.rounds"), "slideLock:", ev("NR.player.slideLock"))
        vpath = pg.video.path(); ctx.close(); b.close()
finally:
    srv.terminate()
W, H = 390 * 2, 844 * 2
sheet = Image.new("RGB", (W * len(shots) // 2, H // 2 + 30), "black"); d = ImageDraw.Draw(sheet)
for i, (label, f) in enumerate(shots):
    sheet.paste(Image.open(f).convert("RGB").resize((W // 2, H // 2)), (i * W // 2, 30)); d.text((i * W // 2 + 8, 8), label, fill="white")
sheet.save(OUT / "vm_1911.png")
ff = shutil.which("ffmpeg") or "ffmpeg"
start = max(0.0, V0 - 0.3); dur = min(5.0, V1 - V0 + 0.3)
subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(vpath), "-t", f"{dur:.2f}", "-vf", "scale=390:844,fps=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / "vm_1911.mp4")], check=True)
# fire still with the casing in the air: screenshots are too slow on this machine for a 0.75 s casing, so take the frame two
# frames after the brightest muzzle-flash frame of the first video shot
fr = OUT / "_vm_frames"; shutil.rmtree(fr, ignore_errors=True); fr.mkdir()
subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(OUT / "vm_1911.mp4"), "-t", "1.2", str(fr / "f_%03d.png")], check=True)
frames = sorted(fr.glob("f_*.png")); lum = [sum(Image.open(f).convert("L").crop((120, 250, 330, 500)).getdata()) for f in frames]
k = min(len(frames) - 1, lum.index(max(lum)) + 2)
big = Image.open(frames[k]).convert("RGB").resize((W // 2, H // 2)); sheet = Image.open(OUT / "vm_1911.png")
idx = [i for i, (lb, _) in enumerate(shots) if lb.startswith("Fire")][0]; sheet.paste(big, (idx * W // 2, 30)); sheet.save(OUT / "vm_1911.png")
shutil.rmtree(fr, ignore_errors=True)
print("errors:", errs or "none"); print("wrote", OUT / "vm_1911.png", OUT / "vm_1911.mp4", f"(video {start:.1f}s +{dur:.1f}s)")
