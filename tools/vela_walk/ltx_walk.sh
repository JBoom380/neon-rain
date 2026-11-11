#!/bin/bash
# Vela front walk-in video takes: CLIP_RECIPE LTX settings, vela_full start frame, FIFO queue (no --front), one take at a time.
cd /c/Users/John/Documents/GitHub/projects/neon-rain-fps/tools/video_perf
P="Full-length shot. A blonde 1940s woman walks toward the camera with confident model strides, one foot stepping in front of the other, left, right, left, right, her hips swaying from side to side in her tight red satin pencil skirt, black high heels clicking, her free hand on her hip, the long cigarette holder in her other gloved hand. Her face stays exactly the same. The camera dollies backward ahead of her, keeping her whole body in frame. Film noir, plain grey studio background."
for s in ${SEEDS:-41 42 43 44 45}; do
  echo "take s$s $(date +%H:%M)"
  python gen.py ltx vela_walk_t$s $s "$P" vp_vela_full.png 97 512 896
done
echo LTX_WALK_DONE
