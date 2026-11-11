"""Probe the doorway colour cast on Vela: the same doorway view with variants (normal, no fog on her, painted only) -> tests/shots/vela_tint_probe.png"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
VARS = sys.argv[1:] or ["normal", "nofog", "vpoff"]
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"])
        shots = []
        for v in VARS:
            pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True)
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html" + ("?vp=off" if v == "vpoff" else "")); pg.wait_for_function("window.READY === true", timeout=120000)
            pg.wait_for_timeout(600); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(600)
            pg.evaluate("""(async () => { const G = NR.game, A = NR.actors, P = NR.player, V3 = (x, y, z) => new THREE.Vector3(x, y, z);
              NR.ui.show('title', false); G.titleCam = false; NR.core.fx.fade = 0;
              const L = G.load('office'); await NR.env.ready.office; P.place(L.spawn.pos, 0.35, 0.05);
              const vela = await A.character('vela', L, V3(-1.0, 0, -6.1), 0); G.chars.push(vela); window.__vela = vela;
              if (L.door) L.door.rotation.y = 1.15; G.beat = 'office_play'; NR.core.setState('PLAY');
              const e = P.eye(), dx = vela.pos.x - e.x, dz = vela.pos.z - e.z; P.yaw = Math.atan2(-dx, -dz); P.pitch = Math.atan2(1.1 - e.y, Math.hypot(dx, dz)); window.__ok = true; })()""")
            pg.wait_for_function("window.__ok === true", timeout=60000); pg.wait_for_timeout(2500)
            if v == "nofog": pg.evaluate("(() => { const v = window.__vela; v.mat.uniforms.fogD.value = 0; if (v.perf) v.perf.u.fogD = { value: 0 }; })()"); pg.wait_for_timeout(300)
            st = pg.evaluate("(() => { const v = window.__vela; return { shown: !!(v.perf && v.perf.shown), clip: v.perf && v.perf.cur && v.perf.cur.name, fogD: v.mat.uniforms.fogD.value, fogC: v.mat.uniforms.fogC.value.getHexString(), amb: v.mat.uniforms.ambient.value.getHexString() }; })()")
            f = OUT / f"_tint_{v}.png"; pg.screenshot(path=str(f), clip={"x": 120, "y": 330, "width": 150, "height": 250}); shots.append(f); print(v, st); pg.close()
        b.close()
    W = Image.new("RGB", (150 * len(shots) * 2, 500))
    for i, f in enumerate(shots): W.paste(Image.open(f).resize((300, 500)), (300 * i, 0)); f.unlink()
    W.save(OUT / "vela_tint_probe.png"); print("ok")
finally:
    srv.terminate()
