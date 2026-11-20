"""Build the human-annotation package: 100 numbered clips, examples, index."""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "标注")
CLIPS = os.path.join(OUT, "clips")
EX = os.path.join(OUT, "examples")
sys.path.insert(0, os.path.join(WS, "third_party", "pylibs"))
sys.path.insert(0, os.path.join(WS, "project", "src"))

import imageio_ffmpeg  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
SEQS = ["sailboat", "book", "horse", "paint", "fish", "unicorn", "yoga",
        "knight", "rabbit", "astronaut", "ship", "asteroids", "retriever"]
LEN = 24
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)


def encode(frames, path, tmp):
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    for i, f in enumerate(frames):
        Image.fromarray(f).save(os.path.join(tmp, f"{i:03d}.png"))
    cmd = [FF, "-y", "-framerate", "8", "-i", os.path.join(tmp, "%03d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    shutil.rmtree(tmp)


def overlay(frames, label, start):
    out = []
    for i, f in enumerate(frames):
        im = Image.fromarray(f)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 34], fill=(0, 0, 0))
        d.text((8, 5), f"{label}  |  frame {i:02d}/23 (global {start + i:02d})", font=FONT, fill=(255, 255, 0))
        out.append(np.asarray(im))
    return out


def main():
    os.makedirs(CLIPS, exist_ok=True)
    os.makedirs(EX, exist_ok=True)
    rows = []
    base = [0, 10, 20, 30, 40, 50, 52]
    starts_by = {seq: base + ([5] if i < 9 else []) for i, seq in enumerate(SEQS)}
    n = 0
    for si, seq in enumerate(SEQS):
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        for st in starts_by[seq]:
            if n >= 100:
                break
            if st + LEN > len(ref):
                continue
            n += 1
            cid = f"clip_{n:03d}"
            frames = overlay(ref[st:st + LEN], f"{cid} | {seq}", st)
            encode(frames, os.path.join(CLIPS, cid + ".mp4"), os.path.join(OUT, "_tmp"))
            rows.append({"clip_id": cid, "sequence": seq, "clip_start": st, "clip_end": st + LEN - 1})
        if n >= 100:
            break
    with open(os.path.join(OUT, "clip_index.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["clip_id", "sequence", "clip_start", "clip_end"]); w.writeheader(); w.writerows(rows)

    # labelled examples
    ref = load_frames(os.path.join(WS, "data", "frames", "sailboat"))
    encode(overlay(ref[26:50], "EXAMPLE clean | sailboat", 26), os.path.join(EX, "示例1_干净_sailboat.mp4"), os.path.join(OUT, "_tmp"))
    encode(overlay(apply_injection(ref, InjectionSpec("A", "offset", 20.0, -1), 30, 12).injected[26:50],
                   "EXAMPLE offset -20 | sailboat", 26), os.path.join(EX, "示例2_偏移20_sailboat.mp4"), os.path.join(OUT, "_tmp"))
    ref2 = load_frames(os.path.join(WS, "data", "frames", "book"))
    encode(overlay(apply_injection(ref2, InjectionSpec("B", "gamma", gamma=2.0), 30, 12).injected[26:50],
                   "EXAMPLE gamma 2 | book", 26), os.path.join(EX, "示例3_gamma2_book.mp4"), os.path.join(OUT, "_tmp"))
    ref3 = load_frames(os.path.join(WS, "data", "frames", "horse"))
    encode(overlay(apply_injection(ref3, InjectionSpec("B13", "gamma", gamma=1.3), 30, 12).injected[26:50],
                   "EXAMPLE gamma 1.3 | horse", 26), os.path.join(EX, "示例4_gamma1.3_horse.mp4"), os.path.join(OUT, "_tmp"))
    encode(overlay(ref3[26:50], "EXAMPLE clean | horse", 26), os.path.join(EX, "示例5_干净_horse.mp4"), os.path.join(OUT, "_tmp"))
    print("clips", n, "examples", 5)


if __name__ == "__main__":
    main()
