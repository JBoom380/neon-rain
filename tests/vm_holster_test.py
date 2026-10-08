"""Smoking + holster viewmodel check on a 390x844 touch screen (alley): idle smoke, drag (to the lips, ember flare, exhale),
draw, fire, holster. Records the run with Playwright, cuts tests/shots/vm_holster.mp4 with ffmpeg and builds the still sheet
tests/shots/vm_holster.png from video frames at the marked beats (page screenshots are too slow for 0.4 s moves).
Usage: python tests/vm_holster_test.py"""
import pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
VID = OUT / "_vm_holster_video"; shutil.rmtree(VID, ignore_errors=True)
KNOWN_404 = ("assets/video/", "vela_walk.json")
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
errs, marks, failed = [], [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True,
                            record_video_dir=str(VID), record_video_size={"width": 390, "height": 844})
        pg = ctx.new_page(); T0 = time.time()
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.on("requestfailed", lambda r: failed.append(r.url))
        pg.on("response", lambda r: r.status >= 400 and failed.append(f"{r.status} {r.url}"))
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
        if ev("NR.player.drawn"): ev("NR.player.vm.anim('holster')"); wait(800)
        ev("NR.player.vm.anim('idleSmoke')"); wait(2000)
        def mark(label, dt=0.0): marks.append((label, time.time() - T0 + dt))
        draw = "NR.player.toggleGun ? NR.player.toggleGun() : NR.player.vm.anim('draw')"
        V0 = time.time() - T0
        wait(900); mark("Idle: lit cigarette, smoke curl"); wait(600)
        ev("NR.player.vm.anim('drag')"); wait(750); mark("Drag: to the lips, ember flares"); wait(1150); mark("Exhale"); wait(1700)
        ev(draw); wait(150); mark("Draw (0.45 s)"); wait(700)
        busy = ev("[NR.player.vm.drawn, NR.player.vm.busy]")
        TFIRE = time.time() - T0; ev("NR.controls.inject.fire = true"); wait(60); ev("NR.controls.inject.fire = false"); wait(30); mark("Drawn + fire, cigarette at the edge"); wait(500)
        ev("NR.controls.inject.fire = true"); wait(60); ev("NR.controls.inject.fire = false"); wait(700)
        ev(draw); wait(170); mark("Holster (0.4 s)"); wait(900)
        V1 = time.time() - T0
        print("drawn/busy after draw:", busy, "| after holster:", ev("[NR.player.vm.drawn, NR.player.vm.busy, NR.player.drawn]"))
        vpath = pg.video.path(); TEND = time.time() - T0; ctx.close(); b.close()
finally:
    srv.terminate()
ff = shutil.which("ffmpeg") or "ffmpeg"
# align wall-clock marks with the video: find the first muzzle flash (brightest frame in the muzzle region) and match it to TFIRE
import numpy as np
raw = subprocess.run([ff, "-loglevel", "error", "-i", str(vpath), "-vf", "fps=30,crop=120:180:220:300,scale=12:18,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
lum = np.frombuffer(raw, np.uint8).reshape(-1, 12 * 18).mean(1); fps = 30.0
lo = int(max(0, (TFIRE - 2.5)) * fps); hi = min(len(lum), int((TFIRE + 2.5) * fps))
d = np.diff(lum[lo:hi]); kf = lo + 1 + int(np.argmax(d))  # sharpest brightness jump = flash onset
LAG = TFIRE - kf / fps; V0 -= LAG; V1 -= LAG; marks = [(lb, t - LAG) for lb, t in marks]; print(f"video offset {-LAG:+.2f} s")
subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{V0:.2f}", "-i", str(vpath), "-t", f"{V1 - V0:.2f}", "-vf", "scale=390:844,fps=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / "vm_holster.mp4")], check=True)
W, H = 390, 844
sheet = Image.new("RGB", (W * len(marks), H + 30), "black"); d = ImageDraw.Draw(sheet)
for i, (label, t) in enumerate(marks):
    f = OUT / f"_vmh_{i}.png"
    subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(vpath), "-frames:v", "1", str(f)], check=True)
    sheet.paste(Image.open(f).convert("RGB").resize((W, H)), (i * W, 30)); d.text((i * W + 8, 8), label, fill="white"); f.unlink()
sheet.save(OUT / "vm_holster.png")
other = [u for u in failed if not any(k in u for k in KNOWN_404)]
errs = [e for e in errs if not ("404" in e or "Failed to load resource" in e) or other]
print("errors:", errs or "none", "| unexpected failed requests:", other or "none")
print("wrote", OUT / "vm_holster.png", OUT / "vm_holster.mp4", f"({V1 - V0:.1f} s)")
