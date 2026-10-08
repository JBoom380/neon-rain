"""NEON RAIN grey-box slice, end to end on a 390x844 touch screen:
title -> office (smoke tutorial, revolver) -> alley fight -> club -> scan 3 clues -> interrogation -> verdict -> club fight -> end card.
Real CDP touch events drive the buttons (SMOKE, SCAN hold, INTERACT, the stick and the look drag); an in-page autopilot
steers and aims (NR.controls.inject). Writes tests/shots/slice_*.png and tests/shots/neon_rain_slice_sheet.png.
Usage: python tests/slice_test.py [--built] [--throttle N]"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "shots"; OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("slice_*.png"): old.unlink()
BUILT = "--built" in sys.argv
THROTTLE = int(sys.argv[sys.argv.index("--throttle") + 1]) if "--throttle" in sys.argv else 1
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)

FPS_JS = """() => new Promise(r => { const t = []; let last = performance.now(), n = 0;
  function f(now) { t.push(now - last); last = now; if (++n < 180) requestAnimationFrame(f); else { t.sort((a,b)=>a-b);
    r({ fps: +(1000 / (t.reduce((a,b)=>a+b,0) / t.length)).toFixed(1), p95ms: +t[Math.floor(t.length*0.95)].toFixed(1) }); } }
  requestAnimationFrame(f); })"""
PILOT_JS = """() => {
  const V = (x, z) => ({ x, z });
  window.__pilot = { goal: null, path: [], face: null, fight: false, arrived: false, aimTol: 0.035, human: true, careless: false, tgt: null, react: 0, noise: { x: 0, y: 0, z: 0 } };
  NR.controls.inject = { mx: 0, my: 0, lookX: 0, lookY: 0, fire: false };
  const wrap = a => Math.atan2(Math.sin(a), Math.cos(a));
  function aimAt(p, rate) { const P = NR.player, e = P.eye(); const dx = p.x - e.x, dy = p.y - e.y, dz = p.z - e.z;
    const yaw = Math.atan2(-dx, -dz), pitch = Math.atan2(dy, Math.hypot(dx, dz)); const ey = wrap(P.yaw - yaw), ep = P.pitch - pitch;
    NR.controls.inject.lookX = ey * rate; NR.controls.inject.lookY = ep * rate; return Math.hypot(ey, ep); }
  (function tick() { requestAnimationFrame(tick);
    const pl = window.__pilot, P = NR.player, J = NR.controls.inject; if (!P || NR.core.state !== 'PLAY') { J.mx = J.my = 0; J.fire = false; return; }
    J.mx = J.my = 0; J.fire = false; if (P.slideLock && P.reloadT <= 0) J.reload = true; // a human reloads when the slide locks
    if (pl.fight && P.armed && !P.drawn && P.drawT <= 0) J.gun = true; // draw for a fight
    let target = null;
    if (pl.fight) { let bd = 1e9; const e0 = P.eye();
      for (const en of NR.actors.enemies) { if (en.dead || en.state === 'dormant') continue; const h = en.headC; const body = { x: h.x, y: h.y - 0.35, z: h.z };
        const d = Math.hypot(h.x - e0.x, h.z - e0.z); const lh = NR.game.level.los(e0, h), lb = NR.game.level.los(e0, new THREE.Vector3(body.x, body.y, body.z));
        if ((lh || lb) && d < bd) { bd = d; target = lh ? h : body; } } }
    if (target && pl.human) { // human-like: reaction delay on a new target, slower slew, wobbling aim point
      const key = Math.round(target.x * 2) + ',' + Math.round(target.z * 2);
      if (pl.tgt !== key) { pl.tgt = key; pl.react = 0.28 + Math.random() * 0.25; }
      pl.react -= 1 / 60; if (Math.random() < 0.05) pl.noise = { x: (Math.random() - 0.5) * 0.22, y: (Math.random() - 0.5) * 0.3, z: (Math.random() - 0.5) * 0.22 };
      const dn = Math.min(1.5, Math.hypot(target.x - P.pos.x, target.z - P.pos.z) / 8);
      if (pl.react <= 0 && !pl.careless) { const err = aimAt({ x: target.x + pl.noise.x * dn, y: target.y - 0.12 * dn + pl.noise.y * dn, z: target.z + pl.noise.z * dn }, 0.12); J.fire = err < pl.aimTol && P.rounds > 0 && P.reloadT <= 0; }
      if (pl.careless && pl.react <= 0) { const err = aimAt({ x: target.x + pl.noise.x * 4, y: target.y + pl.noise.y * 3, z: target.z + pl.noise.z * 4 }, 0.05); J.fire = Math.random() < 0.08 && P.rounds > 0; }
    }
    else if (target) { const err = aimAt(target, 0.35); J.fire = err < pl.aimTol && P.rounds > 0 && P.reloadT <= 0; }
    else if (pl.face) aimAt(pl.face, 0.2);
    // a human pushes forward when nobody is in sight: close to ~6 m of the nearest live enemy
    pl.idle = target ? 0 : (pl.idle || 0) + 1 / 60;
    if (pl.fight && pl.idle > 2.0 && !pl.goal && !pl.path.length) { let near = null, nd = 1e9;
      for (const en of NR.actors.enemies) { if (en.dead || en.state === 'dormant') continue; const d = Math.hypot(en.pos.x - P.pos.x, en.pos.z - P.pos.z); if (d < nd) { nd = d; near = en; } }
      if (near && nd > 6) { const k = (nd - 5) / nd; pl.goal = { x: P.pos.x + (near.pos.x - P.pos.x) * k * 0.5, z: P.pos.z + (near.pos.z - P.pos.z) * k * 0.5 }; pl.push = true; } }
    if (!pl.goal && pl.path.length) pl.goal = pl.path.shift();
    if (pl.goal) { const dx = pl.goal.x - P.pos.x, dz = pl.goal.z - P.pos.z, d = Math.hypot(dx, dz);
      if (d < 0.25 || (pl.push && target)) { const was = pl.push; pl.goal = null; pl.push = false; if (!pl.path.length && !was) pl.arrived = true; }
      else { if (!target && !pl.face) aimAt({ x: pl.goal.x, y: P.pos.y + 1.55, z: pl.goal.z }, 0.15);
        const sy = Math.sin(P.yaw), cy = Math.cos(P.yaw), ux = dx / d, uz = dz / d, sp = Math.min(1, d * 1.5);
        J.mx = (ux * cy - uz * sy) * sp; J.my = (-ux * sy - uz * cy) * sp; } }
  })(); }"""


def main():
    shots, errs, fps, notes = [], [], {}, []
    global CUES; CUES = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--autoplay-policy=no-user-gesture-required"])
        pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        cdp = pg.context.new_cdp_session(pg)
        if THROTTLE > 1: cdp.send("Emulation.setCPUThrottlingRate", {"rate": THROTTLE})
        url = f"http://127.0.0.1:{PORT}/" + ("index.html" if BUILT else "src/dev.html")
        pg.goto(url); pg.wait_for_function("window.READY === true", timeout=30000)
        ev = pg.evaluate
        def wait(ms): pg.wait_for_timeout(ms)
        def shot(key, label):
            f = f"slice_{len(shots) + 1:02d}_{key}.png"; pg.screenshot(path=str(OUT / f)); cue = ev("NR.audio.cueId"); shots.append((label, f)); CUES[f] = cue; print("shot", f, "|", ev("NR.game.beat"), "| cue", cue)
        def center(sel):
            r = ev(f"(() => {{ const e = document.querySelector('{sel}'); if (!e) return null; const b = e.getBoundingClientRect(); return b.width ? [b.x + b.width/2, b.y + b.height/2] : null; }})()")
            return r
        def tap_sel(sel):
            ev(f"(() => {{ const e = document.querySelector('{sel}'); if (e) e.scrollIntoView({{block: 'center'}}); }})()"); wait(120)
            c = center(sel)
            if c: pg.touchscreen.tap(c[0], c[1]); return bool(c)
        tid = [10]
        def touch(kind, x, y, i):
            cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [] if kind == "touchEnd" else [{"x": x, "y": y, "id": i}]})
        def btn_xy(name):
            L = ev("(() => { const L = NR.controls.touchLayout, v = NR.core.view; return { v, L }; })()"); v, L = L["v"], L["L"]
            m = {"smoke": (L["bx"], L["smy"]), "scan": (L["bx"], L["scy"]), "reload": (L["bx"], L["ry"]), "interact": (L["ix"], L["iy"]), "fire": (L["fx"], L["fy"]), "stick": (L["sx"], L["sy"]), "look": (L["w"] * 0.72, L["h"] * 0.4)}[name]
            return v["left"] + m[0], v["top"] + m[1]
        def press(name, hold_ms=60):
            x, y = btn_xy(name); tid[0] += 1; touch("touchStart", x, y, tid[0]); wait(hold_ms); touch("touchEnd", x, y, tid[0])
        def advance():
            for sel in ("#nru > .tut.on", "#nru > .dlg.on", "#nru > .card.on", "#nru .over.on .btn.red"):
                c = center(sel)
                if c: pg.touchscreen.tap(c[0], c[1]); return True
            return False
        HOOKS = []
        def until(cond, timeout=60, hook=None, adv=True):
            t0 = time.time()
            while time.time() - t0 < timeout:
                for hk in HOOKS: hk()
                if ev(cond): return True
                if hook: hook()
                if adv and ev("NR.core.state") in ("CUTSCENE", "TITLE", "DOWN"): advance()
                wait(150)
            dbg = ev("JSON.stringify({ p: [NR.player.pos.x.toFixed(1), NR.player.pos.z.toFixed(1)], lives: NR.player.lives, pilot: window.__pilot && { goal: window.__pilot.goal, path: window.__pilot.path, idle: window.__pilot.idle }, en: NR.actors.enemies.map(e => [e.type, e.state, e.dead, e.pos.x.toFixed(1), e.pos.z.toFixed(1), e.hp]) })")
            pg.screenshot(path=str(OUT / "fail.png"))
            raise RuntimeError("timeout waiting for " + cond + " beat=" + ev("NR.game.beat") + " state=" + ev("NR.core.state") + " " + dbg)
        def go(path, face=None, timeout=40):
            ev(f"(() => {{ const pl = window.__pilot; pl.path = {json.dumps([{'x': a, 'z': b} for a, b in path])}; pl.goal = null; pl.arrived = false; pl.face = {json.dumps(face)}; }})()")
            until("window.__pilot.arrived", timeout)
        def face(pt): ev(f"window.__pilot.face = {json.dumps(pt)}")
        seen = set()
        def snap_once(key, label, cond, delay=0):
            def hook():
                if key not in seen and ev(cond):
                    seen.add(key); wait(delay); shot(key, label)
            return hook

        # ---- gate + title
        wait(2000); shot("gate", "TAP TO ENTER gate")
        pg.touchscreen.tap(195, 500); wait(1200); fps["title"] = ev(FPS_JS); shot("title", "Title")
        tap_sel("#nru .title .btn.red")
        ev(PILOT_JS)
        # ---- office prologue
        def ramp_hook():
            if "ramp" not in seen and ev("NR.audio.cueId") == "03":
                seen.add("ramp"); r = []
                for k in range(8): r.append(ev("NR.audio.deckGains")); wait(220)
                notes.append("crossfade 02->03 deck gains every 0.22 s: " + json.dumps(r))
        HOOKS.append(ramp_hook)
        hooks = [snap_once("card", "Intertitle card", "document.querySelector('#nru > .card.vis') !== null", 400),
                 snap_once("office", "Office: rain, blinds, VO", "NR.game.beat === 'office' && document.querySelector('#nru .dlg.on') !== null && NR.core.fx.fade < 0.05", 900),
                 snap_once("velawalk", "Vela walks in (paced two-pose walk)", "NR.game.chars[0] && NR.game.chars[0].walking && NR.game.chars[0].pos.z > -3.2", 0),
                 snap_once("vela", "Vela at the desk", "NR.game.beat === 'office_talk'", 1200),
                 snap_once("light", "She lights his cigarette", "NR.game.beat === 'office_light' && NR.player.forceCig", 500)]
        def walkframes():
            if "velawalk" in seen and "wf" not in seen:
                seen.add("wf")
                for k in range(6):
                    pg.screenshot(path=str(OUT / f"walk_{k}.png"), clip={"x": 60, "y": 150, "width": 270, "height": 420}); wait(110)
        hooks.append(walkframes)
        until("NR.game.beat === 'office_smoke' && NR.core.state === 'PLAY'", 120, hook=lambda: [h() for h in hooks])
        wait(400); press("smoke"); wait(900); shot("smoke", "She lights his cigarette (SMOKE)")
        until("NR.game.beat === 'office_play' && NR.core.state === 'PLAY'", 90)
        go([(-0.1, 0.45)], timeout=20)  # the env pass starts Harrow 1.2 m behind his chair: step up to the desk
        face({"x": -0.12, "y": 0.8, "z": -0.35}); wait(900)
        press("interact"); until("NR.player.armed && NR.core.state === 'PLAY'", 20); face(None)
        wait(300); shot("revolver", "Revolver taken; touch HUD")
        fps["office"] = ev(FPS_JS)
        go([(-1.6, 0.4), (-1.6, -3.4), (-1.0, -4.2), (-1.0, -5.3)], timeout=40)
        # ---- alley
        until("NR.game.beat === 'alley_play' && NR.core.state === 'PLAY'", 60)
        # real touch: stick drag forward + look drag
        z0, y0 = ev("NR.player.pos.z"), ev("NR.player.yaw")
        sx, sy = btn_xy("stick"); tid[0] += 1; i = tid[0]; touch("touchStart", sx, sy, i)
        for k in range(8): touch("touchMove", sx, sy - 8 * (k + 1), i); wait(40)
        wait(500); touch("touchEnd", sx, sy - 64, i)
        lx, ly = btn_xy("look"); tid[0] += 1; i = tid[0]; touch("touchStart", lx, ly, i)
        for k in range(6): touch("touchMove", lx - 6 * (k + 1), ly, i); wait(30)
        touch("touchEnd", lx - 36, ly, i)
        z1, y1 = ev("NR.player.pos.z"), ev("NR.player.yaw")
        notes.append(f"touch stick moved z {z0:.2f} -> {z1:.2f}; look drag yaw {y0:.3f} -> {y1:.3f}")
        shot("alley", "Alley in the rain")
        ev("window.__pilot.fight = true")
        HOOKS.append(snap_once("alleyfight", "Alley fight: thugs rush", "NR.player.hits >= 1 && NR.actors.enemies.some(e => !e.dead && e.state !== 'dormant')", 60))
        go([(0, -4), (0, -8)], timeout=60)
        ev("window.__pilot.path = []; window.__pilot.goal = null")
        t0 = time.time()
        until("NR.game.beat === 'alley_clear'", 120)
        notes.append(f"alley fight {time.time() - t0:.0f}s, lives {ev('NR.player.lives')}")
        # walk on toward Miles, look back at the blood
        go([(0, -14)], timeout=20); face({"x": -1.5, "y": 0.6, "z": -12.0}); wait(800); shot("alleyblood", "Wound blood: spray, wall and floor stains"); face(None)
        go([(0.3, -24), (0.3, -32.6)], face={"x": 0.2, "y": 0.2, "z": -34.5}, timeout=40)
        press("interact")
        until("NR.game.beat === 'alley_clear' && NR.core.state === 'CUTSCENE'", 10, adv=False); wait(900); shot("miles", "Miles Corran in the alley")
        # ---- club
        ev("window.__pilot.fight = false")
        until("NR.game.beat === 'club_scan' && NR.core.state === 'PLAY'", 90)
        wait(500); shot("club", "The Blue Orchid: stage light, smoke, booths")
        fps["club"] = ev(FPS_JS)
        ev("NR.core.settings.film = 'bwred'"); wait(400); shot("bwred", "Settings: FILM B&W RED"); ev("NR.core.settings.film = 'noir'"); wait(200)
        press("smoke"); wait(300)
        def scan_clue(cid, stand, pt, label):
            go([stand], face=pt, timeout=40); wait(500)
            x, y = btn_xy("scan"); tid[0] += 1; i = tid[0]; touch("touchStart", x, y, i)
            try:
                until(f"!!NR.game.caseData.clues['{cid}']", 12, adv=False)
                if label: wait(200); shot("scan_" + cid, label)
            finally:
                touch("touchEnd", x, y, i)
            face(None)
        go([(2.6, -6.0), (4.6, -11.0)], timeout=30)
        scan_clue("holder", (5.35, -13.4), {"x": 6.6, "y": 0.82, "z": -13.4}, "SCAN + THINK: lipstick on a holder tip")
        go([(2.4, -14.7), (0.6, -14.7)], face={"x": -1.5, "y": 1.6, "z": -19.5}, timeout=30); until("NR.audio.cueId === '05'", 8, adv=False); wait(1600); shot("stage", "By the stage: Dolores's song")
        go([(2.4, -14.7), (4.1, -14.4)], timeout=30)
        go([(4.1, -14.4), (4.1, -16.1), (5.4, -16.1)], timeout=30)
        scan_clue("ticket", (6.25, -18.3), {"x": 7.3, "y": 0.81, "z": -18.4}, None)
        scan_clue("mirror", (6.25, -19.8), {"x": 7.45, "y": 0.81, "z": -19.95}, "SCAN: milky smear on the mirror shard")
        tap_sel("#nru .tr .ib"); wait(700); shot("casefile", "Case file"); tap_sel("#nru .cf .close"); wait(300)
        go([(4.3, -15.7)], face={"x": 5.6, "y": 1.5, "z": -16.6}, timeout=20); wait(400)
        shot("dolores", "Dolores by the dressing room")
        press("interact")
        until("NR.game.beat === 'interrogation' && NR.core.state === 'INTERRO'", 60)
        wait(900); shot("interro", "Interrogation: close-up and meters")
        for q in ("miles", "leaving", "hand", "mother"):
            tap_sel(f'#nru .qb[data-q="{q}"]'); wait(400)
            until("!document.querySelector('#nru .qb.off')", 10, adv=False)
            if q == "leaving": wait(300); shot("slip", "A slip opened by a found clue")
        tap_sel('#nru [data-act="offer"]'); until("!document.querySelector('#nru .qb.off, #nru .btn.off[data-act=offer]') || !!document.querySelector('[data-verdict]')", 10, adv=False)
        wait(500); shot("offer", "OFFER: she never inhales; verdict")
        tap_sel('#nru [data-verdict="ARTIFICIAL"]')
        until("NR.game.beat === 'club_fight' && NR.core.state === 'PLAY'", 60)
        verdict = ev("JSON.parse(localStorage.getItem('neonRainFps.case')).verdicts.dolores")
        notes.append("verdict saved: " + str(verdict))
        ev("window.__pilot.fight = true; window.__pilot.aimTol = 0.03")
        press("smoke"); wait(250); shot("focus", "FOCUS: slow-mo smoke in the gunfight")
        fps["club_fight"] = ev(FPS_JS)
        ch = snap_once("clubfight", "Club gunfight: Gale's men in cover", "NR.player.hits >= 1 && NR.actors.enemies.filter(e => !e.dead && e.state !== 'dormant').length >= 2", 60)
        t0 = time.time()
        until("NR.game.beat === 'club_clear' || NR.game.beat === 'end'", 180, hook=ch)
        notes.append(f"club fight {time.time() - t0:.0f}s, lives {ev('NR.player.lives')}")
        ev("(() => { const a = NR.actors.enemies.find(e => e.kind === 'artificial'); const P = NR.player; const d = Math.hypot(a.pos.x - P.pos.x, a.pos.z - P.pos.z); window.__pilot.fight = false; window.__pilot.face = { x: a.pos.x, y: 0.2, z: a.pos.z }; if (d > 2.2) { window.__pilot.path = [{ x: a.pos.x + (P.pos.x - a.pos.x) / d * 1.8, z: a.pos.z + (P.pos.z - a.pos.z) / d * 1.8 }]; window.__pilot.goal = null; } })()")
        wait(2200); shot("milk", "Artificial man bleeds pale milk")
        until("NR.game.beat === 'end'", 60)
        wait(1800); shot("end", "End-of-slice card")
        st = ev("({ state: NR.core.state, shots: NR.player.shots, hits: NR.player.hits, heads: NR.player.heads, pack: NR.player.pack, lives: NR.player.lives, clues: Object.keys(NR.game.caseData.clues) })")
        notes.append("final " + json.dumps(st))
        # colour mode (B&W off) of the club for comparison
        b.close()
    return shots, errs, fps, notes


def women(shots, keys, name, title, cues=False):
    pick = [(l, f) for k in keys for (l, f) in shots if f.split("_", 2)[2][:-4] == k]
    th_w, th_h, cols = 390, 844, 3
    rows = (len(pick) + cols - 1) // cols
    img = Image.new("RGB", (cols * (th_w + 12) + 12, 50 + rows * (th_h + 44)), (14, 13, 12)); d = ImageDraw.Draw(img)
    try: f, fb = ImageFont.truetype("arial.ttf", 22), ImageFont.truetype("arialbd.ttf", 22)
    except Exception: f = fb = ImageFont.load_default()
    d.text((12, 14), title, fill=(234, 223, 202), font=fb)
    for i, (label, fn) in enumerate(pick):
        x = 12 + (i % cols) * (th_w + 12); y = 50 + (i // cols) * (th_h + 44)
        img.paste(Image.open(OUT / fn).convert("RGB").resize((th_w, th_h), Image.LANCZOS), (x, y)); d.text((x, y + th_h + 8), (label + "  [cue " + str(CUES.get(fn)) + "]") if cues else label, fill=(232, 176, 64), font=f)
    p = OUT / name; img.save(p); return p


def sheet(shots):
    th_w, th_h, cols = 260, 563, 5
    rows = (len(shots) + cols - 1) // cols
    W = cols * (th_w + 12) + 12; H = 52 + rows * (th_h + 40)
    img = Image.new("RGB", (W, H), (18, 16, 14)); d = ImageDraw.Draw(img)
    try: f, fb = ImageFont.truetype("arial.ttf", 15), ImageFont.truetype("arialbd.ttf", 20)
    except Exception: f = fb = ImageFont.load_default()
    d.text((12, 14), "NEON RAIN grey-box slice: end-to-end run at 390x844 touch (" + str(len(shots)) + " beats)", fill=(234, 223, 202), font=fb)
    for i, (label, fn) in enumerate(shots):
        x = 12 + (i % cols) * (th_w + 12); y = 52 + (i // cols) * (th_h + 40)
        im = Image.open(OUT / fn).convert("RGB").resize((th_w, th_h), Image.LANCZOS); img.paste(im, (x, y))
        d.text((x, y + th_h + 6), f"{i + 1}. {label}"[:34], fill=(232, 176, 64), font=f)
    p = OUT / "neon_rain_slice_sheet.png"; img.save(p); return p


try:
    shots, errs, fps, notes = main()
finally:
    srv.terminate()
print("FPS", json.dumps(fps))
for n in notes: print("NOTE", n)
print("ERRORS", len(errs)); [print("  ", e[:300]) for e in errs]
print("sheet", sheet(shots))
print("music", women(shots, ["title", "card", "revolver", "velawalk", "alleyfight", "club", "stage", "interro", "clubfight", "end"], "music_cues.png", "NEON RAIN: one scene per music cue (cue number in each label)", cues=True))
print("women", women(shots, ["velawalk", "vela", "light", "dolores", "interro", "offer"], "women_in_game.png", "NEON RAIN: the women in game (default B&W with red kept)"))
