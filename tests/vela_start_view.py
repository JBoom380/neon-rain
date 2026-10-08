"""Vela in the office seen from the player's start position (the view from John's phone), 390x844.
Plays the real office beat up to her mark (UI fast), then hands control back and aims at her from the spawn point.
Writes tests/shots/vela_start_view_{0..3}.png + vela_start_view.png (strip). Usage: python tests/vela_start_view.py [--built] [--webkit]"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
PAGE = "index.html" if "--built" in sys.argv else "src/dev.html"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8); errors = []
try:
    with sync_playwright() as p:
        eng = p.webkit if "--webkit" in sys.argv else p.chromium
        b = eng.launch(**({} if "--webkit" in sys.argv else {"args": ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"]}))
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True)
        pg.on("pageerror", lambda e: errors.append(str(e))); pg.on("console", lambda m: m.type == "error" and errors.append(m.text[:6000]))
        pg.goto(f"http://127.0.0.1:{PORT}/{PAGE}"); pg.wait_for_function("window.READY === true", timeout=120000)
        pg.wait_for_timeout(600); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(600)
        pg.evaluate("""(async () => { const G = NR.game, A = NR.actors, P = NR.player, V3 = (x, y, z) => new THREE.Vector3(x, y, z);
          NR.ui.show('title', false); G.titleCam = false; NR.core.fx.fade = 0;
          const L = G.load('office'); await NR.env.ready.office; P.place(L.spawn.pos, 0.35, 0.05);
          const vela = await A.character('vela', L, V3(-1.0, 0, -6.1), 0); G.chars.push(vela); window.__vela = vela;
          const d = L.boxes.indexOf(L.doorCol); if (d >= 0) L.boxes.splice(d, 1); if (L.door) L.door.rotation.y = 1.15;
          G.beat = 'office_play'; NR.core.setState('PLAY');
          await vela.walkTo([V3(-1.0, 0, -4.2), V3(-1.5, 0, -2.4), V3(-1.5, 0, -0.65)], 1.0); vela.faceTo(P.pos); window.__arrived = true; })()""")
        pg.wait_for_function("window.__arrived === true", timeout=60000)
        info = pg.evaluate("""(() => { const P = NR.player, v = window.__vela, e = P.eye(); const dx = v.pos.x - e.x, dz = v.pos.z - e.z;
          P.yaw = Math.atan2(-dx, -dz); P.pitch = Math.atan2(1.2 - e.y, Math.hypot(dx, dz)); return { spawn: [+e.x.toFixed(2), +e.z.toFixed(2)], vela: [v.pos.x, v.pos.z], cls: v.constructor.name, fov: NR.core.camera.fov }; })()""")
        shots = []
        for k in range(4):
            pg.wait_for_timeout(900)
            st = pg.evaluate("(() => { const v = window.__vela, p = v.perf; return { shown: !!(p && p.shown), clip: p && p.cur && p.cur.name, painted: !!v._ps, map: (v.mat.uniforms.map.value && v.mat.uniforms.map.value.image && (v.mat.uniforms.map.value.image.currentSrc || v.mat.uniforms.map.value.image.src || '').split('/').pop()) || null, fps: Math.round(NR.core.fps) }; })()")
            f = OUT / f"vela_start_view_{k}.png"; pg.screenshot(path=str(f)); shots.append(f); print(k, st)
        print(info); b.close()
        ims = [Image.open(f).convert("RGB").resize((390, 844)) for f in shots]
        strip = Image.new("RGB", (390 * 4, 844)); [strip.paste(im, (390 * i, 0)) for i, im in enumerate(ims)]; strip.save(OUT / "vela_start_view.png")
finally:
    srv.terminate()
print("ERRORS", len(errors), errors[:5])
