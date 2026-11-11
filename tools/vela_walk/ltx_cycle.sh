#!/bin/bash
# Filmed gait cycle: LTX (CLIP_RECIPE settings) between consecutive Klein stride keys, first + last frame guides. FIFO, one at a time.
# usage: ltx_cycle.sh SEEDKEY SEED  (keys/key_PP_sSEEDKEY.png)
K=$1; S=${2:-7}
V=/c/Users/John/Documents/GitHub/projects/neon-rain-fps/art/motion/vela
IN=/e/ComfyUI_windows_portable/ComfyUI/input
cd /c/Users/John/Documents/GitHub/projects/neon-rain-fps/tools/video_perf
for p in 00 04 08 12; do cp $V/keys/key_${p}_s$K.png $IN/vw_wk_${p}_s$K.png; done
P="A blonde 1940s woman takes one graceful step toward the camera in black high heels, her legs swing naturally in her tight red satin pencil skirt, hips sway. Her face stays exactly the same. Smooth natural motion. The camera does not move. Film noir, plain grey studio background."
for seg in "00 04" "04 08" "08 12" "12 00"; do set -- $seg
  python gen.py ltx vw_cyc_k${K}_s${S}_$1 $S "$P" vw_wk_$1_s$K.png 9 512 896 vw_wk_$2_s$K.png
done
echo CYCLE_DONE
