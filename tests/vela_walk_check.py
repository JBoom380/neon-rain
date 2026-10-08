"""Vela walk-in check on 390x844 touch: the real office beat, recorded twice with Playwright video:
(1) from Harrow's chair (the player's view), (2) from a 3/4 side spot by the window. Each clip runs from the first walk
frame to 2.5 s after she settles into her idle, cut, captioned and joined into tests/shots/vela_walk_v1.mp4 (30 fps).
Also logs per-frame sprite state (mode, sector, frame, position) to tests/shots/vela_walk_v1.json.
Usage: python tests/vela_walk_check.py [out_name]"""
import json, pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"; TMP = OUT / "_vwalk"
NAME = sys.argv[1] if len(sys.argv) > 1 else "vela_walk_v1"
shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
clips, errs, logs = [], [], {}

def click_through(pg):
    for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
        if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); return

def until(pg, cond, limit=90, clicks=True):
    t0 = time.time()
    while time.time() - t0 < limit:
        if pg.evaluate(cond): return True
        if clicks and pg.evaluate("NR.core.state") == "CUTSCENE": click_through(pg)
        pg.wait_for_timeout(100)
    return False

VELA = "NR.game.chars.find(c => c.who === 'vela')"
def session(b, name, side):
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True, is_mobile=True,
                        record_video_dir=str(TMP / name), record_video_size={"width": 390, "height": 844})
    pg = ctx.new_page(); t0 = time.time()
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true")
    pg.wait_for_timeout(600); pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
    until(pg, f"!!({VELA})", 120)
    if side:  # watch from by the window, off her right side
        pg.evaluate("NR.player.place(new THREE.Vector3(1.2, 0, -2.9), 0, 0)")
    # hold the dialogue that follows her arrival so the idle shows; log the sprite state every frame
    pg.evaluate(f"""(() => {{ const v = {VELA}; window.__log = []; const t0 = performance.now();
      const tick = () => {{ window.__log.push([+(performance.now() - t0).toFixed(1), v.mode || (v.walking ? 'walk' : 'idle'), v.sector, v.frame, +v.pos.x.toFixed(3), +v.pos.z.toFixed(3), v.clip ? v.clip.f : -1]);
        if (window.__log.length < 4000) requestAnimationFrame(tick); }}; requestAnimationFrame(tick); }})()""")
    until(pg, f"({VELA}).mode === 'walk' || ({VELA}).walking", 120)
    a = time.time() - t0 - 0.4
    if side: pg.evaluate("NR.player.place(new THREE.Vector3(1.2, 0, -2.9), 0, 0)")
    until(pg, f"({VELA}).mode === 'idle' && !({VELA}).path", 40, clicks=False)
    pg.wait_for_timeout(2500); e = time.time() - t0
    logs[name] = pg.evaluate("window.__log")
    path = pg.video.path(); ctx.close()
    clips.append((("1 Player view: Vela walks in" if not side else "2 Three-quarter side view"), str(path), a, e - a))

try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        session(b, "player", False)
        session(b, "side", True)
        b.close()
finally:
    srv.terminate()
parts = []; font = "C\\:/Windows/Fonts/arialbd.ttf"
for i, (label, src, a, dur) in enumerate(clips):
    out = TMP / f"part{i}.mp4"; txt = label.replace(":", "\\:")
    vf = f"fps=30,scale=390:844,drawbox=x=0:y=ih-44:w=iw:h=44:color=black@0.6:t=fill,drawtext=fontfile='{font}':text='{txt}':x=10:y=h-30:fontsize=16:fontcolor=0xF0C060"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, a):.2f}", "-t", f"{dur:.2f}", "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)], check=True)
    parts.append(out)
lst = TMP / "list.txt"; lst.write_text("".join(f"file '{p_.as_posix()}'\n" for p_ in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(OUT / f"{NAME}.mp4")], check=True)
json.dump(logs, open(OUT / f"{NAME}.json", "w"))
print("clips", [(c[0], round(c[2], 1), round(c[3], 1)) for c in clips]); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
print("wrote", OUT / f"{NAME}.mp4")
