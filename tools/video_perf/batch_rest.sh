#!/bin/bash
# Resubmit: the batch-1 shell ended before the cold reaction; then the stole end frames (first/last-frame take).
cd "$(dirname "$0")"
CC="Close-up of a raven-haired 1940s woman holding a cigarette. She stares coldly at the camera, lifts her chin a little and blinks once slowly, a thin curl of smoke rises. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx dolores_cold_s43 43 "$CC" vp_dolores_close_cold.jpg 73 480 640
bash batch_stole3.sh
