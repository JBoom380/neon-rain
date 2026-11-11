"""Identity key: repaint one frame of a sequence with FLUX.2 Klein, the frame itself as pose reference and FAV1 as the identity
reference (face, golden pin curls, warm skin). The result replaces CUTDIR/<set>/a<az>/cut_KK.png (3D matte kept), so vw_prop.py
carries it to every frame. Usage: vw_klein.py GUIDEDIR CUTDIR --set walk --angles 90,135 [--key -1] [--seed 7]"""
import os, sys, json, argparse
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vw_paint as VP
FAV1 = r'C:\Users\John\Documents\GitHub\projects\neon-rain-fps\art\vela_favorites\FAV1_blonde_seed52.png'
P = ("Keep the first image exactly: the same pose, the same body outline, the same position and size in the frame, the same black satin halter top, "
     "red satin pencil skirt, black opera gloves, long cigarette holder, black high heels and plain flat grey background. Make her the woman in the second "
     "image: the same face, the same glossy golden blonde 1940s pin curls, the same warm peach skin and red lips. Painted as a 1940s pulp noir illustration, "
     "soft studio light. Classy, fully clothed.")
def klein(img_a, img_b, seed, W=512, H=1024):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-base-4b-fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "full_encoder_small_decoder.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": img_a}},
        "5": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["4", 0], "upscale_method": "lanczos", "megapixels": 0.5, "resolution_steps": 16}},
        "8": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "24": {"class_type": "LoadImage", "inputs": {"image": img_b}},
        "25": {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["24", 0], "upscale_method": "lanczos", "megapixels": 0.6, "resolution_steps": 16}},
        "28": {"class_type": "VAEEncode", "inputs": {"pixels": ["25", 0], "vae": ["3", 0]}},
        "7": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": P}},
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
        "19": {"class_type": "SaveImage", "inputs": {"images": ["18", 0], "filename_prefix": "neonrain/vw_klein"}}}
    return VP.run(wf)
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('guides'); ap.add_argument('cut')
    ap.add_argument('--set', default='walk'); ap.add_argument('--angles', default='90'); ap.add_argument('--key', type=int, default=-1); ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    fav = VP.upload(Image.open(FAV1).convert('RGB'), 'vw_fav1.png')
    for az in [int(x) for x in a.angles.split(',')]:
        cd = os.path.join(a.cut, a.set, 'a%03d' % az); gd = os.path.join(a.guides, a.set, 'a%03d' % az)
        n = len([f for f in os.listdir(cd) if f.startswith('cut_')])
        C = [cv2.imread(os.path.join(cd, 'cut_%02d.png' % i), cv2.IMREAD_UNCHANGED).astype(np.float32) for i in range(n)]
        k = a.key
        if k < 0:
            med = np.median(np.stack([c[..., :3] for c in C]), 0); k = int(np.argmin([np.abs(c[..., :3] - med).mean() for c in C]))
        c = C[k]; al = c[..., 3:4] / 255; bgr = c[..., :3] * al + np.array([80, 74, 74], np.float32) * (1 - al)
        src = VP.upload(Image.fromarray(cv2.cvtColor(bgr.astype(np.uint8), cv2.COLOR_BGR2RGB)), 'vw_klein_src.png')
        out, dt = klein(src, fav, a.seed + az)
        o = cv2.cvtColor(np.asarray(out.resize((512, 1024), Image.LANCZOS)), cv2.COLOR_RGB2BGR).astype(np.float32)
        g = cv2.imread(os.path.join(gd, 'color_%02d.png' % k), cv2.IMREAD_UNCHANGED)
        cv2.imwrite(os.path.join(cd, 'klein_src_%02d.png' % k), c.astype(np.uint8))
        cv2.imwrite(os.path.join(cd, 'cut_%02d.png' % k), np.dstack([o, c[..., 3]]).astype(np.uint8))
        json.dump({'key': k}, open(os.path.join(cd, 'key.json'), 'w'))
        print('[klein]', a.set, az, 'key', k, '%.0fs' % dt, flush=True)
