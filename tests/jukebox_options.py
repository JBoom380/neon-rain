"""Jukebox design options A/B/C (?jb=a|b|c) on 390x844 touch: closed menu + open list with a track playing, and a
function check per variant (tap a track, pause/play, next, prev, scrub, shuffle, repeat, BACK keeps playing).
Writes tests/shots/jukebox_options.png. Usage: python tests/jukebox_options.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
ST = "(() => { const c = NR.audio.current(); return { cue: NR.audio.cueId, t: c ? +c.currentTime.toFixed(2) : -1, paused: c ? c.paused : null }; })()"
NAMES = {"a": "A  INLINE LIST", "b": "B  LINER NOTES", "c": "C  RADIO DIAL"}
shots, report, errs = [], {}, []
def tap(pg, sel):
    pg.evaluate(f"document.querySelector('{sel}').scrollIntoView({{block:'center'}})")
    r = pg.evaluate(f"(() => {{ const b = document.querySelector('{sel}').getBoundingClientRect(); return [b.x + b.width/2, b.y + b.height/2]; }})()")
    pg.touchscreen.tap(r[0], r[1]); pg.wait_for_timeout(250)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        for v in "abc":
            pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
            pg.on("pageerror", lambda e, v=v: errs.append(v + " " + str(e))); pg.on("console", lambda m, v=v: m.type == "error" and errs.append(v + " " + m.text))
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?jb={v}"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(1000)
            pg.touchscreen.tap(195, 500); pg.wait_for_timeout(2500)
            f = f"jb_{v}_closed.png"; pg.screenshot(path=str(OUT / f)); shots.append((NAMES[v] + ": menu", f))
            tap(pg, "#nru .title .menu .btn:nth-child(2)"); pg.wait_for_timeout(500)
            if v == "c": tap(pg, '#nru .jb [data-act="list"]')
            tap(pg, '#nru .jb [data-i="2"]'); pg.wait_for_timeout(2600)
            r = {"variant": pg.evaluate("NR.jukebox.variant"), "after_tap": pg.evaluate(ST)}
            f = f"jb_{v}_open.png"; pg.screenshot(path=str(OUT / f)); shots.append((NAMES[v] + ": playing", f))
            tap(pg, '#nru .jb [data-act="play"]'); r["paused"] = pg.evaluate(ST)["paused"]
            tap(pg, '#nru .jb [data-act="play"]'); pg.wait_for_timeout(300); r["resumed"] = not pg.evaluate(ST)["paused"]
            if v == "c":
                tap(pg, '#nru .jb .dial .ar[data-act="next"]')
            else: tap(pg, '#nru .jb [data-act="next"]')
            pg.wait_for_timeout(300); r["next"] = pg.evaluate("NR.audio.cueId")
            tap(pg, '#nru .jb [data-act="prev"]'); pg.wait_for_timeout(300); r["prev"] = pg.evaluate("NR.audio.cueId")
            pg.evaluate("(() => { const rg = document.querySelector('#nru .jb input'); rg.value = 400; rg.dispatchEvent(new Event('input')); })()"); pg.wait_for_timeout(300)
            r["scrub"] = pg.evaluate("(() => { const c = NR.audio.current(); return +(c.currentTime / c.duration).toFixed(2); })()")
            tap(pg, '#nru .jb [data-act="shuf"]'); tap(pg, '#nru .jb [data-act="rep"]'); r["shuf_rep"] = pg.evaluate("[NR.jukebox.shuffle, NR.jukebox.repeat]")
            a0 = pg.evaluate(ST); tap(pg, '#nru .jb [data-act="back"]'); pg.wait_for_timeout(1200); a1 = pg.evaluate(ST)
            r["back_keeps_playing"] = a1["t"] > a0["t"] and not a1["paused"] and pg.evaluate("!document.querySelector('#nru .jb.on') && !!document.querySelector('#nru .title.on .menu .btn')")
            r["media"] = pg.evaluate("navigator.mediaSession.metadata && navigator.mediaSession.metadata.title + ' / ' + navigator.mediaSession.metadata.artist")
            report[v] = r; pg.close()
        b.close()
finally:
    srv.terminate()
W, H = 390, 844
img = Image.new("RGB", (6 * (W + 12) + 12, H + 96), (14, 13, 12)); d = ImageDraw.Draw(img)
f1, fb = ImageFont.truetype("arial.ttf", 20), ImageFont.truetype("arialbd.ttf", 22)
d.text((12, 14), "NEON RAIN jukebox options (?jb=a|b|c), menu style, 390x844", fill=(234, 223, 202), font=fb)
for i, (label, fn) in enumerate(shots):
    x = 12 + i * (W + 12); img.paste(Image.open(OUT / fn).convert("RGB").resize((W, H), Image.LANCZOS), (x, 50)); d.text((x, H + 60), label, fill=(232, 176, 64), font=f1)
img.save(OUT / "jukebox_options.png")
print(json.dumps(report, indent=0)); print("ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
