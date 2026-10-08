"""Shimmer check for Vela's full-length video at the player's start view (390x844, game render scale).
The clip is paused on one frame and the camera strafes 2 mm per frame for 16 frames; the figure is sampled from the
game canvas each step. Shimmer = mean frame-to-frame change of the high-pass detail inside her box, after the box
follows her on screen. Run for the 1280 px texture and the 640 px tier. Usage: python tests/vela_shimmer_test.py"""
import json, pathlib, socket, subprocess, sys, time, base64, io
import numpy as np, cv2
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
STAGE = (ROOT / "tests" / "vela_start_view.py").read_text(encoding="utf-8").split('pg.evaluate("""', 1)[1].split('""")', 1)[0]
GRAB = """(tier) => new Promise(res => { NR.vperf.forceTier = tier; const v = window.__vela, P = NR.player; const out = []; let k = 0;
  const vids = Object.values(NR.vperf.vids); const step = () => {
    for (const c of vids) if (!c.v.paused) c.v.pause();
    const c = NR.core.renderer.domElement, cam = NR.core.camera, w = c.width, h = c.height;
    // her box on the canvas: project feet and hair top
    const top = new THREE.Vector3(v.pos.x, 1.82, v.pos.z).project(cam), bot = new THREE.Vector3(v.pos.x, 0.0, v.pos.z).project(cam);
    const cx = (top.x * 0.5 + 0.5) * w, y0 = (1 - (top.y * 0.5 + 0.5)) * h, y1 = (1 - (bot.y * 0.5 + 0.5)) * h, bw = (y1 - y0) * 0.42;
    out.push({ url: c.toDataURL('image/png'), box: [cx - bw / 2, y0, bw, y1 - y0] });
    if (++k < 17) { P.pos.x += 0.002; requestAnimationFrame(() => requestAnimationFrame(step)); } else res({ out, shown: v.perf.shown, clip: v.perf.cur && v.perf.cur.name, tex: v.perf.cur && v.perf.cur.v.videoWidth + 'x' + v.perf.cur.v.videoHeight }); };
  setTimeout(step, 2500); })"""


def shimmer(res):
    crops = []
    for o in res["out"]:
        im = Image.open(io.BytesIO(base64.b64decode(o["url"].split(",")[1]))).convert("L")
        x, y, w, h = o["box"]; c = np.asarray(im.crop((round(x), round(y), round(x + w), round(y + h))).resize((160, 400), Image.BILINEAR), np.float32)
        hp = c - cv2.GaussianBlur(c, (0, 0), 2)
        crops.append(hp)
    d = [np.abs(crops[i] - crops[i - 1]).mean() for i in range(1, len(crops))]
    return round(float(np.mean(d)), 3), round(float(np.std([c.std() for c in crops])), 3), round(float(np.mean([c.std() for c in crops])), 3)


report = {}
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True)
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true", timeout=120000)
        pg.wait_for_timeout(600); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(600)
        pg.evaluate(STAGE); pg.wait_for_function("window.__arrived === true", timeout=60000)
        pg.evaluate("""(() => { const P = NR.player, v = window.__vela, e = P.eye(); const dx = v.pos.x - e.x, dz = v.pos.z - e.z; P.yaw = Math.atan2(-dx, -dz); P.pitch = Math.atan2(1.2 - e.y, Math.hypot(dx, dz)); })()""")
        report["render_px"] = pg.evaluate("NR.core.renderer.domElement.width + 'x' + NR.core.renderer.domElement.height")
        for tier in ("big", "small"):
            pg.evaluate("NR.player.place(new THREE.Vector3(0, 0, 1.6), NR.player.yaw, NR.player.pitch)")
            r = pg.evaluate(GRAB, tier)
            m = shimmer(r)
            report[tier] = {"clip": r["clip"], "tex": r["tex"], "shown": r["shown"], "shimmer": m[0], "detail_std": m[2], "detail_var_over_steps": m[1]}
        pg.evaluate("NR.vperf.forceTier = null")
        b.close()
finally:
    srv.terminate()
print(json.dumps(report, indent=1))
(ROOT / "tests" / "shots" / "vela_shimmer.json").write_text(json.dumps(report, indent=1))
