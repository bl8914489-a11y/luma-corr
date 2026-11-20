"""Assemble the final annotation delivery package with a 5-clip qualification test."""
from __future__ import annotations

import os
import shutil
import sys
import zipfile

import numpy as np

WS = r"F:\周四焜哥论文"
SRC = os.path.join(WS, "标注")
OUT = os.path.join(SRC, "标注资料包_2026-11-18")
ZIP = os.path.join(SRC, "标注资料包_2026-11-18.zip")
sys.path.insert(0, os.path.join(WS, "project", "src"))
sys.path.insert(0, os.path.join(WS, "project", "tools"))

from build_annotation_clips import encode, overlay  # noqa: E402
from luma_corr.imaging import load_frames  # noqa: E402
from luma_corr.injection import InjectionSpec, apply_injection  # noqa: E402

READ = """# 开始前必读（5 分钟）

## 这个包是什么

- 100 个 24 帧（约 3 秒）的生成视频片段，来自 13 段 VideoDM/Meta 子集；
- 每个片段顶部烧录了 clip 编号和 frame 00–23，不需要你数帧；
- 你要判断：**整体亮度/曝光/对比度是否出现异常**，并标出起止帧。

## 先做资格测试（约 10 分钟）

1. 打开 `03_资格测试/qual_01.mp4 … qual_05.mp4`，按正式流程标 5 个片段；
2. 标完后打开 `03_资格测试/答案.md` 对照；
3. **5/5 通过**；4/5 请重读指南再标一次；<4/5 先别开始正式 100 个，告诉我，我补讲。

资格测试不计入正式数据，只是为了让你熟悉工具和口径。

## 正式标注（2.5–3.5 小时）

1. 打开 `02_标注模板_2026-11-18.xlsx`，用 `Annotator_A` 或 `Annotator_B` 表；
2. 打开 `04_正式片段/clip_001.mp4` 开始，按编号顺序做；
3. 每个片段：正常播放一遍 → 逐帧（VLC: E/D；mpv: ./,）→ 填一行；
4. 每 20 个休息一下，避免疲劳导致漏标；
5. 做完另存为 `标注模板_你的名字.xlsx`。

## 填表规则（只记这 5 条）

- 无缺陷：`has_defect=0`，`type=none`，start/end 留空；
- 有缺陷：`has_defect=1`，`defect_start/defect_end` 填 0–23（含首尾）；
- 多段：只标最主要一段，其余写 `notes`；
- 截断：start 填 0 或 end 填 23，`notes` 写“截断”；
- 拿不准：`confidence=1` + `notes`，**不要猜**。

## 关于“标错”

- 标注不是考试，没有“责任”问题；错误由**双人一致性**和**仲裁**发现，不靠你一个人保证 100%；
- 100 个里抽 20% 双标；kappa/IoU 低于阈值会仲裁争议项；
- 所以：**不确定就标低置信度并写 notes**，这比硬判更有价值。

## 交付

- Excel 另存为 `标注模板_你的名字.xlsx`；
- 不要改前四列：`clip_id / sequence / clip_start / clip_end`；
- 发回即可。

## 数据边界

13 段来自 VideoDM/Meta 子集，能确认是生成视频子集，但公开数据没有逐段模型名/提示词；论文会如实写这一限制。片段有重叠，统计按 13 段聚类。
"""

ANSWERS = """# 资格测试答案（先自己标完再看）

| 片段 | has_defect | 区间（0–23） | type | severity | 说明 |
|---|---|---|---|---|---|
| qual_01 | 0 | — | none | — | 干净 sailboat |
| qual_02 | 1 | 4–15 | exposure | 4 | 整体变暗 20 |
| qual_03 | 1 | 4–15 | gamma | 4 | gamma 2.0，中间调/对比变化 |
| qual_04 | 1 | 4–15 | gamma | 2 | gamma 1.3，轻微 |
| qual_05 | 0 | — | none | — | 干净 horse |

判定：5/5 的 has_defect 全对，且 3 个正例区间 IoU≥0.5，即通过。
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "03_资格测试"))
    os.makedirs(os.path.join(OUT, "04_正式片段"))
    os.makedirs(os.path.join(OUT, "05_示例"))
    open(os.path.join(OUT, "00_开始前必读.md"), "w", encoding="utf-8").write(READ)
    shutil.copy2(os.path.join(SRC, "标注指南_2026-11-18.docx"), os.path.join(OUT, "01_标注指南.docx"))
    shutil.copy2(os.path.join(SRC, "标注指南_2026-11-18.pdf"), os.path.join(OUT, "01_标注指南.pdf"))
    shutil.copy2(os.path.join(SRC, "标注模板_2026-11-18.xlsx"), os.path.join(OUT, "02_标注模板_2026-11-18.xlsx"))
    shutil.copy2(os.path.join(SRC, "clip_index.csv"), os.path.join(OUT, "clip_index.csv"))
    shutil.copy2(os.path.join(SRC, "标注速查卡.md"), os.path.join(OUT, "速查卡.md"))
    for f in os.listdir(os.path.join(SRC, "clips")):
        shutil.copy2(os.path.join(SRC, "clips", f), os.path.join(OUT, "04_正式片段", f))
    for f in os.listdir(os.path.join(SRC, "examples")):
        shutil.copy2(os.path.join(SRC, "examples", f), os.path.join(OUT, "05_示例", f))

    # neutral qualification clips (no labels in the overlay)
    ref = load_frames(os.path.join(WS, "data", "frames", "sailboat"))
    book = load_frames(os.path.join(WS, "data", "frames", "book"))
    horse = load_frames(os.path.join(WS, "data", "frames", "horse"))
    q = [
        ("qual_01", ref[26:50]),
        ("qual_02", apply_injection(ref, InjectionSpec("A", "offset", 20.0, -1), 30, 12).injected[26:50]),
        ("qual_03", apply_injection(book, InjectionSpec("B", "gamma", gamma=2.0), 30, 12).injected[26:50]),
        ("qual_04", apply_injection(horse, InjectionSpec("B13", "gamma", gamma=1.3), 30, 12).injected[26:50]),
        ("qual_05", horse[26:50]),
    ]
    for name, frames in q:
        encode(overlay(frames, f"{name.upper()}", 26), os.path.join(OUT, "03_资格测试", name + ".mp4"),
               os.path.join(OUT, "_tmp"))
    open(os.path.join(OUT, "03_资格测试", "答案.md"), "w", encoding="utf-8").write(ANSWERS)

    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("package", OUT, "files", n, "zip", round(os.path.getsize(ZIP) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
