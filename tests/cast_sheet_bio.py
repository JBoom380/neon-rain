"""characters_bioshock_v1.png: per character a turntable (front, 3/4, side, back) + face close-up in the game's real-time
look (three.js, PBR + rim, sodium / teal / red light, NOIR COLOR grade) on 390x844 frames, Harrow as first-person hands,
and a lineup of the whole cast. Usage: python tests/cast_sheet_bio.py [out.png]"""
import json, pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"; TMP = OUT / "_bio"; TMP.mkdir(parents=True, exist_ok=True)
DEST = OUT / (sys.argv[1] if len(sys.argv) > 1 else "characters_bioshock_v1.png")
ONLY = sys.argv[2].split(',') if len(sys.argv) > 2 else None
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
CAST = [("vela", "Vela Castellane", "idle"), ("dolores", "Dolores Delacroix", "idle"), ("kastor", "Kastor Gale", "idle"), ("dane", "Lt. Dane", "idle"),
        ("gale_a", "Gale's man: navy chalk-stripe", "aim_pistol"), ("gale_b", "Gale's man: camel overcoat, Thompson", "aim_tommy"), ("gale_c", "Gale's man: grey herringbone", "hold_pistol"),
        ("synth", "The artificial man", "aim_pistol"), ("thug_a", "Alley thug: the brawler", "slash"), ("thug_b", "Alley thug: the lamp man", "hold_knife_lamp"),
        ("thug_c", "Alley thug: the gunsel", "aim_pistol"), ("miles", "Miles Corran", "idle"), ("harrow", "Sam Harrow (first-person hands)", "aim_pistol")]
VIEWS = [("front", 0), ("3/4", 35), ("side", 90), ("back", 180)]
errs = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 390, "height": 844})
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/tests/cast_sheet_bio.html"); pg.wait_for_function("window.READY === true || window.ERR", timeout=120000)
        have = pg.evaluate("window.HAVE"); FAM = pg.evaluate("NR.cast.FAMILY")
        CAST[:] = [c for c in CAST if FAM[c[0]] in have and (not ONLY or c[0] in ONLY)]
        for vid, _, pose in CAST:
            for i, (nm, ang) in enumerate(VIEWS):
                pg.evaluate(f"window.shot('{vid}', {{ ang: {ang}, clip: 'idle', t: 0.5 }})"); pg.locator("canvas").screenshot(path=str(TMP / f"{vid}_{i}.png"))
            if vid == "harrow":
                pg.evaluate(f"window.shot('{vid}', {{ fp: true, clip: 'aim_pistol', t: 0.3 }})")
            else:
                pg.evaluate(f"window.shot('{vid}', {{ face: true, ang: 18, clip: 'idle', t: 0.5 }})")
            pg.locator("canvas").screenshot(path=str(TMP / f"{vid}_4.png"))
            pg.evaluate(f"window.shot('{vid}', {{ ang: 30, clip: '{pose}', t: {0.3 if pose == 'slash' else 0.4} }})"); pg.locator("canvas").screenshot(path=str(TMP / f"{vid}_5.png"))
        pg.set_viewport_size({"width": 1560, "height": 844})
        order = [('thug_a', 0.2), ('thug_b', 0.9), ('thug_c', 1.4), ('miles', 0.7), ('dane', 1.1), ('vela', 0.4), ('kastor', 0.6), ('dolores', 1.2), ('gale_a', 0.3), ('gale_b', 1.0), ('gale_c', 1.6), ('synth', 0.5)]
        lst = [[v, 'idle', t] for v, t in order if FAM[v] in have]
        pg.evaluate("window.lineup(" + json.dumps(lst) + ")")
        pg.locator("canvas").screenshot(path=str(TMP / "lineup.png"))
        b.close()
finally:
    srv.terminate()
TW, TH = 195, 422; LAB = 30; cols = 6
try: f, fb = ImageFont.truetype("arial.ttf", 16), ImageFont.truetype("arialbd.ttf", 26)
except Exception: f = fb = ImageFont.load_default()
lw, lh = 1560, 844
W = max(24 + cols * (TW + 6) + 24, lw + 48)
H = 90 + lh + 40 + len(CAST) * (TH + LAB + 6) + 20
img = Image.new("RGB", (W, H), (10, 9, 9)); d = ImageDraw.Draw(img)
d.text((24, 24), "NEON RAIN: the cast, BioShock pass v1 (three.js game look: PBR + rim, sodium/teal light, NOIR COLOR grade)", fill=(236, 222, 196), font=fb)
img.paste(Image.open(TMP / "lineup.png").convert("RGB"), (24, 70)); d.text((24, 70 + lh + 6), "Lineup", fill=(232, 176, 64), font=f)
y = 70 + lh + 40
for vid, label, pose in CAST:
    d.text((24, y), label + "   [front, 3/4, side, back, " + ("first-person hands" if vid == "harrow" else "face") + ", " + pose + "]", fill=(232, 176, 64), font=f)
    for i in range(cols):
        im = Image.open(TMP / f"{vid}_{i}.png").convert("RGB").resize((TW, TH), Image.LANCZOS)
        img.paste(im, (24 + i * (TW + 6), y + LAB - 6))
    y += TH + LAB + 6
img.save(DEST)
print("wrote", DEST, img.size, "ERRORS", len(errs)); [print(" ", e[:300]) for e in errs]
