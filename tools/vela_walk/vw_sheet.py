"""Contact sheet: vw_sheet.py OUT.png DIR1[:prefix] [DIR2 ...] [--scale 0.25] [--bg 90]
Each DIR becomes one row of its <prefix>_NN.png frames (default prefix color), composited on grey."""
import sys, os, glob
from PIL import Image, ImageDraw
args = sys.argv[1:]; scale = 0.25; bgv = 90
if '--scale' in args: i = args.index('--scale'); scale = float(args[i + 1]); del args[i:i + 2]
if '--bg' in args: i = args.index('--bg'); bgv = int(args[i + 1]); del args[i:i + 2]
out, rows = args[0], args[1:]
R = []
for r in rows:
    d, _, pre = r.partition(':'); pre = pre or 'color'
    fs = sorted(glob.glob(os.path.join(d, pre + '_*.png')))
    ims = []
    for f in fs:
        im = Image.open(f).convert('RGBA'); bg = Image.new('RGBA', im.size, (bgv, bgv, bgv + 4, 255)); bg.alpha_composite(im)
        ims.append(bg.convert('RGB').resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS))
    R.append((r, ims))
cw = max(im.width for _, ims in R for im in ims); ch = max(im.height for _, ims in R for im in ims)
ncol = max(len(ims) for _, ims in R)
sheet = Image.new('RGB', (cw * ncol, (ch + 14) * len(R)), (20, 20, 24)); dr = ImageDraw.Draw(sheet)
for ri, (name, ims) in enumerate(R):
    y = ri * (ch + 14); dr.text((3, y), name[-60:], fill=(230, 200, 120))
    for ci, im in enumerate(ims): sheet.paste(im, (ci * cw, y + 14))
sheet.save(out); print(out, sheet.size)
