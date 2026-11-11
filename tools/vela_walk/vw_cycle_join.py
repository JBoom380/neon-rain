"""Join the four LTX stride segments (key to key, shared end frames) into one seamless gait-cycle mp4.
Usage: vw_cycle_join.py OUT.mp4 SEG00.mp4 SEG04.mp4 SEG08.mp4 SEG12.mp4  (each segment's last frame = next segment's first)"""
import sys, subprocess, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'video_perf'))
import process as VP
out, segs = sys.argv[1], sys.argv[2:]
F = [VP.read_frames(s) for s in segs]
seq = np.concatenate([f[:-1] for f in F], 0)
h, w = seq.shape[1:3]
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', '24', '-i', '-', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv444p', out], stdin=subprocess.PIPE)
p.stdin.write(seq.tobytes()); p.stdin.close(); p.wait()
print(out, len(seq), 'frames', [len(f) for f in F])
