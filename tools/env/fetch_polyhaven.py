"""Download the CC0 Poly Haven models (glTF, 1k textures) and PBR textures (1k) the NEON RAIN environment pass uses.
Output: art/env_src/models/<id>/<id>.gltf (+ bin + textures), art/env_src/tex/<id>_{diff,nor_gl,rough}_1k.jpg.
art/ is gitignored: these are build inputs; the baked GLBs in assets/models/ are what ships.
Usage: python tools/env/fetch_polyhaven.py"""
import json, pathlib, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "art" / "env_src"
UA = {"User-Agent": "neon-rain-env-pass/1.0"}

MODELS = [
    # office
    "modern_arm_chair_01", "GreenChair_01", "vintage_wooden_drawer_01", "wooden_bookshelf_worn", "book_encyclopedia_set_01",
    "side_table_01", "Sofa_01", "ceiling_fan", "standing_picture_frame_01", "hanging_picture_frame_01", "office_notepads",
    "clipboard", "vintage_lighter", "wine_bottles_01", "binder_notebook",
    # alley
    "metal_trash_can", "modular_fire_escape", "barrel_03", "wooden_crate_01", "cardboard_box_01", "modular_metal_gutter",
    "industrial_wall_lamp", "water_manhole_cover", "trashbag", "modular_industrial_pipes_01", "old_tyre", "street_lamp_01",
    # club
    "round_wooden_table_01", "bar_chair_round_01", "Chandelier_02", "ornate_mirror_01", "chinese_screen_panels",
]
TEXTURES = [
    "wood_floor_worn", "plastered_wall_04", "brown_planks_05", "black_painted_planks", "white_plaster_02", "black_walnut_veneer_01",
    "red_brick_03", "dark_brick_wall", "asphalt_02", "green_metal_rust", "rusty_metal_shutter", "concrete_wall_006",
    "herringbone_parquet", "dirty_carpet", "velour_velvet", "leather_red_02", "marble_01", "dark_wooden_planks", "patterned_plaster_wall",
    "rusty_metal_02",
]


def get(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers=UA)
    dest.write_bytes(urllib.request.urlopen(req, timeout=120).read())


def api(asset):
    req = urllib.request.Request(f"https://api.polyhaven.com/files/{asset}", headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def fetch_model(mid):
    g = api(mid)["gltf"]["1k"]["gltf"]
    base = OUT / "models" / mid
    get(g["url"], base / pathlib.Path(g["url"]).name)
    for rel, info in g["include"].items():
        get(info["url"], base / rel)
    return mid


def fetch_tex(tid):
    f = api(tid)
    if "Diffuse" not in f and "coll1" in f:  # colour-variant sets (e.g. leather_red_02) ship coll1/coll2 instead
        f["Diffuse"] = f["coll1"]
    for key, name in (("Diffuse", "diff"), ("nor_gl", "nor_gl"), ("Rough", "rough")):
        if key in f and "1k" in f[key]:
            get(f[key]["1k"]["jpg"]["url"], OUT / "tex" / f"{tid}_{name}_1k.jpg")
    return tid


if __name__ == "__main__":
    only = set(sys.argv[1:])
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(fetch_model, [m for m in MODELS if not only or m in only]):
            print("model", r)
        for r in ex.map(fetch_tex, [t for t in TEXTURES if not only or t in only]):
            print("tex", r)
