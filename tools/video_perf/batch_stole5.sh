#!/bin/bash
# Stole take 3 (high priority, front of queue): Klein end frame, then first/last-frame LTX takes.
cd "$(dirname "$0")"
IN=/e/ComfyUI_windows_portable/ComfyUI/input; OUTD=/c/Users/John/Documents/ComfyUI_Output/vperf
KE="The same woman with the same face and the same platinum blonde pin curls, red lipstick. The black mink fur stole has slipped off her shoulders and now hangs low around her elbows and forearms, her bare shoulders and her black satin halter top and red satin skirt are fully visible, black opera gloves. Same pose, same framing, same plain dark grey background. Photoreal, sharp focus."
python gen.py klein vela_stole_end_k1 131 "$KE" vp_vela_stole_in.png 768 960 --front
cp $OUTD/vela_stole_end_k1_00001_.png $IN/vp_vela_stole_end1.png && echo KLEIN1
PS="A blonde 1940s woman in a black fur stole stands in place. She slowly lets the black fur stole slip off her shoulders down to her elbows, showing her bare shoulders and black satin halter top, and gives the camera a slow knowing look. Her face stays exactly the same. Slow, smooth motion. The camera does not move. Film noir."
python gen.py ltx vela_stole_fl_s91 91 "$PS" vp_vela_stole_in.png 97 512 640 vp_vela_stole_end1.png --front
python gen.py ltx vela_stole_fl_s92 92 "$PS" vp_vela_stole_in.png 97 512 640 vp_vela_stole_end1.png --front
echo ALLDONE
