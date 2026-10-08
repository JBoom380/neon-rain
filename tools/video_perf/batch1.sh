#!/bin/bash
# Video-performance batch 1: new start frames (FLUX.2 Klein) and LTX clips at the vela_clip1 recipe.
cd "$(dirname "$0")"
K1="The same woman with the same face, the same platinum blonde 1940s pin curls, red lipstick and smoky eyes, the same black satin halter top and long black opera gloves, holding the same long black cigarette holder. Medium close-up portrait from the waist up, she faces the camera and looks into the lens. Plain dark grey studio background, soft low-key light. Photoreal, sharp focus."
python gen.py klein vela_mcu_k1 101 "$K1" vela_fav1.png 768 1024
python gen.py klein vela_mcu_k2 102 "$K1" vela_fav1.png 768 1024
PS="A blonde 1940s woman stands in place, slowly raises the long cigarette holder to her red lips and takes a slow drag, lowers it, then breathes out a soft stream of smoke and gives the camera a slow knowing look. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir, smoke drifting."
python gen.py ltx vela_smoke_s21 21 "$PS" vela_fav1.png 97
PD="A raven-haired 1940s woman stands in place and looks at herself in a mirror toward the camera. She slowly touches her black hair with one gloved hand, shifts her weight onto one hip and breathes slowly, a thin curl of smoke rises from her cigarette holder. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx dolores_idle_s31 31 "$PD" vp_dolores_fav2.png 97
CW="Close-up of a raven-haired 1940s woman holding a cigarette. She gives a slow warm smile, blinks softly and tilts her head a little, a thin curl of smoke rises. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
CG="Close-up of a raven-haired 1940s woman holding a cigarette. She narrows her eyes a little, glances aside and back to the camera, and breathes slowly, a thin curl of smoke rises. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
CC="Close-up of a raven-haired 1940s woman holding a cigarette. She stares coldly at the camera, lifts her chin a little and blinks once slowly, a thin curl of smoke rises. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx dolores_warm_s41 41 "$CW" vp_dolores_close_warm.jpg 73 480 640
python gen.py ltx dolores_guarded_s42 42 "$CG" vp_dolores_close_guarded.jpg 73 480 640
python gen.py ltx dolores_cold_s43 43 "$CC" vp_dolores_close_cold.jpg 73 480 640
python gen.py ltx vela_smoke_s22 22 "$PS" vela_fav1.png 97
python gen.py ltx dolores_idle_s32 32 "$PD" vp_dolores_fav2.png 97
echo ALLDONE
