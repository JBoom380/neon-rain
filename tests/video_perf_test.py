"""Video-performance test, 390x844 portrait.
Chromium (VP9 + alpha path): office with Vela's video performances (stole entrance, idle, talk, smoke) on her billboard in the
framed close-up, the open-lens fallback to the painted angles, a side view (video hidden), then the club with Dolores and the
interrogation close-up (warm / guarded / cold loops). Records the session to tests/shots/video_perf_v1.mp4 and writes a contact
sheet tests/shots/video_perf_v1.png. WebKit (iOS path: H.264 with stacked alpha): checks the mode, playback and render.
Usage: python tests/video_perf_test.py [--built] [--no-webkit]"""
import json, pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
TMP = OUT / "_vp_tmp"; shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir()
PAGE = "index.html" if "--built" in sys.argv else "src/dev.html"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)

FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(); const t0 = last, f0 = NR.core.frame;
  const done = () => { const n = NR.core.frame - f0, secs = (performance.now() - t0) / 1000; t.sort((a,b)=>a-b);
    r({ fps: +(n / secs).toFixed(1), p95ms: t.length ? +t[Math.floor(t.length*0.95)].toFixed(1) : null, frames: n, secs: +secs.toFixed(1) }); };
  function f(now) { t.push(now - last); last = now; if (t.length < 150 && now - t0 < 6000) requestAnimationFrame(f); else done(); }
  requestAnimationFrame(f); setTimeout(() => { if (t.length < 150) done(); }, 8000); })"""
STAGE_OFFICE = """async () => {
  const G = NR.game, A = NR.actors, P = NR.player, V3 = (x, y, z) => new THREE.Vector3(x, y, z);
  NR.ui.show('title', false); G.titleCam = false; NR.core.fx.fade = 0;
  const L = G.load('office'); await NR.env.ready.office;
  P.place(L.spawn.pos, 0.35, 0.05);
  const vela = await A.character('vela', L, V3(-1.5, 0, -0.65), 0); G.chars.push(vela); vela.faceTo(P.pos); window.__vela = vela;
  G.beat = 'office_talk'; NR.core.setState('CUTSCENE'); G.lookTarget = () => V3(vela.pos.x, 1.55, vela.pos.z); G.lookRate = 4;
  return { mode: NR.vperf.MODE, dist: +Math.hypot(P.pos.x - vela.pos.x, P.pos.z - vela.pos.z).toFixed(2) };
}"""
STATE = """() => { const v = window.__vela || window.__dol; const p = v && v.perf; return { mode: NR.vperf.MODE, fov: +NR.core.camera.fov.toFixed(1), shown: !!(p && p.shown),
  clip: p && p.cur && p.cur.name, stole: !!(p && p.stoleDone), vids: NR.vperf.stats(), panel: NR.vperf.panelState ? NR.vperf.panelState() : null, beat: NR.game.beat }; }"""
STAGE_CLUB = """async () => {
  const G = NR.game, A = NR.actors, P = NR.player, V3 = (x, y, z) => new THREE.Vector3(x, y, z);
  NR.ui.say && document.querySelector('#nru .dlg') && document.querySelector('#nru .dlg').classList.remove('on');
  const L = G.load('club'); await NR.env.ready.club;
  const dp = L.doloresPos; const dir = V3(dp.x, 0, dp.z).sub(V3(-1.5, 0, -19)).normalize();
  const dol = new A.Painted('dolores', L, dp, 0); G.chars.push(dol); window.__dol = dol; window.__vela = null;
  P.place(V3(dp.x + 2.0, 0, dp.z + 0.6), 0, 0); dol.faceTo(P.pos);
  G.beat = 'club_meet'; NR.core.setState('CUTSCENE'); G.lookTarget = () => V3(dol.pos.x, 1.6, dol.pos.z); G.lookRate = 4; void dir;
  return { pos: [dp.x, dp.z] };
}"""

errors = []
shots = []


def snap(pg, name, label):
    p = TMP / f"{name}.png"; pg.screenshot(path=str(p)); shots.append((p, label)); return p


def hook(pg, tag):
    pg.on("pageerror", lambda e: errors.append(f"{tag} PAGEERROR {e}"))
    pg.on("console", lambda m: m.type == "error" and errors.append(f"{tag} console.error {m.text[:300]}"))


report = {}
try:
    with sync_playwright() as p:
        # ------------------------------------------------------------ Chromium: VP9 alpha path, recorded
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True,
                            record_video_dir=str(TMP), record_video_size={"width": 390, "height": 844})
        pg = ctx.new_page(); hook(pg, "chromium")
        pg.goto(f"http://127.0.0.1:{PORT}/{PAGE}"); pg.wait_for_function("window.READY === true")
        pg.wait_for_timeout(600); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(600)
        report["office"] = pg.evaluate(STAGE_OFFICE)
        pg.wait_for_function("NR.core.camera.fov < 34", timeout=15000)
        pg.wait_for_timeout(1200); snap(pg, "01_stole_a", "ARRIVAL: STOLE (0.5 s)")
        pg.wait_for_timeout(1500); snap(pg, "02_stole_b", "ARRIVAL: STOLE (2 s)")
        report["stole_state"] = pg.evaluate(STATE)
        pg.wait_for_function("window.__vela.perf && (window.__vela.perf.stoleDone || !NR.vperf.AVAIL.has('vela_stole'))", timeout=20000)
        pg.wait_for_timeout(1500); snap(pg, "03_idle", "IDLE LOOP (VP9 ALPHA)")
        report["idle_state"] = pg.evaluate(STATE)
        report["fps_idle"] = pg.evaluate(FPS_JS)
        pg.evaluate("void NR.ui.say('VELA', 'Mr. Harrow? The glass on your door says you find things.')")
        pg.wait_for_timeout(2500); snap(pg, "04_talk", "DIALOGUE: TALK LOOP")
        report["talk_state"] = pg.evaluate(STATE)
        pg.evaluate("document.querySelector('#nru .dlg') && document.querySelector('#nru .dlg').dispatchEvent(new PointerEvent('pointerup', {bubbles: true}))")
        pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#nru .dlg') && document.querySelector('#nru .dlg').dispatchEvent(new PointerEvent('pointerup', {bubbles: true}))")
        pg.evaluate("NR.game.beat = 'office_light'")
        pg.wait_for_timeout(2500); snap(pg, "05_smoke", "LIGHTER BEAT: DRAG + EXHALE")
        report["smoke_state"] = pg.evaluate(STATE)
        pg.evaluate("NR.game.beat = 'office_smoke'; NR.core.setState('PLAY'); NR.game.lookTarget = null;")
        pg.wait_for_timeout(2200); snap(pg, "06_open", "OPEN LENS: PAINTED FIGURE")
        report["open_state"] = pg.evaluate(STATE)
        pg.evaluate("""(() => { const v = window.__vela, V3 = (x, y, z) => new THREE.Vector3(x, y, z); NR.core.setState('CUTSCENE'); NR.game.beat = 'office_talk';
          NR.player.place(V3(v.pos.x - 2.0, 0, v.pos.z - 0.2), 0, 0); NR.game.lookTarget = () => V3(v.pos.x, 1.55, v.pos.z); })()""")
        pg.wait_for_timeout(2500); snap(pg, "07_side", "SIDE VIEW: VIDEO HIDDEN")
        report["side_state"] = pg.evaluate(STATE)
        # ------------------------------------------------------------ club: Dolores billboard + interrogation close-up
        report["club"] = pg.evaluate(STAGE_CLUB)
        pg.wait_for_timeout(3500); snap(pg, "08_dolores", "CLUB: DOLORES (VIDEO)")
        report["dolores_state"] = pg.evaluate(STATE)
        pg.evaluate("NR.core.setState('INTERRO'); window.__itg = NR.ui.interrogate('dolores', NR.story.dolores, {}); 0")
        pg.wait_for_timeout(2500); snap(pg, "09_itg_guarded", "INTERROGATION: GUARDED")
        report["panel_guarded"] = pg.evaluate("NR.vperf.panelState && NR.vperf.panelState()")
        report["fps_panel"] = pg.evaluate(FPS_JS)
        for mood in ("warm", "cold"):
            pg.evaluate(f"""(() => {{ for (const im of document.querySelectorAll('#nru .itg .pic img')) im.classList.toggle('on', /{mood}$/.test(im.alt)); }})()""")
            pg.wait_for_timeout(2200); snap(pg, f"10_itg_{mood}", f"INTERROGATION: {mood.upper()}")
            report[f"panel_{mood}"] = pg.evaluate("NR.vperf.panelState && NR.vperf.panelState()")
        pg.evaluate("NR.core.settings.film = 'bwred'")
        pg.wait_for_timeout(1200); snap(pg, "11_itg_bwred", "INTERROGATION: B&W RED")
        pg.evaluate("NR.core.settings.film = 'noir'")
        vid = pg.video.path() if pg.video else None
        ctx.close(); b.close()
        if vid:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(OUT / "video_perf_v1.mp4")], check=True)
        # ------------------------------------------------------------ WebKit: iOS path (stacked-alpha H.264)
        if "--no-webkit" not in sys.argv:
            wb = p.webkit.launch()
            wctx = wb.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True)
            wp = wctx.new_page(); hook(wp, "webkit")
            wp.goto(f"http://127.0.0.1:{PORT}/{PAGE}"); wp.wait_for_function("window.READY === true", timeout=60000)
            wp.wait_for_timeout(800); wp.touchscreen.tap(195, 500); wp.wait_for_timeout(800)
            report["webkit_ua"] = wp.evaluate("navigator.userAgent")
            report["webkit_can"] = wp.evaluate("""(() => { const v = document.createElement('video'); return { webm: v.canPlayType('video/webm; codecs="vp9"'), mp4: v.canPlayType('video/mp4; codecs="avc1.4D401E"') }; })()""")
            report["webkit_office"] = wp.evaluate(STAGE_OFFICE)
            try:
                wp.wait_for_function("NR.core.camera.fov < 34", timeout=20000)
            except Exception as e:
                errors.append(f"webkit fov never framed: {e}")
            wp.wait_for_timeout(9000)
            report["webkit_state"] = wp.evaluate(STATE)
            report["webkit_fps"] = wp.evaluate(FPS_JS)
            wp.screenshot(path=str(TMP / "12_webkit.png")); shots.append((TMP / "12_webkit.png", "WEBKIT / iOS PATH: STACKED ALPHA"))
            wp.evaluate(STAGE_CLUB); wp.evaluate("NR.core.setState('INTERRO'); NR.ui.interrogate('dolores', NR.story.dolores, {}); 0")
            wp.wait_for_timeout(4000)
            report["webkit_panel"] = wp.evaluate("NR.vperf.panelState && NR.vperf.panelState()")
            wp.screenshot(path=str(TMP / "13_webkit_itg.png")); shots.append((TMP / "13_webkit_itg.png", "WEBKIT: INTERROGATION (MP4)"))
            wctx.close(); wb.close()
finally:
    srv.terminate()

# ------------------------------------------------------------ contact sheet
cols, tw = 5, 234; th = int(tw * 844 / 390)
rows = (len(shots) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (10, 9, 8)); d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 13)
except Exception:
    font = ImageFont.load_default()
for k, (pth, label) in enumerate(shots):
    im = Image.open(pth).convert("RGB").resize((tw, th), Image.LANCZOS)
    x, y = (k % cols) * tw, (k // cols) * (th + 26)
    sheet.paste(im, (x, y + 26)); d.text((x + 6, y + 6), label, font=font, fill=(230, 200, 120))
sheet.save(OUT / "video_perf_v1.png")
(OUT / "video_perf_v1.json").write_text(json.dumps({"report": report, "errors": errors}, indent=1))
print(json.dumps(report, indent=1)[:6000])
print("ERRORS", len(errors)); [print(" ", e) for e in errors]
