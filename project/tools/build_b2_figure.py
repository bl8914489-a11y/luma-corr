"""Create a 2x2 high-resolution B2 qualitative figure with PIL."""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"F:\周四焜哥论文\project\src")
from luma_corr.corrections import correct
from luma_corr.imaging import load_frames
from luma_corr.injection import InjectionSpec, apply_injection

WS = r"F:\周四焜哥论文"
ref = load_frames(os.path.join(WS, "data", "frames", "sailboat"))
inj = apply_injection(ref, InjectionSpec("B", "gamma", gamma=2.0), 30, 12).injected
a3 = correct({"id": "A3", "kind": "offset_linear", "k": 3, "scope": "local"}, inj, 30, 12).out
d = os.path.join(WS, "third_party", "All-In-One-Deflicker", "results", "sailboat_B_len12", "final", "output")
files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
b2 = np.stack([np.asarray(Image.open(os.path.join(d, f)).convert("RGB")) for f in files])
t = 34
panels = [("Reference", ref[t]), ("Injected (B, gamma=2)", inj[t]),
          ("A3 local", a3[t]), ("B2 All-In-One", b2[t])]
S = 512
LAB = 44
canvas = Image.new("RGB", (S * 2, (S + LAB) * 2), "white")
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("arial.ttf", 26)
except Exception:
    font = ImageFont.load_default()
for i, (title, img) in enumerate(panels):
    r, c = divmod(i, 2)
    x, y = c * S, r * (S + LAB)
    draw.text((x + 10, y + 8), title, fill="black", font=font)
    canvas.paste(Image.fromarray(img), (x, y + LAB))
out = os.path.join(WS, "paper", "figures", "fig2_b2_example.png")
canvas = canvas.resize((canvas.width * 2, canvas.height * 2), Image.LANCZOS)
canvas.save(out, dpi=(300, 300))
print(out, canvas.size)
