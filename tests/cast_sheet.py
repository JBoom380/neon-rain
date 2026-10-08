"""characters_v2.png: a turntable sheet per cast member (front, 3/4, side, back, combat pose, face) under noir light, plus
the in-game shots from tests/cast_test.py (alley fight, Miles, club fight). Usage: python tests/cast_sheet.py (run cast_test.py first)"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "tests" / "shots"; TMP = OUT / "_cast"; TMP.mkdir(exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, str(ROOT / "tests" / "range_server.py"), str(PORT)], cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
CAST = [("thug_a", "Alley thug: the brawler", "slash", 0.3), ("thug_b", "Alley thug: the lamp man", "hold_knife_lamp", 0.4), ("thug_c", "Alley thug: the gunsel", "aim_pistol", 0.4),
        ("gale_a", "Gale's man: pinstripe", "aim_pistol", 0.4), ("gale_b", "Gale's man: overcoat, Thompson", "aim_tommy", 0.4), ("gale_c", "Gale's man: grey suit", "run", 0.3),
        ("synth", "The artificial man", "aim_pistol", 0.4), ("miles", "Miles Corran", "dead_pose", 0.0)]
VIEWS = [(0, None, 0.4, False), (35, None, 0.4, False), (90, None, 0.4, False), (180, None, 0.4, False), (40, "pose", 0, False), (18, None, 0.4, True)]
errs = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 300, "height": 520})
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
        pg.goto(f"http://127.0.0.1:{PORT}/tests/cast_sheet.html"); pg.wait_for_function("window.READY === true", timeout=60000)
        for vid, _, pose, pt in CAST:
            for i, (ang, clip, t, close) in enumerate(VIEWS):
                c, tt = (pose, pt) if clip == "pose" else ("idle", t)
                if vid == "miles" and clip != "pose": c = "idle"
                pg.evaluate(f"window.shot('{vid}', {ang}, '{c}', {str(close).lower()}, {tt})")
                pg.locator("canvas").screenshot(path=str(TMP / f"{vid}_{i}.png"))
        b.close()
finally:
    srv.terminate()
TW, TH = 300, 520; LAB = 34
try: f, fb = ImageFont.truetype("arial.ttf", 17), ImageFont.truetype("arialbd.ttf", 28)
except Exception: f = fb = ImageFont.load_default()
game = [("cast_alley_1.png", "Alley fight (in game)"), ("cast_alley_2.png", "Alley fight (in game)"), ("cast_miles.png", "Miles Corran (in game)"), ("cast_club_all.png", "Club fight (in game)"), ("cast_club_view.png", "Club fight (in game)")]
game = [(g, l) for g, l in game if (OUT / g).exists()]
GW, GH = 390, 844
cols = len(VIEWS)
W = 24 + cols * (TW + 8) + 24 + 2 * (GW + 10)
rows_h = len(CAST) * (TH + LAB + 8)
H = max(rows_h, 3 * (GH + 40)) + 90
img = Image.new("RGB", (W, H), (12, 11, 10)); d = ImageDraw.Draw(img)
d.text((24, 22), "NEON RAIN: the cast, v2 (Poly Haven fabrics, new hats, neon rim; CharMorph people, CMU mocap, <15k triangles each)", fill=(236, 222, 196), font=fb)
y = 80
for vid, label, pose, _ in CAST:
    d.text((24, y), label + "   [front, 3/4, side, back, " + pose + ", face]", fill=(232, 176, 64), font=f)
    for i in range(cols):
        img.paste(Image.open(TMP / f"{vid}_{i}.png").convert("RGB"), (24 + i * (TW + 8), y + LAB - 8))
    y += TH + LAB + 8
gx = 24 + cols * (TW + 8) + 24
for k, (g, l) in enumerate(game):
    col, row = k % 2, k // 2
    x0, y0 = gx + col * (GW + 10), 80 + row * (GH + 40)
    img.paste(Image.open(OUT / g).convert("RGB").resize((GW, GH), Image.LANCZOS), (x0, y0 + 26)); d.text((x0, y0), l, fill=(232, 176, 64), font=f)
img.save(OUT / "characters_v2.png")
print("wrote", OUT / "characters_v2.png", img.size, "ERRORS", len(errs)); [print(" ", e[:200]) for e in errs]
