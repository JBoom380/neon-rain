"""3D cast in game on 390x844 touch: the alley fight (thugs), Miles Corran's body, the club fight (Gale's men + the artificial
man), fps with 5 animated enemies, console errors. Writes tests/shots/cast_*.png. Usage: python tests/cast_test.py"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0; function f(now) { t.push(now - last); last = now; if (++n < 240) requestAnimationFrame(f); else { t.sort((a,b)=>a-b); r({ fps: +(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1), p95ms: +t[Math.floor(t.length*0.95)].toFixed(1) }); } } requestAnimationFrame(f); })"""
errs, info = [], {}
def click_through(pg):
    for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
        if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); return True
    return False
def start(pg, beat):
    pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html?beat={beat}"); pg.wait_for_function("window.READY === true")
    pg.wait_for_timeout(600); pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
def until(pg, cond, limit=60, clicks=True):
    t0 = time.time()
    while time.time() - t0 < limit:
        if pg.evaluate(cond): return True
        if clicks and pg.evaluate("NR.core.state") == "CUTSCENE": click_through(pg)
        pg.wait_for_timeout(150)
    return False
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        def page():
            pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
            pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
            return pg
        # ---------------- alley
        pg = page(); start(pg, "alley")
        until(pg, "NR.game.beat === 'alley_play'", 60)
        until(pg, "NR.actors.enemies.length === 3 && NR.actors.enemies.every(e => e.cr)", 40, False)
        info["alley_variants"] = pg.evaluate("NR.actors.enemies.map(e => e.variant + ':' + e.cr.kind)")
        pg.evaluate("NR.player.hurt = () => {}; NR.player.place(new THREE.Vector3(0.2, 0, -7.0), 0, 0)")
        pg.wait_for_timeout(2600); pg.screenshot(path=str(OUT / "cast_alley_1.png"))
        pg.wait_for_timeout(1500); pg.screenshot(path=str(OUT / "cast_alley_2.png"))
        info["alley_states"] = pg.evaluate("NR.actors.enemies.map(e => [e.state, e.cr.layerName.L, e.cr.layerName.U])")
        # kill them, then look at Miles
        pg.evaluate("for (const e of NR.actors.enemies) e.damage(500, e.headC, new THREE.Vector3(0, 0, -1), false)")
        pg.wait_for_timeout(1800); pg.screenshot(path=str(OUT / "cast_alley_dead.png"))
        pg.evaluate("(() => { const L = NR.game.level, bp = L.bodyPos; NR.core.setState('CUTSCENE'); NR.game.lookTarget = () => new THREE.Vector3(bp.x, 0.3, bp.z); NR.player.place(new THREE.Vector3(bp.x + 1.3, 0, bp.z + 1.6), 0.6, 0); })()")
        pg.wait_for_timeout(1500); pg.screenshot(path=str(OUT / "cast_miles.png"))
        info["miles"] = pg.evaluate("(() => { const g = NR.game.level.scene.children.find(o => o.userData && o.userData.rig && o.userData.rig.variant === 'miles'); if (!g) return 'no rig'; const h = g.userData.rig.bones.head.getWorldPosition(new THREE.Vector3()); const hat = g.userData.hat; const hp = hat ? new THREE.Box3().setFromObject(hat) : null; return { head: h.toArray().map(v => +v.toFixed(2)), hatMin: hp && hp.min.toArray().map(v => +v.toFixed(2)), hatMax: hp && hp.max.toArray().map(v => +v.toFixed(2)) }; })()")
        pg.close()
        # ---------------- club fight
        pg = page(); start(pg, "clubfight")
        until(pg, "NR.game.beat === 'club_fight'", 60)
        until(pg, "NR.actors.enemies.length === 5 && NR.actors.enemies.every(e => e.cr)", 40, False)
        info["club_variants"] = pg.evaluate("NR.actors.enemies.map(e => e.variant + ':' + e.cr.kind)")
        pg.evaluate("NR.player.hurt = () => {}")
        pg.wait_for_timeout(2500); pg.screenshot(path=str(OUT / "cast_club_1.png"))
        # fps with all 5 animated on screen: stage the five in the open floor in front of the camera (they keep their AI)
        pg.evaluate("""(() => { NR.core.setState('PLAY'); NR.game.lookTarget = null; const P = NR.player, L = NR.game.level, V = (x, y, z) => new THREE.Vector3(x, y, z);
          let best = null; for (const sx of [-4, -2, 0, 2, 4, 6]) for (const sz of [-2, -5, -8, -11, -14, -17]) { if (L.blockedAt(sx, sz, 0.4)) continue;
            for (let k = 0; k < 16; k++) { const yaw = k * Math.PI / 8, dir = V(-Math.sin(yaw), 0, -Math.cos(yaw)); const h = L.ray(V(sx, 1.2, sz), dir, 12); const free = h ? h.point.distanceTo(V(sx, 1.2, sz)) : 12;
              let ok = 0; for (let i = 0; i < 5; i++) { const q = V(sx, 0, sz).addScaledVector(dir, 4 + i * 0.9).add(V(dir.z, 0, -dir.x).multiplyScalar((i - 2) * 0.9)); if (!L.blockedAt(q.x, q.z, 0.3)) ok++; }
              const sc = Math.min(free, 9) + ok * 2; if (!best || sc > best.sc) best = { sc, sx, sz, yaw, dir }; } }
          P.place(V(best.sx, 0, best.sz), best.yaw, -0.04);
          NR.actors.enemies.forEach((e, i) => { const q = V(best.sx, 0, best.sz).addScaledVector(best.dir, 4 + i * 0.9).add(V(best.dir.z, 0, -best.dir.x).multiplyScalar((i - 2) * 0.9)); e.pos.copy(q); e.prev.copy(q); if (e.cover) { e.cover.taken = null; e.cover = null; } e.state = 'stand'; e.t = -100; });
          window.__best = best; })()""")
        pg.wait_for_timeout(1200)
        info["onscreen"] = pg.evaluate("(() => { const cam = NR.core.camera; cam.updateMatrixWorld(); const f = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse)); return NR.actors.enemies.filter(e => !e.dead && f.containsPoint(e.headC)).length; })()")
        info["fps_5_enemies"] = pg.evaluate(FPS_JS)
        cdp = pg.context.new_cdp_session(pg); cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        info["fps_5_enemies_cpu4x"] = pg.evaluate(FPS_JS); cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
        info["onscreen_after"] = pg.evaluate("(() => { const cam = NR.core.camera; cam.updateMatrixWorld(); const f = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse)); return NR.actors.enemies.filter(e => !e.dead && f.containsPoint(e.headC)).length; })()")
        pg.screenshot(path=str(OUT / "cast_club_all.png"))
        pg.evaluate("NR.core.setState('PLAY'); NR.game.lookTarget = null; NR.player.place(new THREE.Vector3(5.6, 0, -14.4), 0.9, 0)")
        pg.wait_for_timeout(1800); pg.screenshot(path=str(OUT / "cast_club_2.png"))
        pg.evaluate("(() => { NR.core.setState('CUTSCENE'); NR.player.place(new THREE.Vector3(5.6, 0, -14.4), 0.9, 0); const P = NR.player.pos; let best = null, bd = 1e9; for (const e of NR.actors.enemies) { if (e.dead) continue; const d = Math.hypot(e.pos.x - P.x, e.pos.z - P.z); if (d < bd && d > 2.5) { bd = d; best = e; } } if (best) NR.game.lookTarget = () => new THREE.Vector3(best.pos.x, 1.3, best.pos.z); })()")
        pg.wait_for_timeout(1600); pg.screenshot(path=str(OUT / "cast_club_view.png"))
        info["club_states"] = pg.evaluate("NR.actors.enemies.map(e => [e.state, e.cr.layerName.L, e.cr.layerName.U])")
        pg.close(); b.close()
finally:
    srv.terminate()
print(json.dumps(info, indent=1)); print("ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
