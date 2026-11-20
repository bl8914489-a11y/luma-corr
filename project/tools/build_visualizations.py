"""Build visual comparisons (frame tiles + GIF + HTML viewer) for key cases.

No video encoder is available on this machine, so the deliverable is:
  * per-frame tiled PNGs (reference | injected | A3 | A4 | A7),
  * an animated GIF at a *nominal* 8 fps (not the dataset FPS),
  * a self-contained HTML viewer that steps/plays the PNG frames.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from luma_corr.corrections import correct  # noqa: E402
from luma_corr.imaging import frame_luma_means, load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402
from luma_corr.metrics import frame_metrics  # noqa: E402

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.path.join(WS, "可视化")
FRAMES = os.path.join(OUT, "frames")
FPS = 8
START = 30

CASES = [
    {"id": "sailboat_A_len12", "seq": "sailboat", "inj": "A", "len": 12,
     "note": "静态场景，常数偏移 −20。A3 恢复区间内亮度；A4 全序列写回会改到区间外。"},
    {"id": "sailboat_B_len12", "seq": "sailboat", "inj": "B", "len": 12,
     "note": "gamma=2，校正阶段上界削波；A3 有残差，A7 自适应 gamma 更好。"},
    {"id": "horse_A_len12", "seq": "horse", "inj": "A", "len": 12,
     "note": "运动场景，常数偏移；看 A3 与 A4 的边界差异。"},
    {"id": "book_B_len12", "seq": "book", "inj": "B", "len": 12,
     "note": "gamma=2，削波比例最高的样本（5.38%）；A3 残差最明显。"},
]

METHODS = {
    "A3": {"id": "A3", "kind": "offset_linear", "k": 3, "scope": "local"},
    "A4": {"id": "A4", "kind": "offset_median", "window": 7, "scope": "global"},
    "A7": {"id": "A7", "kind": "gamma_adaptive", "k": 3, "scope": "local"},
}
PANELS = ["Reference", "Injected", "A3 local k=3", "A4 full-seq", "A7 adaptive gamma"]
TILE = 280
HEAD = 30
FOOT = 26
GAP = 6


def font(size=15, bold=False):
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
                 r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def tile_frame(images, ymaes, t, start, length, note):
    n = len(images)
    w = n * TILE + (n - 1) * GAP
    h = HEAD + TILE + FOOT
    canvas = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(canvas)
    f = font(14)
    fb = font(15, True)
    in_int = start <= t < start + length
    # header
    d.rectangle([0, 0, w, HEAD - 2], fill=(180, 30, 30) if in_int else (40, 40, 40))
    d.text((8, 6), f"frame {t:02d}   " + ("IN DEFECT INTERVAL" if in_int else "outside interval")
           + f"   interval=[{start},{start+length})", font=fb, fill=(255, 255, 255))
    for i, (name, im, mae) in enumerate(zip(PANELS, images, ymaes)):
        x = i * (TILE + GAP)
        canvas.paste(im, (x, HEAD))
        d.rectangle([x, HEAD, x + TILE - 1, HEAD + TILE - 1], outline=(120, 120, 120))
        d.text((x + 4, HEAD + 4), name, font=f, fill=(255, 255, 0))
        d.text((x + 4, HEAD + TILE - 20), f"Y MAE {mae:5.2f}", font=f, fill=(255, 255, 0))
    d.text((8, HEAD + TILE + 4), note[:160], font=font(12), fill=(60, 60, 60))
    return canvas


def main():
    os.makedirs(FRAMES, exist_ok=True)
    cases_meta = []
    for case in CASES:
        seq, inj_id, length = case["seq"], case["inj"], case["len"]
        ref = load_frames(os.path.join(WS, "data", "frames", seq))
        spec = {"A": InjectionSpec("A", "offset", 20.0, -1),
                "B": InjectionSpec("B", "gamma", gamma=2.0),
                "B13": InjectionSpec("B13", "gamma", gamma=1.3)}[inj_id]
        inj = apply_injection(ref, spec, START, length).injected
        outs = {k: correct(m, inj, START, length).out for k, m in METHODS.items()}
        case_dir = os.path.join(FRAMES, case["id"])
        os.makedirs(case_dir, exist_ok=True)
        metrics = []
        for t in range(ref.shape[0]):
            panels = [ref[t], inj[t]] + [outs[k][t] for k in ("A3", "A4", "A7")]
            ymaes = [0.0] + [frame_metrics(panels[i], ref[t])["y_mae"] for i in range(1, 5)]
            ims = [Image.fromarray(p).resize((TILE, TILE), Image.BILINEAR) for p in panels]
            tiled = tile_frame(ims, ymaes, t, START, length, case["note"])
            tiled.save(os.path.join(case_dir, f"{t:03d}.png"))
            metrics.append({"t": t, "in_interval": int(START <= t < START + length),
                            "ymaes": [round(v, 3) for v in ymaes],
                            "luma_ref": float(frame_luma_means(ref[t:t + 1])[0]),
                            "luma_injected": float(frame_luma_means(inj[t:t + 1])[0])})
        # full 8 fps GIF: use every frame (duration 125 ms)
        gif = []
        for t in range(ref.shape[0]):
            im = Image.open(os.path.join(case_dir, f"{t:03d}.png")).convert("RGB")
            gif.append(im.resize((im.width // 2, im.height // 2), Image.BILINEAR))
        gif[0].save(os.path.join(OUT, f"{case['id']}.gif"), save_all=True, append_images=gif[1:],
                    duration=int(1000 / FPS), loop=0, optimize=True)
        agg = {name: float(np.mean([m["ymaes"][i] for m in metrics if m["in_interval"]]))
               for i, name in enumerate(["Reference", "Injected", "A3", "A4", "A7"])}
        meta = {**case, "start": START, "frames": int(ref.shape[0]),
                "interval_mean_y_mae": agg,
                "panel_order": PANELS, "nominal_fps": FPS,
                "note": case["note"] + "  GIF 的 8 fps 是演示帧率，数据集未提供真实 FPS。"}
        cases_meta.append(meta)
        with open(os.path.join(case_dir, "metrics.json"), "w", encoding="utf-8") as fh:
            json.dump({"case": meta, "frames": metrics}, fh, ensure_ascii=False)
        print("built", case["id"], flush=True)

    with open(os.path.join(OUT, "cases.json"), "w", encoding="utf-8") as fh:
        json.dump(cases_meta, fh, ensure_ascii=False, indent=1)
    print("cases", len(cases_meta))


if __name__ == "__main__":
    main()
