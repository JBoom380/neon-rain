#!/bin/bash
# High priority: Vela slides the mink stole to her elbows (cover pose start frame on a grey plate).
cd "$(dirname "$0")"
PS="A blonde 1940s woman in a black mink fur stole stands in place. She slowly slides the fur stole off her shoulders and lets it fall to her elbows, showing her black satin halter top and red satin skirt, then gives the camera a slow knowing look. Her face stays exactly the same. Very subtle, slow motion. The camera does not move. Film noir."
python gen.py ltx vela_stole_s71 71 "$PS" vp_vela_stole_in.png 97 512 640
python gen.py ltx vela_stole_s72 72 "$PS" vp_vela_stole_in.png 97 512 640
python gen.py ltx vela_stole_s73 73 "$PS" vp_vela_stole_in.png 97 512 640
echo ALLDONE
