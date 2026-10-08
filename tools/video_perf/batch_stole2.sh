#!/bin/bash
# Stole take 2: shorter, concrete action words (take 1 drifted the face and did not move the fur).
cd "$(dirname "$0")"
until grep -q -E "ALLDONE|ERROR|Traceback" batch_stole.log; do sleep 20; done
PS2="A blonde 1940s woman in a black fur stole. She slowly lowers her shoulders and the black fur stole slips down her arms to her elbows, showing her bare shoulders and black satin halter top. She looks at the camera. Her face stays exactly the same. Slow, smooth motion. The camera does not move. Film noir."
python gen.py ltx vela_stole_s74 74 "$PS2" vp_vela_stole_in.png 97 512 640
python gen.py ltx vela_stole_s75 75 "$PS2" vp_vela_stole_in.png 97 512 640
PF="A blonde 1940s woman stands in place, breathing slowly, she shifts her weight onto one hip and blinks, the cigarette holder stays in her gloved hand. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx vela_full_s81 81 "$PF" vp_vela_full.png 97
echo ALLDONE
