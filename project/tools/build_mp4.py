"""Encode the tiled PNG frames into 8 fps MP4 demos via imageio-ffmpeg."""
from __future__ import annotations

import os
import subprocess
import sys

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
BASE = os.path.join(WS, "可视化")
sys.path.insert(0, os.path.join(WS, "third_party", "pylibs"))

import imageio_ffmpeg  # noqa: E402

CASES = ["sailboat_A_len12", "sailboat_B_len12", "horse_A_len12", "book_B_len12"]


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    for c in CASES:
        src = os.path.join(BASE, "frames", c, "%03d.png")
        out = os.path.join(BASE, c + ".mp4")
        cmd = [ff, "-y", "-framerate", "8", "-i", src, "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-crf", "20", out]
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(c, r.returncode, os.path.getsize(out) if os.path.exists(out) else "MISSING")


if __name__ == "__main__":
    main()
