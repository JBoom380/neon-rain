#!/bin/bash
# Vela talking (dialogue beats), FAV1 start frame, same framing as vela_clip1. Runs after the stole batch.
cd "$(dirname "$0")"
until grep -q -E "ALLDONE|ERROR|Traceback" batch_stole.log; do sleep 20; done
PT="A blonde 1940s woman stands in place and talks softly to the camera, her red lips move gently as she speaks, she tilts her head slightly and blinks, the cigarette holder stays still in her gloved hand. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir, smoke drifting."
python gen.py ltx vela_talk_s51 51 "$PT" vela_fav1.png 97
python gen.py ltx vela_talk_s52 52 "$PT" vela_fav1.png 97
echo ALLDONE
