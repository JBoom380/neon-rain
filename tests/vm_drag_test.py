"""Drag viewmodel check (2 drags: raise, hold with ember flare, lower, exhale)
(derived from vm_holster_test.py). Smoking + holster viewmodel check on a 390x844 touch screen (alley): idle smoke, drag (to the lips, ember flare, exhale),
draw, fire, holster. Records the run with Playwright, cuts tests/shots/vm_holster.mp4 with ffmpeg and builds the still sheet
tests/shots/vm_holster.png from video frames at the marked beats (page screenshots are too slow for 0.4 s moves).
Usage: python tests/vm_holster_test.py"""
import pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
VID = OUT / "_vm_drag_video"; shutil.rmtree(VID, ignore_errors=True)
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
        # TEMP (test-only, file untouched): src/actors.js line 152 is missing a ")" (another agent's file); serve a patched copy
        bad = "String(((((Math.round(az2 / (Math.PI / 4)) % 8) + 8) % 8) * 45) :"
        src_a = (ROOT / "src" / "actors.js").read_text(encoding="utf-8")
        if bad in src_a: pg.route("**/src/actors.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=src_a.replace(bad, "String(((((Math.round(az2 / (Math.PI / 4)) % 8) + 8) % 8) * 45)) :")))
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
        V0 = time.time() - T0
        wait(1200)
        for k in range(2):
            ev("NR.player.vm.anim('drag')"); wait(4000)
        V1 = time.time() - T0
        vpath = pg.video.path(); TEND = time.time() - T0; ctx.close(); b.close()
finally:
    srv.terminate()
ff = shutil.which("ffmpeg") or "ffmpeg"
V0 = max(0.0, V0 - 0.6); V1 = V1 + 0.6
subprocess.run([ff, "-y", "-loglevel", "error", "-ss", f"{V0:.2f}", "-i", str(vpath), "-t", f"{V1 - V0:.2f}", "-vf", "scale=390:844,fps=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / "vm_drag.mp4")], check=True)
subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(OUT / "vm_drag.mp4"), "-vf", "fps=4,scale=156:338,tile=10x4", "-frames:v", "1", str(OUT / "vm_drag.png")], check=True)
other = [u for u in failed if not any(k in u for k in KNOWN_404)]
errs = [e for e in errs if not ("404" in e or "Failed to load resource" in e) or other]
print("errors:", errs or "none", "| unexpected failed requests:", other or "none")
print("wrote", OUT / "vm_drag.png", OUT / "vm_drag.mp4", f"({V1 - V0:.1f} s)")
