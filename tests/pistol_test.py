""".45 pistol logic: 7+1, fire rate, slide lock + dry click, tactical (7+1) vs empty (7) reload, magazine count, no-mags,
mag drops, HUD text, RELOAD button pulse. Usage: python tests/pistol_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8); r, errs = {}, []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat=clubfight"); pg.wait_for_function("window.READY === true"); pg.wait_for_timeout(600)
        pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
        pg.wait_for_function("NR.game.beat === 'club_fight' && NR.core.state === 'PLAY'", timeout=30000)
        pg.evaluate("""(() => { NR.player.god = true; NR.player.drawn = true; for (const e of NR.actors.enemies) { e.state = 'dormant'; e.pos.set(0, -50, 0); e.group.position.set(0, -50, 0); } window.__ev = []; for (const e of ['shot','dryFire','slideLock','reload','reloaded','noMags','magPickup']) NR.bus.on(e, d => window.__ev.push(e));
          NR.player.pitch = 1.1; NR.controls.lastDevice; NR.controls.inject = { fire: false }; })()""")
        r["start"] = pg.evaluate("[NR.player.rounds, NR.player.mags]")
        pg.evaluate("NR.controls.inject.fire = true"); t0 = pg.evaluate("performance.now()")
        pg.wait_for_function("NR.player.rounds === 0", timeout=5000); t1 = pg.evaluate("performance.now()")
        r["8_shots_ms"] = round(t1 - t0); pg.wait_for_timeout(400); pg.evaluate("NR.controls.inject.fire = false")
        r["slide_lock"] = pg.evaluate("[NR.player.slideLock, window.__ev.filter(e => e === 'dryFire').length > 0, document.querySelector('#nru .tl .rl').textContent, document.querySelector('#nrc .reload').classList.contains('need')]")
        pg.evaluate("NR.controls.inject.reload = true"); pg.wait_for_function("NR.player.reloadT <= 0 && !NR.player.slideLock", timeout=5000)
        r["empty_reload"] = pg.evaluate("[NR.player.rounds, NR.player.mags, NR.player.reloadDur]")
        r["pre"] = pg.evaluate("[NR.player.armed, NR.player.drawn, NR.player.drawT, NR.player.reloadT, NR.core.state, NR.player.rounds]"); pg.evaluate("NR.player.rounds = 3; NR.player.reload()"); pg.wait_for_timeout(100); pg.wait_for_function("NR.player.reloadT <= 0", timeout=5000)
        r["state_before_tac"] = pg.evaluate("[NR.player.armed, NR.player.drawn, NR.player.drawT, NR.player.reloadT, NR.core.state]")
        r["tactical_reload"] = pg.evaluate("[NR.player.rounds, NR.player.mags, NR.player.reloadDur]")
        pg.evaluate("NR.player.rounds = 0; NR.player.mags = 0; NR.player.reloadT = 0; NR.player.reload()"); pg.wait_for_timeout(300)
        r["no_mags"] = pg.evaluate("[NR.player.reloadT > 0, window.__ev.includes('noMags')]")
        pg.evaluate("NR.bus.emit('enemyDown', { enemy: {}, head: false })"); r["drop_when_empty"] = pg.evaluate("NR.player.mags")
        r["events"] = pg.evaluate("[...new Set(window.__ev)]")
        b.close()
finally:
    srv.terminate()
print(json.dumps(r)); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
