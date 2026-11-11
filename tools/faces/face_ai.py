"""img2img of the front head renders with RealVisXL through the local ComfyUI API. usage: face_ai.py [denoise] [variants...]
front_<v>.png (768) -> ai_<v>.png (1024). One job at a time."""
import sys, os, json, time, io, urllib.request, uuid
from PIL import Image

S = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "art", "faces_work")).replace(chr(92), "/") + "/"  # work folder (art/ is not in the repo)
API = "http://127.0.0.1:8188"
DEN = float(sys.argv[1]) if len(sys.argv) > 1 else 0.48
ALL = ["thug_a", "thug_b", "thug_c", "gale_a", "gale_b", "gale_c"]
VAR = sys.argv[2:] or ALL
BASE = "front view portrait photograph of a man's face, {who}, 1940s, film noir crime drama, detailed skin with pores, sharp eyes with catch light, defined eyebrows, natural lips, even soft frontal light, symmetrical, head centred, plain black background, 85mm, photorealistic"
WHO = {"thug_a": "a rough street thug in his thirties, heavy stubble, broken nose, tired mean eyes",
       "thug_b": "a hard street thug in his forties, dark stubble, scar through one eyebrow, heavy brow",
       "thug_c": "a young wiry street thug, thin stubble, hollow cheeks, cold stare",
       "gale_a": "a clean-shaven gangster gunman in his thirties, slick dark hair, cold confident eyes",
       "gale_b": "a heavyset gangster enforcer in his forties, clean-shaven, thick neck, small hard eyes",
       "gale_c": "an older grey-haired gangster hitman, clean-shaven, lined face, pale calm eyes"}
NEG = "smile, teeth, makeup, woman, glasses, hat, hands, side light, strong shadows, text, watermark, cartoon, painting, 3d render, plastic skin, blurry, deformed, extra eyes"


def post(path, data, ctype="application/json"):
    r = urllib.request.Request(API + path, data=data, headers={"Content-Type": ctype}); return json.loads(urllib.request.urlopen(r, timeout=60).read())


def upload(path, name):
    b = "----nr" + uuid.uuid4().hex; body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode() + open(path, "rb").read() + (f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n").encode()
    return post("/upload/image", body, "multipart/form-data; boundary=" + b)["name"]


for v in VAR:
    src = Image.open(S + f"front_{v}.png").convert("RGB").resize((1024, 1024), Image.LANCZOS); src.save(S + f"front1024_{v}.png")
    name = upload(S + f"front1024_{v}.png", f"nr_front_{v}.png")
    wf = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
          "2": {"class_type": "CLIPTextEncode", "inputs": {"text": BASE.format(who=WHO[v]), "clip": ["1", 1]}},
          "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["1", 1]}},
          "4": {"class_type": "LoadImage", "inputs": {"image": name}},
          "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["1", 2]}},
          "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["5", 0], "seed": 4107 + ALL.index(v), "steps": 26, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": DEN}},
          "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
          "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": f"nr_face_{v}"}}}
    t0 = time.time(); pid = post("/prompt", json.dumps({"prompt": wf}).encode())["prompt_id"]
    while True:
        h = json.loads(urllib.request.urlopen(API + "/history/" + pid, timeout=30).read())
        if pid in h and h[pid].get("outputs"): break
        if pid in h and h[pid].get("status", {}).get("status_str") == "error": raise SystemExit("comfy error " + json.dumps(h[pid]["status"])[:400])
        if time.time() - t0 > 900: raise SystemExit("timeout")
        time.sleep(2)
    im = h[pid]["outputs"]["8"]["images"][0]
    data = urllib.request.urlopen(f"{API}/view?filename={im['filename']}&subfolder={im['subfolder']}&type={im['type']}", timeout=60).read()
    Image.open(io.BytesIO(data)).convert("RGB").save(S + f"ai_{v}.png"); print(v, f"{time.time() - t0:.0f} s", flush=True)
