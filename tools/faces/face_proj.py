"""Enemy face textures by front projection.
  extract : per variant, render the head from the front (ortho) with its own texture -> front_<v>.png + geo_<v>.npz
  apply   : project ai_<v>.png back onto the colour texture (front-facing head texels only, feathered) -> out/<v>_col.jpg
usage: face_proj.py extract|apply
Variants: thug_a, thug_b, thug_c (thugs.glb), gale_a, gale_b, gale_c (gale.glb)."""
import sys, json, struct, io, os
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")).replace(chr(92), "/") + "/"
S = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "art", "faces_work")).replace(chr(92), "/") + "/"  # work folder (art/ is not in the repo)
FAM = {"thug_a": "thugs", "thug_b": "thugs", "thug_c": "thugs", "gale_a": "gale", "gale_b": "gale", "gale_c": "gale"}
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
RES = 768


def load(fam):
    b = open(ROOT + f"assets/models/cast/{fam}.glb", "rb").read(); n = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + n]), b, 20 + n + 8


def acc(j, b, bin0, i):
    a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]; dt = np.dtype(CT[a["componentType"]]); nc = NC[a["type"]]
    off = bin0 + bv.get("byteOffset", 0) + a.get("byteOffset", 0); stride = bv.get("byteStride") or dt.itemsize * nc
    raw = np.frombuffer(b, np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * nc, offset=off)
    idx = (np.arange(a["count"])[:, None] * stride + np.arange(dt.itemsize * nc)[None, :]).ravel()
    out = raw[idx].view(dt).reshape(a["count"], nc).astype(np.float64 if dt != np.uint32 and dt.kind == "f" else dt)
    if a.get("normalized"): out = out.astype(np.float64) / np.iinfo(dt).max
    return out


def image(j, b, bin0, name):
    im = next(x for x in j["images"] if x["name"] == name); bv = j["bufferViews"][im["bufferView"]]
    return Image.open(io.BytesIO(b[bin0 + bv.get("byteOffset", 0): bin0 + bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB")


def head_geo(v):
    j, b, bin0 = load(FAM[v])
    mi = next(i for i, m in enumerate(j["materials"]) if m["name"] == v + "_mat")
    names = [n.get("name", "") for n in j["nodes"]]
    kids = {i: n.get("children", []) for i, n in enumerate(j["nodes"])}
    head = names.index("spine_006"); desc = set(); st = [head]
    while st:
        x = st.pop(); desc.add(x); st += kids[x]
    P, N, UV, TRI = [], [], [], []; base = 0
    for ni, node in enumerate(j["nodes"]):
        if "mesh" not in node or "_lod1" in node.get("name", ""): continue
        skin = j["skins"][node["skin"]] if "skin" in node else None
        for pr in j["meshes"][node["mesh"]]["primitives"]:
            if pr.get("material") != mi or skin is None: continue
            A = pr["attributes"]; p = acc(j, b, bin0, A["POSITION"]); nn = acc(j, b, bin0, A["NORMAL"]); uv = acc(j, b, bin0, A["TEXCOORD_0"])
            jo = acc(j, b, bin0, A["JOINTS_0"]).astype(int); w = acc(j, b, bin0, A["WEIGHTS_0"]).astype(np.float64); ix = acc(j, b, bin0, pr["indices"]).astype(int).reshape(-1, 3)
            isHead = np.isin(np.array(skin["joints"])[jo], list(desc)); hw = (w * isHead).sum(1) / np.maximum(w.sum(1), 1e-9)
            keep = (hw[ix] > 0.6).all(1)
            P.append(p); N.append(nn); UV.append(uv); TRI.append(ix[keep] + base); base += len(p)
    P, N, UV, TRI = np.concatenate(P), np.concatenate(N), np.concatenate(UV), np.concatenate(TRI)
    return P, N, UV, TRI, image(j, b, bin0, v + "_col")


def raster(tri_xy, tri_attr, size, zs=None):
    """Rasterize triangles (pixel coords) with per-vertex attributes; returns attr image and coverage. zs: per-vertex depth (larger wins)."""
    H = W = size; out = np.zeros((H, W, tri_attr.shape[2]), np.float64); cov = np.zeros((H, W), bool); zb = np.full((H, W), -1e9)
    for t in range(len(tri_xy)):
        (x0, y0), (x1, y1), (x2, y2) = tri_xy[t]; minx, maxx = int(max(0, np.floor(min(x0, x1, x2)))), int(min(W - 1, np.ceil(max(x0, x1, x2)))); miny, maxy = int(max(0, np.floor(min(y0, y1, y2)))), int(min(H - 1, np.ceil(max(y0, y1, y2))))
        if maxx < minx or maxy < miny: continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-12: continue
        xs, ys = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
        a = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / den; bb = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / den; c = 1 - a - bb
        m = (a >= -1e-4) & (bb >= -1e-4) & (c >= -1e-4)
        if not m.any(): continue
        val = a[..., None] * tri_attr[t, 0] + bb[..., None] * tri_attr[t, 1] + c[..., None] * tri_attr[t, 2]
        if zs is not None:
            z = a * zs[t, 0] + bb * zs[t, 1] + c * zs[t, 2]; sub = zb[miny:maxy + 1, minx:maxx + 1]; m &= z > sub; sub[m] = z[m]
        out[miny:maxy + 1, minx:maxx + 1][m] = val[m]; cov[miny:maxy + 1, minx:maxx + 1][m] = True
    return out, cov


def bilinear(img, u, v):
    h, w = img.shape[:2]; x = np.clip(u * w - 0.5, 0, w - 1.001); y = np.clip(v * h - 0.5, 0, h - 1.001); x0, y0 = x.astype(int), y.astype(int); fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy


def frame(P, N, TRI):
    """front = +Z if the mean head normal of the nose-side points that way; returns projection params"""
    used = np.unique(TRI); p = P[used]
    lo, hi = p.min(0), p.max(0); c = (lo + hi) / 2; half = max(hi[0] - lo[0], hi[1] - lo[1]) / 2 * 1.12
    return c, half


def extract():
    for v in FAM:
        P, N, UV, TRI, tex = head_geo(v); c, half = frame(P, N, TRI); T = np.asarray(tex, np.float64) / 255
        # the face looks along the axis where the head's front normals carry the eyes: try +Z and -Z, keep the one whose projected image has more texture contrast
        best = None
        for sgn in (1, -1):
            xy = np.stack([(P[:, 0] * sgn - c[0] * sgn) / half * 0.5 + 0.5, 0.5 - (P[:, 1] - c[1]) / half * 0.5], 1) * RES
            fr = N[:, 2] * sgn; tk = TRI[(fr[TRI] > 0.05).any(1)]
            img, cov = raster(xy[tk], UV[tk], RES, zs=(P[:, 2] * sgn)[tk])
            col = bilinear(T, img[..., 0], img[..., 1]) * cov[..., None]; score = col[cov].std() if cov.any() else 0
            if best is None or score > best[0]: best = (score, sgn, col, cov)
        _, sgn, col, cov = best
        Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(S + f"front_{v}.png")
        np.savez(S + f"geo_{v}.npz", c=c, half=half, sgn=sgn); print(v, "head tris", len(TRI), "front sign", sgn, "coverage", round(cov.mean(), 3))


def apply():
    os.makedirs(S + "out", exist_ok=True)
    for v in FAM:
        if not os.path.exists(S + f"ai_{v}.png"): print(v, "no ai image, skipped"); continue
        P, N, UV, TRI, tex = head_geo(v); g = np.load(S + f"geo_{v}.npz"); c, half, sgn = g["c"], float(g["half"]), float(g["sgn"])
        T = np.asarray(tex, np.float64) / 255; SZ = T.shape[0]
        ai = np.asarray(Image.open(S + f"ai_{v}.png").convert("RGB").resize((RES, RES), Image.LANCZOS), np.float64) / 255
        src = np.asarray(Image.open(S + f"front_{v}.png").convert("RGB"), np.float64) / 255; m = src.sum(2) > 0.02
        for ch in range(3):  # keep the skin tone of the model: match mean and spread inside the face
            a, s0 = ai[..., ch][m], src[..., ch][m]; ai[..., ch] = (ai[..., ch] - a.mean()) / (a.std() + 1e-6) * (s0.std() * 1.25 + 1e-6) + s0.mean()
        ai = np.clip(ai, 0, 1)
        px = np.stack([(P[:, 0] * sgn - c[0] * sgn) / half * 0.5 + 0.5, 0.5 - (P[:, 1] - c[1]) / half * 0.5, N[:, 2] * sgn], 1)
        uvpx = np.stack([UV[:, 0] * SZ, UV[:, 1] * SZ], 1)
        attr, cov = raster(uvpx[TRI], px[TRI], SZ)
        u, w_, fz = attr[..., 0], attr[..., 1], attr[..., 2]
        wgt = np.clip((fz - 0.3) / 0.35, 0, 1) * cov; edge = np.minimum.reduce([u, 1 - u, w_, 1 - w_]); wgt *= np.clip(edge / 0.06, 0, 1)
        wgt = wgt * wgt * (3 - 2 * wgt)
        new = bilinear(ai, np.clip(u, 0, 1), np.clip(w_, 0, 1)); out = T * (1 - wgt[..., None]) + new * wgt[..., None]
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(S + f"out/{v}_col.jpg", quality=92)
        # roughness map: the shader reads R near 0.45 as skin (matte, no hard highlight); the stubble area was not marked, so the face texels get the marker
        j, bb, bin0 = load(FAM[v]); rm = np.asarray(image(j, bb, bin0, v + "_rm"), np.float64); RS = rm.shape[0]
        attr2, cov2 = raster(np.stack([UV[:, 0] * RS, UV[:, 1] * RS], 1)[TRI], px[TRI], RS)
        w2 = np.clip((attr2[..., 2] - 0.1) / 0.3, 0, 1) * cov2
        rm[..., 0] = rm[..., 0] * (1 - w2) + 115.0 * w2
        Image.fromarray(np.clip(rm, 0, 255).astype(np.uint8)).save(S + f"out/{v}_rm.png")
        print(v, "texels painted", int((wgt > 0.05).sum()))


if __name__ == "__main__":
    {"extract": extract, "apply": apply}[sys.argv[1]]()
