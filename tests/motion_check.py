"""Real-time motion check on 390x844 touch: Playwright video of (1) alley thugs rushing + knife slash, (2) Gale's men moving
between cover, peeking and firing, (3) a death fall, (4) Vela walking in (painted billboard). Each clip is cut to ~6 s,
captioned and joined into tests/shots/motion_check.mp4. Usage: python tests/motion_check.py"""
import json, pathlib, shutil, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"; TMP = OUT / "_motion"
shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir(parents=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
clips, errs, notes = [], [], {}

def click_through(pg):
    for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on"):
        if pg.evaluate(f"!!document.querySelector('{sel}')"): pg.evaluate(f"document.querySelector('{sel}').dispatchEvent(new PointerEvent('pointerup', {{bubbles:true}}))"); return

def until(pg, cond, limit=60, clicks=True):
    t0 = time.time()
    while time.time() - t0 < limit:
        if pg.evaluate(cond): return True
        if clicks and pg.evaluate("NR.core.state") == "CUTSCENE": click_through(pg)
        pg.wait_for_timeout(120)
    return False

def session(b, name, beat, script):
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True, is_mobile=True,
                        record_video_dir=str(TMP / name), record_video_size={"width": 390, "height": 844})
    pg = ctx.new_page(); t0 = time.time()
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(f"http://127.0.0.1:{PORT}/src/dev.html" + (f"?beat={beat}" if beat else "")); pg.wait_for_function("window.READY === true")
    pg.wait_for_timeout(600); pg.evaluate("NR.ui.fast = true"); pg.touchscreen.tap(195, 500); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#nru .title .btn.red').dispatchEvent(new PointerEvent('pointerup', {bubbles:true}))")
    marks = script(pg, lambda: time.time() - t0)
    path = pg.video.path(); ctx.close()
    for (label, a, dur) in marks: clips.append((label, str(path), a, dur))

AIM_AT = "(e) => { const P = NR.player, dx = e.pos.x - P.pos.x, dz = e.pos.z - P.pos.z; P.yaw = Math.atan2(-dx, -dz); P.pitch = -0.05; }"

def alley(pg, now):
    until(pg, "NR.game.beat === 'alley_play'", 60)
    until(pg, "NR.actors.enemies.length === 3 && NR.actors.enemies.every(e => e.cr)", 40, False)
    pg.evaluate("NR.player.hurt = () => {}; NR.player.place(new THREE.Vector3(0.0, 0, -7.0), 0, -0.04)")
    pg.evaluate("""(() => { window.__fs = []; const tick = () => { for (const e of NR.actors.enemies) { if (!e.cr || e.dead || e.cr.layerName.L !== 'run' || e.cr.layer.L.getEffectiveWeight() < 0.99) continue; const b = e.cr.bones; window.__ts = [e.cr.layer.L.timeScale, e.cr.speedOf('run')];
      for (const f of ['foot_L', 'foot_R']) { const n = e.cr.nodes[f]; const p = n.getWorldPosition(new THREE.Vector3()); window.__fs.push([e.id, f, performance.now(), p.x, p.y, p.z, e.vel.length(), e.cr.fl && e.cr.fl[f.slice(-1)].lock ? 1 : 0, e.cr.fl ? +e.cr.fl[f.slice(-1)].w.toFixed(2) : -1, e.cr.fl ? +(e.cr.fl[f.slice(-1)].lo || 0).toFixed(3) : -1, +e.cr.ankle0.toFixed(3)]); } }
      if (window.__fs.length < 4000) requestAnimationFrame(tick); }; requestAnimationFrame(tick); })()""")
    a = now(); pg.wait_for_timeout(7000)
    fs = pg.evaluate("window.__fs"); notes['run_timescale'] = pg.evaluate('window.__ts'); notes['ik'] = pg.evaluate('[window.__flc, window.__fle]')
    import collections, math
    tr = collections.defaultdict(list)
    for eid, f, t, x, y, z, v, lk, w, lo, a0 in fs: tr[(eid, f)].append((t / 1000, x, y, z, v, lk, w, lo, a0))
    k0 = sorted(tr, key=lambda k: -len(tr[k]))[0]; notes['trace'] = [(round(q[2], 3), q[5], q[6], round(q[1], 3), round(q[3], 3)) for q in tr[k0][:45]]
    slide, body, split, bad = [], [], {}, []
    for k, s in tr.items():
        if len(s) < 10: continue
        ymin = min(q[2] for q in s)
        for q0, q1 in zip(s[:-1], s[1:]):
            dt = q1[0] - q0[0]
            if dt <= 0 or dt > 0.1: continue
            if q0[2] < ymin + 0.012 and q1[2] < ymin + 0.012:
                slide.append(math.hypot(q1[1] - q0[1], q1[3] - q0[3]) / dt); body.append(q0[4]); split.setdefault((q0[5], q1[5]), []).append(slide[-1]); (q0[5] == 0 or q1[5] == 0) and bad.append((k, round(q0[0] - tr[k][0][0], 2), round(q0[2], 3), round(q1[2], 3), round(slide[-1], 2), q0[5], q1[5], q0[6], q1[6], q0[7]))
    notes['bad'] = bad[:40]
    notes['split'] = {str(k): [len(v), round(sum(v) / len(v), 2)] for k, v in split.items()}
    notes["foot_slide"] = {"contact_samples": len(slide), "foot_speed_on_ground_mps": round(sum(slide) / max(1, len(slide)), 2), "body_speed_mps": round(sum(body) / max(1, len(body)), 2)}
    notes["alley"] = pg.evaluate("NR.actors.enemies.map(e => [e.variant, e.state, e.cr.layerName.L, e.cr.layerName.U])")
    return [("1 Alley thugs rush in, knife slash", a, 6.5)]

def club(pg, now):
    until(pg, "NR.game.beat === 'club_fight'", 60)
    until(pg, "NR.actors.enemies.length === 5 && NR.actors.enemies.every(e => e.cr)", 40, False)
    pg.evaluate("NR.player.hurt = () => {}")
    # stand where the room opens up and keep facing the nearest live gunman (the camera follows him)
    pg.evaluate("(() => { NR.player.place(new THREE.Vector3(4.6, 0, -6.0), 0, -0.04); window.__track = setInterval(() => { const P = NR.player; let best = null, bd = 1e9; for (const e of NR.actors.enemies) { if (e.dead) continue; const d = Math.hypot(e.pos.x - P.pos.x, e.pos.z - P.pos.z); if (d < bd) { bd = d; best = e; } } if (best) { const dx = best.pos.x - P.pos.x, dz = best.pos.z - P.pos.z; const want = Math.atan2(-dx, -dz); let dy = want - P.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy)); P.yaw += dy * 0.08; P.pitch = -0.06; } }, 16); })()")
    a = now(); pg.wait_for_timeout(7000)
    notes["club"] = pg.evaluate("NR.actors.enemies.map(e => [e.variant, e.state, e.cr.layerName.L, e.cr.layerName.U])")
    # a death fall: pick the nearest live one, hold the camera on him, shoot him in the chest from the front
    pg.evaluate("(() => { clearInterval(window.__track); const P = NR.player; let best = null, bd = 1e9; for (const e of NR.actors.enemies) { if (e.dead) continue; const d = Math.hypot(e.pos.x - P.pos.x, e.pos.z - P.pos.z) - (e.crouch > 0.5 ? 6 : 0); if (d < bd && NR.game.level.los(P.eye(), e.headC)) { bd = d; best = e; } } if (!best) for (const e of NR.actors.enemies) if (!e.dead) { best = e; break; } window.__victim = best; window.__track = setInterval(() => { const e = window.__victim, hp = e.cr ? e.cr.bones.hips.getWorldPosition(new THREE.Vector3()) : e.pos; const dx = hp.x - P.pos.x, dz = hp.z - P.pos.z; P.yaw = Math.atan2(-dx, -dz); P.pitch = Math.atan2(hp.y - 1.5, Math.hypot(dx, dz)) * 0.8; }, 16); })()")
    b = now(); pg.wait_for_timeout(900)
    pg.evaluate("(() => { const e = window.__victim, P = NR.player; const d = new THREE.Vector3(e.pos.x - P.pos.x, 0, e.pos.z - P.pos.z).normalize(); e.damage(500, e.headC.clone().add(new THREE.Vector3(0, -0.4, 0)), d, false); })()")
    pg.wait_for_timeout(3500)
    notes["death"] = pg.evaluate("[window.__victim.deathClip, +window.__victim.crouch.toFixed(2)]")
    return [("2 Gale's men: cover, peek, fire", a, 6.5), ("3 A death fall", b, 4.2)]

def office(pg, now):
    until(pg, "NR.game.chars[0] && NR.game.chars[0].walking", 90)
    a = now() - 0.3; pg.wait_for_timeout(6500)
    notes["vela"] = pg.evaluate("NR.game.chars[0].constructor.name")
    return [("4 Vela walks in (painted billboard, 2-pose walk)", a, 6.0)]

try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        session(b, "alley", "alley", alley)
        session(b, "club", "clubfight", club)
        session(b, "office", None, office)
        b.close()
finally:
    srv.terminate()
# cut, caption, join (30 fps MP4, 390x844)
parts = []
font = "C\\:/Windows/Fonts/arialbd.ttf"
for i, (label, src, a, dur) in enumerate(clips):
    out = TMP / f"part{i}.mp4"
    txt = label.replace(":", "\\:").replace("'", "")
    vf = f"fps=30,scale=390:844,drawbox=x=0:y=ih-54:w=iw:h=54:color=black@0.7:t=fill,drawtext=fontfile='{font}':text='{txt}':x=10:y=h-38:fontsize=17:fontcolor=0xF0C060"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0, a):.2f}", "-t", f"{dur:.2f}", "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)], check=True)
    parts.append(out)
lst = TMP / "list.txt"; lst.write_text("".join(f"file '{p_.as_posix()}'\n" for p_ in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(OUT / "motion_check_v2.mp4")], check=True)
print(json.dumps(notes)); print("clips", [(c[0], round(c[2], 1)) for c in clips]); print("ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
print("wrote", OUT / "motion_check_v2.mp4")
