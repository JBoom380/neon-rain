"""Neon Rain hub cover options, txt2img RealVisXL 1344x768. Usage: python cover_gen.py NAME SEED "prompt" """
import json, sys, time, urllib.request
API = "http://127.0.0.1:8188"
name, seed, pos = sys.argv[1], int(sys.argv[2]), sys.argv[3]
NEG = ("text, letters, words, watermark, logo, signature, nude, cleavage, colorful, pink, cartoon, anime, deformed, extra fingers, "
       "blurry, lowres, modern clothes, smartphone")
STYLE = (", 1940s film noir movie still, black and white photograph with deep blacks, only the red kept in color, hard light, "
         "venetian blind shadows or rain, cinematic composition, 35mm film grain, masterpiece")
wf = {
  "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
  "2": {"class_type": "EmptyLatentImage", "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
  "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": pos + STYLE}},
  "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
  "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["2", 0],
        "seed": seed, "steps": 30, "cfg": 5.5, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
  "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
  "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": f"neonrain_covers/{name}"}},
}
for i in range(90):
    try: urllib.request.urlopen(API + "/system_stats", timeout=3); break
    except Exception: time.sleep(2)
r = json.load(urllib.request.urlopen(urllib.request.Request(API + "/prompt", data=json.dumps({"prompt": wf}).encode(), headers={"Content-Type": "application/json"})))
pid = r["prompt_id"]
while True:
    time.sleep(2)
    h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
    if pid in h:
        print("done", name); break
