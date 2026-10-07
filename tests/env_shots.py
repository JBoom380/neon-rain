"""Environment pass check on a 390x844 touch screen: the beats John saw (office start view toward the window, Vela at the
desk, the alley, the Blue Orchid), fps per set, console errors. Runs the baked sets (default) and the grey-box sets
(?env=grey) and writes a before/after sheet.
Usage: python tests/env_shots.py [--only after|before] [--throttle N] [--out env_pass_v1.png]"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
THROTTLE = int(sys.argv[sys.argv.index("--throttle") + 1]) if "--throttle" in sys.argv else 1
SHEET = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "env_pass_v1.png"
BUILT = "--built" in sys.argv
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0;
  function f(now) { t.push(now - last); last = now; if (++n < 150) requestAnimationFrame(f); else { t.sort((a,b)=>a-b);
    r({ fps: +(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1), p95ms: +t[Math.floor(t.length*0.95)].toFixed(1) }); } }
  requestAnimationFrame(f); })"""


def run(pw, mode):
    errs, shots, fps = [], {}, {}
    b = pw.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required", "--ignore-gpu-blocklist"])
    def page(q):
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text[:300]))
        if THROTTLE > 1: pg.context.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": THROTTLE})
        url = f"http://127.0.0.1:{PORT}/" + ("index.html" if BUILT else "src/dev.html") + "?" + q + ("&env=grey" if mode == "before" else "")
        pg.goto(url); pg.wait_for_function("window.READY === true", timeout=60000)
        pg.wait_for_timeout(600); pg.evaluate("NR.ui.fast = true")
        pg.touchscreen.tap(195, 500); pg.wait_for_timeout(500)
        pg.evaluate("document.querySelector('#nru .title .btn.red') && document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        return pg
    def advance(pg):
        for sel in ("#nru .tut.on", "#nru .dlg.on", "#nru .card.on"):
            if pg.evaluate(f"!!document.querySelector('{sel}')"):
                pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); return
    def until(pg, cond, timeout=60, adv=True):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if pg.evaluate(cond): return True
            if adv: advance(pg)
            pg.evaluate("NR.game.beat === 'office_smoke' && NR.core.state === 'PLAY' && NR.player.smoked < 1 && NR.player.smoke()")
            pg.wait_for_timeout(150)
        raise RuntimeError(mode + " timeout " + cond + " beat=" + pg.evaluate("NR.game.beat"))
    def envready(pg, name):
        if mode == "after": pg.wait_for_function(f"!NR.env.built.includes('{name}') || NR.env.ready['{name}'] !== undefined", timeout=60000); pg.evaluate(f"NR.env.ready['{name}'] || null")
    def shot(pg, key):
        f = OUT / f"env_{mode}_{key}.png"; pg.screenshot(path=str(f)); shots[key] = f; print(mode, "shot", key, pg.evaluate("NR.game.beat"))
    # office
    pg = page("")
    until(pg, "NR.game.beat === 'office' && !!document.querySelector('#nru .dlg.on')", 60, adv=False)
    envready(pg, "office"); pg.wait_for_timeout(3200); shot(pg, "office")
    until(pg, "NR.game.beat === 'office_talk'", 60); pg.wait_for_timeout(1500); shot(pg, "vela")
    until(pg, "NR.game.beat === 'office_play' && NR.core.state === 'PLAY'", 120)
    pg.wait_for_timeout(500); fps["office"] = pg.evaluate(FPS_JS)
    # free look around the office at the end of the beat: toward the desk from the door side
    pg.evaluate("NR.player.place(new THREE.Vector3(-1.2, 0, -3.4), -2.76, -0.32)"); pg.wait_for_timeout(700); shot(pg, "officedesk")
    pg.close()
    # alley
    pg = page("beat=alley")
    until(pg, "NR.game.beat === 'alley_play' && NR.core.state === 'PLAY'", 60)
    envready(pg, "alley"); pg.wait_for_timeout(1500); shot(pg, "alley"); fps["alley"] = pg.evaluate(FPS_JS)
    pg.close()
    # club
    pg = page("beat=club")
    until(pg, "NR.game.beat === 'club_scan' && NR.core.state === 'PLAY'", 60)
    envready(pg, "club"); pg.wait_for_timeout(1500); shot(pg, "club"); fps["club"] = pg.evaluate(FPS_JS)
    pg.close(); b.close()
    return shots, fps, errs


def sheet(results):
    keys = ["office", "vela", "officedesk", "alley", "club"]
    w, h = 260, 563
    rows = [m for m in ("before", "after") if m in results]
    im = Image.new("RGB", (w * len(keys), (h + 28) * len(rows)), (12, 10, 9)); d = ImageDraw.Draw(im)
    try: font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 15)
    except Exception: font = None
    for r, m in enumerate(rows):
        shots, fps, errs = results[m]
        for c, k in enumerate(keys):
            if k in shots:
                im.paste(Image.open(shots[k]).convert("RGB").resize((w, h)), (c * w, r * (h + 28) + 28))
            f = fps.get(k if k in fps else ("office" if k in ("vela", "officedesk") else k))
            d.text((c * w + 6, r * (h + 28) + 6), f"{m.upper()} {k}  {f['fps'] if f else ''} fps", fill=(230, 200, 150), font=font)
    im.save(OUT / SHEET); print("sheet", OUT / SHEET)


if __name__ == "__main__":
    res = {}
    try:
        with sync_playwright() as pw:
            for mode in ("before", "after"):
                if ONLY and mode != ONLY: continue
                res[mode] = run(pw, mode)
                print(mode, "fps", json.dumps(res[mode][1]), "errors", len(res[mode][2]))
                for e in res[mode][2][:10]: print("  ERR", e)
        sheet(res)
    finally:
        srv.terminate()
