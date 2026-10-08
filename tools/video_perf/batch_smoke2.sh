#!/bin/bash
# Smoke take 2: name the glove and the holder so they hold their shape (take s21 turned the glove into a bare hand).
cd "$(dirname "$0")"
until grep -q -E "ALLDONE|ERROR|Traceback" batch_talk.log; do sleep 30; done
PS2="A blonde 1940s woman stands in place. Her hand in a long black satin opera glove slowly lifts the long thin black cigarette holder to her red lips, she draws on it, lowers it, and breathes out a soft curl of smoke with a slow knowing look at the camera. The black glove and the long black holder stay the same. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir, smoke drifting."
python gen.py ltx vela_smoke_s23 23 "$PS2" vela_fav1.png 97
python gen.py ltx vela_smoke_s24 24 "$PS2" vela_fav1.png 97
echo ALLDONE
