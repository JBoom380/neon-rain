#!/bin/bash
# Full-length Vela idle (open lens default), Klein full-body start frame, clip1 recipe. Front of queue (urgent fix).
cd "$(dirname "$0")"
PF="A blonde 1940s woman stands in place, breathing slowly, she shifts her weight gently onto one hip and blinks, the long cigarette holder stays in her black gloved hand. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx vela_full_s81 81 "$PF" vp_vela_full.png 97 512 896 --front
echo ALLDONE
