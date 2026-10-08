#!/bin/bash
# vela_full_v2: full-length front start frame, FAV1 face as identity reference (Klein, two references), then LTX takes.
cd "$(dirname "$0")"
K="Keep the first image exactly: the same full-length pose, the same black satin halter top, red satin pencil skirt, black opera gloves, cigarette holder, high heels, framing and plain grey background. Replace only her face with the exact face of the woman in the second image: the same face shape, eyes, eyebrows, nose, full red lips and soft rounded jaw, the same platinum blonde pin curls. She looks straight at the camera. Photoreal, sharp focus."
for s in 141 142 143; do python gen.py klein vela_full_v2_k$s $s "$K" vp_vela_full.png 768 1344 vp_fav1.png --front; done
echo KLEINDONE
