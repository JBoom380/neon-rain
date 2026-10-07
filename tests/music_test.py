"""NEON RAIN music + jukebox test on 390x844 touch and 1280x800 desktop:
landing menu plays 04 over the Blue Orchid; the jukebox plays every track (time advances); crossfade ramps; shuffle, repeat,
scrub; playback continues after the panel closes; Media Session metadata; rain loops decode. Screenshots: landing, jukebox x2.
Usage: python tests/music_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0; function f(now) { t.push(now - last); last = now; if (++n < 180) requestAnimationFrame(f); else { r(+(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1)); } } requestAnimationFrame(f); })"""
STATE = "(() => { const c = NR.audio.current(); return { cue: NR.audio.cueId, t: c ? +c.currentTime.toFixed(2) : -1, paused: c ? c.paused : null, gains: NR.audio.deckGains }; })()"
report, errs = {}, []
def tapjs(pg, sel): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))")
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        for dev, vp, touch in (("phone", {"width": 390, "height": 844}, True), ("desktop", {"width": 1280, "height": 800}, False)):
            pg = b.new_page(viewport=vp, device_scale_factor=2 if touch else 1, has_touch=touch, is_mobile=touch)
            pg.on("pageerror", lambda e, d=dev: errs.append(d + " pageerror: " + str(e))); pg.on("console", lambda m, d=dev: m.type == "error" and errs.append(d + ": " + m.text))
            pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(1200)
            if touch: pg.touchscreen.tap(195, 500)
            else: pg.mouse.click(640, 400)
            pg.wait_for_timeout(3500); r = {"landing": pg.evaluate(STATE), "fps_landing": pg.evaluate(FPS_JS)}
            r["rain_decoded"] = pg.evaluate("NR.audio.ambience && true")
            if dev == "phone": pg.screenshot(path=str(OUT / "music_landing.png"))
            # jukebox
            if touch:
                c = pg.evaluate("(() => { const b = document.querySelector('#nru .title .btn:nth-child(2)').getBoundingClientRect(); return [b.x + b.width/2, b.y + b.height/2]; })()"); pg.touchscreen.tap(c[0], c[1])
            else: tapjs(pg, "#nru .title .btn:nth-child(2)")
            pg.wait_for_timeout(900)
            if dev == "phone": pg.screenshot(path=str(OUT / "music_jukebox_1.png"))
            plays = []
            for i in range(pg.evaluate("NR.jukebox.list.length")):
                pg.evaluate(f"(() => {{ const c = document.querySelectorAll('#nru .jb .rec')[{i}]; c.scrollIntoView({{inline:'center'}}); c.dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}})); }})()")
                ramp = []
                for k in range(5): pg.wait_for_timeout(300); ramp.append(pg.evaluate("NR.audio.deckGains"))
                a = pg.evaluate(STATE); pg.wait_for_timeout(700); b2 = pg.evaluate(STATE)
                plays.append({"track": a["cue"], "advancing": b2["t"] > a["t"] and not b2["paused"], "ramp": ramp if i < 2 else None})
            r["plays"] = plays
            r["media_session"] = pg.evaluate("navigator.mediaSession && navigator.mediaSession.metadata ? navigator.mediaSession.metadata.title + ' / ' + navigator.mediaSession.metadata.artist : null")
            # shuffle + repeat + scrub
            tapjs(pg, "#nru .jb .sh"); tapjs(pg, "#nru .jb .rp")
            pg.evaluate("(() => { const rg = document.querySelector('#nru .jb input'); rg.value = 500; rg.dispatchEvent(new Event('input')); })()"); pg.wait_for_timeout(500)
            r["after_scrub"] = pg.evaluate("(() => { const c = NR.audio.current(); return +(c.currentTime / c.duration).toFixed(2); })()")
            r["shuffle_repeat"] = pg.evaluate("[NR.jukebox.shuffle, NR.jukebox.repeat]")
            pg.evaluate("(() => { const cs = document.querySelector('#nru .jb .cards'); cs.scrollLeft = cs.scrollWidth * 0.55; })()"); pg.wait_for_timeout(900)
            if dev == "phone": pg.screenshot(path=str(OUT / "music_jukebox_2.png"))
            else: pg.screenshot(path=str(OUT / "music_jukebox_desktop.png"))
            # next with shuffle, then close: keeps playing
            tapjs(pg, "#nru .jb .nx"); pg.wait_for_timeout(800); before = pg.evaluate(STATE)
            tapjs(pg, "#nru .jb .close"); pg.wait_for_timeout(1500); after = pg.evaluate(STATE)
            r["keeps_playing_after_close"] = after["t"] > before["t"] and not after["paused"] and after["cue"] == before["cue"]
            # ended -> next track (repeat ALL), simulate by seeking near the end
            tapjs(pg, "#nru .title .btn:nth-child(2)"); pg.wait_for_timeout(400)
            for _ in range(2): tapjs(pg, "#nru .jb .rp")   # one -> off -> all
            pg.evaluate("window.__c0 = NR.audio.cueId; NR.audio.current().loop = false; NR.audio.current().currentTime = NR.audio.current().duration - 0.6"); pg.wait_for_timeout(2500)
            r["auto_next_on_end"] = pg.evaluate("NR.audio.cueId !== window.__c0")
            report[dev] = r; pg.close()
        b.close()
finally:
    srv.terminate()
print(json.dumps(report, indent=1)); print("ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
