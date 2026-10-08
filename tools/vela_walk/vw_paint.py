"""Paint Vela frames over the 3D guides with SDXL (RealVisXL) + ControlNet union (depth + openpose) in the local ComfyUI.
Usage: vw_paint.py GUIDEDIR OUTDIR --set walk --angles 0,45 --frames 0-15 [--denoise 0.5] [--seed 52] [--tag t]
Reads GUIDEDIR/<set>/a<az>/{color,depth,pose}_NN.png; writes OUTDIR/<set>/a<az>/paint_NN.png (raw, on grey).
Queues politely: one job at a time, appended to the shared FIFO queue."""
import os, sys, json, time, uuid, argparse, io, urllib.request, urllib.parse
from PIL import Image
URL = "http://127.0.0.1:8188"; CID = str(uuid.uuid4())
BG = (74, 74, 80)
WHO = ("a glamorous curvy young woman in her twenties with soft platinum blonde 1940s pin curls, fair porcelain skin, red lipstick, smoky eyes, "
       "wearing a black satin halter top with a deep V neckline, a tight red satin knee-length pencil skirt, long black satin opera gloves "
       "and black patent high-heeled pumps, one gloved hand raised holding a long black cigarette holder")
STYLE = ("1940s pulp noir paperback cover oil painting, painterly brushstrokes, soft studio key light with a warm rim light, full body head to toe, "
         "plain flat grey background, elegant, beautiful face")
VIEW = {0: "facing the viewer, front view", 45: "three-quarter front view, turned to her left", 90: "side profile view, facing left",
        135: "three-quarter back view, seen from behind", 180: "back view, seen from behind, back of her head", 225: "three-quarter back view, seen from behind",
        270: "side profile view, facing right", 315: "three-quarter front view, turned to her right"}
ACT = {'walk': "walking gracefully, mid stride", 'stop': "walking then stopping", 'idle': "standing still in a relaxed elegant pose", 'pose': "standing still in a relaxed elegant pose"}
NEG = ("nude, naked, nipples, lowres, blurry, deformed, disfigured, bad anatomy, extra limbs, extra fingers, mutated hands, ugly face, cross-eyed, "
       "cartoon, anime, 3d render, cgi, plastic, doll, text, watermark, frame, multiple people, cropped")

def _req(path, data=None, headers=None, timeout=120):
    r = urllib.request.Request(URL + path, data=data, headers=headers or {})
    with urllib.request.urlopen(r, timeout=timeout) as f: return f.read()
def upload(img, name):
    buf = io.BytesIO(); img.save(buf, 'PNG'); b = "----vw" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n").encode()
    body += buf.getvalue() + f"\r\n--{b}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n".encode()
    return json.loads(_req("/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={b}"}))["name"]
def run(wf, timeout=14400, pid=None):
    # one job of ours at a time, appended to the shared FIFO queue behind other agents' jobs
    if pid is None:
        r = json.loads(_req("/prompt", json.dumps({"prompt": wf, "client_id": CID}).encode(), {"Content-Type": "application/json"}))
        if "error" in r: raise RuntimeError(json.dumps(r)[:2000])
        pid = r["prompt_id"]; print('[queued]', pid, flush=True)
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(_req(f"/history/{pid}"))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error": raise RuntimeError(json.dumps(st)[:3000])
            for o in h[pid]["outputs"].values():
                for f in o.get("images", []):
                    q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                    return Image.open(io.BytesIO(_req("/view?" + q))).convert('RGB'), time.time() - t0
        time.sleep(2)
    raise TimeoutError(pid)

def wf_paint(init, depth, pose, pos, seed, denoise, steps, cfg, s_depth, s_pose, end_depth, end_pose, prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": pos}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
        "4": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "xinsir-controlnet-union-sdxl-promax.safetensors"}},
        "5": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["4", 0], "type": "depth"}},
        "6": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["4", 0], "type": "openpose"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": init}},
        "11": {"class_type": "LoadImage", "inputs": {"image": depth}},
        "12": {"class_type": "LoadImage", "inputs": {"image": pose}},
        "13": {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": ["2", 0], "negative": ["3", 0], "control_net": ["5", 0], "image": ["11", 0],
                                                                    "strength": s_depth, "start_percent": 0.0, "end_percent": end_depth, "vae": ["1", 2]}},
        "14": {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": ["13", 0], "negative": ["13", 1], "control_net": ["6", 0], "image": ["12", 0],
                                                                    "strength": s_pose, "start_percent": 0.0, "end_percent": end_pose, "vae": ["1", 2]}},
        "15": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["1", 2]}},
        "16": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["14", 0], "negative": ["14", 1], "latent_image": ["15", 0], "seed": seed,
                                                    "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": denoise}},
        "17": {"class_type": "VAEDecode", "inputs": {"samples": ["16", 0], "vae": ["1", 2]}},
        "18": {"class_type": "SaveImage", "inputs": {"images": ["17", 0], "filename_prefix": prefix}},
    }

def wf_batch(jobs, pos, seed, denoise, steps, cfg, s_depth, s_pose, end_depth, end_pose, prefix):
    """jobs: list of (key, init, depth, pose) uploaded names; one queue item paints them all"""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
        "4": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "xinsir-controlnet-union-sdxl-promax.safetensors"}},
        "5": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["4", 0], "type": "depth"}},
        "6": {"class_type": "SetUnionControlNetType", "inputs": {"control_net": ["4", 0], "type": "openpose"}}}
    save = {}; penc = {}
    for n, job in enumerate(jobs):
        key, init, depth, pose = job[:4]; jp = job[4] if len(job) > 4 else pos; js = job[5] if len(job) > 5 else seed
        if jp not in penc:
            pid = str(20 + len(penc)); wf[pid] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": jp}}; penc[jp] = pid
        b = 100 + n * 10; B = lambda k: str(b + k)
        wf[B(0)] = {"class_type": "LoadImage", "inputs": {"image": init}}
        wf[B(1)] = {"class_type": "LoadImage", "inputs": {"image": depth}}
        wf[B(2)] = {"class_type": "LoadImage", "inputs": {"image": pose}}
        wf[B(3)] = {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": [penc[jp], 0], "negative": ["3", 0], "control_net": ["5", 0], "image": [B(1), 0],
                    "strength": s_depth, "start_percent": 0.0, "end_percent": end_depth, "vae": ["1", 2]}}
        wf[B(4)] = {"class_type": "ControlNetApplyAdvanced", "inputs": {"positive": [B(3), 0], "negative": [B(3), 1], "control_net": ["6", 0], "image": [B(2), 0],
                    "strength": s_pose, "start_percent": 0.0, "end_percent": end_pose, "vae": ["1", 2]}}
        wf[B(5)] = {"class_type": "VAEEncode", "inputs": {"pixels": [B(0), 0], "vae": ["1", 2]}}
        wf[B(6)] = {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": [B(4), 0], "negative": [B(4), 1], "latent_image": [B(5), 0], "seed": js,
                    "steps": steps, "cfg": cfg, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": denoise}}
        wf[B(7)] = {"class_type": "VAEDecode", "inputs": {"samples": [B(6), 0], "vae": ["1", 2]}}
        wf[B(8)] = {"class_type": "SaveImage", "inputs": {"images": [B(7), 0], "filename_prefix": prefix + "_" + key}}
        save[B(8)] = key
    return wf, save

def _submit(wf):
    r = json.loads(_req("/prompt", json.dumps({"prompt": wf, "client_id": CID}).encode(), {"Content-Type": "application/json"}))
    if "error" in r: raise RuntimeError(json.dumps(r)[:2000])
    print('[queued]', r["prompt_id"], flush=True); return r["prompt_id"]

def run_batch(wf, save, timeout=36000):
    """survives ComfyUI restarts: polling errors are retried; a job that vanished from queue and history is resubmitted"""
    pid = None; t0 = time.time(); last_check = 0
    while time.time() - t0 < timeout:
        try:
            if pid is None: pid = _submit(wf)
            h = json.loads(_req(f"/history/{pid}"))
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error": raise RuntimeError(json.dumps(st)[:3000])
                res = {}
                for nid, o in h[pid]["outputs"].items():
                    for f in o.get("images", []):
                        q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                        res[save[nid]] = Image.open(io.BytesIO(_req("/view?" + q))).convert('RGB')
                return res, time.time() - t0
            if time.time() - last_check > 60:
                last_check = time.time(); q = json.loads(_req("/queue"))
                if not any(it[1] == pid for k in ('queue_running', 'queue_pending') for it in q[k]):
                    time.sleep(5)
                    if pid not in json.loads(_req(f"/history/{pid}")): print('[lost] resubmitting', flush=True); pid = None
        except (OSError, ValueError) as e:
            print('[comfy unreachable]', type(e).__name__, flush=True); time.sleep(20)
        time.sleep(3)
    raise TimeoutError(pid)

def on_bg(p, bg):
    im = Image.open(p).convert('RGBA'); b = Image.new('RGBA', im.size, bg + (255,)); b.alpha_composite(im); return b.convert('RGB')

def frange(s, n):
    if not s: return list(range(n))
    out = []
    for part in s.split(','):
        if '-' in part: a, b = part.split('-'); out += list(range(int(a), int(b) + 1))
        else: out.append(int(part))
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('guides'); ap.add_argument('out')
    ap.add_argument('--set', default='walk'); ap.add_argument('--angles', default='0'); ap.add_argument('--frames', default='')
    ap.add_argument('--denoise', type=float, default=0.5); ap.add_argument('--seed', type=int, default=52); ap.add_argument('--steps', type=int, default=0)
    ap.add_argument('--cfg', type=float, default=5.5); ap.add_argument('--sd', type=float, default=0.55); ap.add_argument('--sp', type=float, default=0.5)
    ap.add_argument('--ed', type=float, default=0.8); ap.add_argument('--ep', type=float, default=0.7)
    ap.add_argument('--init', default='color'); ap.add_argument('--group', type=int, default=1); ap.add_argument('--extra', default=''); ap.add_argument('--tag', default='')
    a = ap.parse_args()
    if not a.steps: a.steps = 16 if a.denoise <= 0.35 else 22  # KSampler runs every step even at low denoise
    angs = [int(x) for x in a.angles.split(',')]
    for g0 in range(0, len(angs), a.group):
        jobs = []
        for az in angs[g0:g0 + a.group]:
            gd = os.path.join(a.guides, a.set, 'a%03d' % az); od = os.path.join(a.out, a.set, 'a%03d' % az); os.makedirs(od, exist_ok=True)
            n = len([f for f in os.listdir(gd) if f.startswith('color_')])
            pos = f"{WHO}, {ACT[a.set]}, {VIEW[az]}, {STYLE}{', ' + a.extra if a.extra else ''}"
            for i in frange(a.frames, n):
                out = os.path.join(od, 'paint_%02d%s.png' % (i, a.tag))
                if os.path.exists(out): continue
                k = '%s_a%03d_%02d' % (a.set, az, i)
                ip = os.path.join(gd, '%s_%02d.png' % (a.init, i)) if not os.path.isdir(a.init) else os.path.join(a.init, a.set, 'a%03d' % az, 'init_%02d.png' % i)
                jobs.append((k, upload(on_bg(ip, BG), 'vw_init_' + k + '.png'), upload(on_bg(os.path.join(gd, 'depth_%02d.png' % i), (0, 0, 0)), 'vw_depth_' + k + '.png'),
                             upload(Image.open(os.path.join(gd, 'pose_%02d.png' % i)).convert('RGB'), 'vw_pose_' + k + '.png'), pos, a.seed + az, out))
        if not jobs: continue
        wf, save = wf_batch([j[:6] for j in jobs], None, a.seed, a.denoise, a.steps, a.cfg, a.sd, a.sp, a.ed, a.ep, 'neonrain/vw')
        res, dt = run_batch(wf, save)
        for j in jobs: res[j[0]].save(j[6])
        print('[paint]', a.set, angs[g0:g0 + a.group], len(jobs), 'frames %.0fs' % dt, flush=True)
