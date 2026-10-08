"""klein NAME SEED "prompt" SRC [W H]   |   ltx NAME SEED "prompt" SRC FRAMES [W H] [END]
ltx with END: first frame SRC and last frame END (LTXVAddGuide at frame -1, cropped before decode)."""
import json, sys, time, urllib.request

API = "http://127.0.0.1:8188"
FRONT = "--front" in sys.argv  # high-priority take: queue at the front (others' jobs are delayed, never cancelled)
if FRONT: sys.argv.remove("--front")


def run(wf):
    req = urllib.request.Request(API + "/prompt", data=json.dumps({"prompt": wf, **({"front": True} if FRONT else {})}).encode(), headers={"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req))
    if "error" in resp:
        print("ERROR", json.dumps(resp)[:1500]); sys.exit(1)
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(3)
        h = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                print("ERROR", json.dumps(st)[:2000]); sys.exit(1)
            outs = []
            for o in h[pid]["outputs"].values():
                for k in ("images", "videos", "gifs"):
                    for i in o.get(k, []):
                        outs.append((i.get("subfolder", ""), i["filename"]))
            print("done", round(time.time() - t0, 1), "s", outs); return


mode, name, seed, prompt, src = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]

if mode == "klein" and len(sys.argv) > 8:  # klein NAME SEED "prompt" SRC W H REF2: second reference image (face / identity)
    W, H = int(sys.argv[6]), int(sys.argv[7]); ref2 = sys.argv[8]
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-base-4b-fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "full_encoder_small_decoder.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": src}},
        "5": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["4", 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "24": {"class_type": "LoadImage", "inputs": {"image": ref2}},
        "25": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["24", 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}},
        "28": {"class_type": "VAEEncode", "inputs": {"pixels": ["25", 0], "vae": ["3", 0]}},
        "7": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
        "11": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["9", 0], "latent": ["8", 0]}},
        "21": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["11", 0], "latent": ["28", 0]}},
        "12": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["10", 0], "latent": ["8", 0]}},
        "22": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["12", 0], "latent": ["28", 0]}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "15": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["21", 0], "negative": ["22", 0], "cfg": 5.0}},
        "16": {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": W, "height": H}},
        "17": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["13", 0], "guider": ["15", 0], "sampler": ["14", 0], "sigmas": ["16", 0], "latent_image": ["7", 0]}},
        "18": {"class_type": "VAEDecode", "inputs": {"samples": ["17", 0], "vae": ["3", 0]}},
        "19": {"class_type": "SaveImage", "inputs": {"images": ["18", 0], "filename_prefix": f"vperf/{name}"}},
    }
elif mode == "klein":
    W, H = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (768, 1344)
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-base-4b-fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "full_encoder_small_decoder.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": src}},
        "5": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["4", 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}},
        "7": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
        "11": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["9", 0], "latent": ["8", 0]}},
        "12": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["10", 0], "latent": ["8", 0]}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "15": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["11", 0], "negative": ["12", 0], "cfg": 5.0}},
        "16": {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": W, "height": H}},
        "17": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["13", 0], "guider": ["15", 0], "sampler": ["14", 0], "sigmas": ["16", 0], "latent_image": ["7", 0]}},
        "18": {"class_type": "VAEDecode", "inputs": {"samples": ["17", 0], "vae": ["3", 0]}},
        "19": {"class_type": "SaveImage", "inputs": {"images": ["18", 0], "filename_prefix": f"vperf/{name}"}},
    }
else:
    frames = int(sys.argv[6])
    W, H = (int(sys.argv[7]), int(sys.argv[8])) if len(sys.argv) > 8 else (512, 896)
    neg = ("blurry, low quality, distorted, deformed face, morphing face, changing face, extra fingers, deformed hands, melting hands, "
           "extra limbs, watermark, text, jittery, flicker, morphing, warping, nudity, static image")
    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": src}},
        "10": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ltx-video-2b-v0.9.5.safetensors"}},
        "11": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5xxl_fp8_e4m3fn.safetensors", "type": "ltxv", "device": "default"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["11", 0], "text": prompt}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["11", 0], "text": neg}},
        "20": {"class_type": "ImageScale", "inputs": {"image": ["1", 0], "upscale_method": "lanczos", "width": W, "height": H, "crop": "center"}},
        "12": {"class_type": "LTXVPreprocess", "inputs": {"image": ["20", 0], "img_compression": 30}},
        "13": {"class_type": "LTXVImgToVideo", "inputs": {"positive": ["2", 0], "negative": ["3", 0], "vae": ["10", 2], "image": ["12", 0],
                                                          "width": W, "height": H, "length": frames, "batch_size": 1, "strength": 1.0}},
        "14": {"class_type": "LTXVConditioning", "inputs": {"positive": ["13", 0], "negative": ["13", 1], "frame_rate": 24.0}},
        "15": {"class_type": "LTXVScheduler", "inputs": {"steps": 30, "max_shift": 2.05, "base_shift": 0.95, "stretch": True, "terminal": 0.1, "latent": ["13", 2]}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "17": {"class_type": "CFGGuider", "inputs": {"model": ["10", 0], "positive": ["14", 0], "negative": ["14", 1], "cfg": 3.0}},
        "4": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "18": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["4", 0], "guider": ["17", 0], "sampler": ["16", 0], "sigmas": ["15", 0], "latent_image": ["13", 2]}},
        "19": {"class_type": "VAEDecode", "inputs": {"samples": ["18", 0], "vae": ["10", 2]}},
        "21": {"class_type": "CreateVideo", "inputs": {"images": ["19", 0], "fps": 24.0}},
        "22": {"class_type": "SaveVideo", "inputs": {"video": ["21", 0], "filename_prefix": f"vperf/{name}", "format": "mp4", "codec": "auto"}},
    }
if mode == "ltx" and len(sys.argv) > 9:
    end = sys.argv[9]
    wf["30"] = {"class_type": "LoadImage", "inputs": {"image": end}}
    wf["31"] = {"class_type": "ImageScale", "inputs": {"image": ["30", 0], "upscale_method": "lanczos", "width": W, "height": H, "crop": "center"}}
    wf["32"] = {"class_type": "LTXVPreprocess", "inputs": {"image": ["31", 0], "img_compression": 30}}
    wf["33"] = {"class_type": "LTXVAddGuide", "inputs": {"positive": ["13", 0], "negative": ["13", 1], "vae": ["10", 2], "latent": ["13", 2], "image": ["32", 0], "frame_idx": -1, "strength": 1.0}}
    wf["14"]["inputs"].update({"positive": ["33", 0], "negative": ["33", 1]})
    wf["15"]["inputs"]["latent"] = ["33", 2]
    wf["18"]["inputs"]["latent_image"] = ["33", 2]
    wf["34"] = {"class_type": "LTXVCropGuides", "inputs": {"positive": ["14", 0], "negative": ["14", 1], "latent": ["18", 0]}}
    wf["19"]["inputs"]["samples"] = ["34", 2]
run(wf)
