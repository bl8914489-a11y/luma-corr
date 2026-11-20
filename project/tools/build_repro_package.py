"""Assemble the reproducible delivery package (code + artifacts + checksums)."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
OUT = os.path.join(WS, "交付", "复现包_2026-11-17")
ZIP = os.path.join(WS, "交付", "复现包_2026-11-17.zip")

COPY = [
    ("project", None),
    ("results/runs", None),
    ("results/tables", None),
    ("results/environment", None),
    ("results/tests", None),
    ("results/FREEZE_2026-11-17.json", None),
    ("results/FREEZE_B2_FULL_2026-11-18.json", None),
    ("results/FREEZE_RQ3_SCAN_2026-11-18.json", None),
    ("results/FREEZE_MULTI_INTERVAL_2026-11-18.json", None),
    ("results/FREEZE_MULTI_MIXED_2026-11-18.json", None),
    ("results/FREEZE_EDGE_2026-11-18.json", None),
    ("results/FREEZE_MULTI_SCAN_2026-11-18.json", None),
    ("results/FREEZE_EDGE_AWARE_2026-11-18.json", None),
    ("results/FREEZE_MULTI_SCAN_THREE_2026-11-18.json", None),
    ("results/FREEZE_B2_MULTI_2026-11-19.json", None),
    ("results/FREEZE_B2_THREE_2026-11-19.json", None),
    ("results/FREEZE_MULTI_FOUR_2026-11-19.json", None),
    ("results/FREEZE_B2_FOUR_2026-11-19.json", None),
    ("results/FREEZE_MULTI_SCAN_FOUR_2026-11-19.json", None),
    ("results/FREEZE_NATURAL_PRE_2026-11-19.json", None),
    ("results/FREEZE_NATURAL_SINGLE_2026-11-20.json", None),
    ("results/FREEZE_E2E_2026-11-21.json", None),
    ("results/FREEZE_FULL13_2026-11-21.json", None),
    ("results/FULL13_MATRIX_2026-11-21.md", None),
    ("results/B2_TIMING_2026-11-21.md", None),
    ("results/b2_logs", None),
    ("标注/回收/标注_最终_确认_2026-11-20.csv", None),
    ("results/B2_FULL_2026-11-18.md", None),
    ("results/B2_FULL_READY.json", None),
    ("results/UNCERTAINTY_2026-11-18.json", None),
    ("results/UNCERTAINTY_2026-11-18.md", None),
    ("results/AUDIT_document_consistency.md", None),
    ("results/manuscript_table_audit.md", None),
    ("results/reference_audit.md", None),
    ("报告", None),
    ("实验记录", None),
    ("项目计划", None),
    ("data/manifest", None),
    ("data/literature", None),
    ("paper", None),
    ("投稿", None),
]
VIZ = ["index.html", "打开可视化.cmd", "cases.json", "如何查看.md", "可视化查看说明.docx",
       "sailboat_A_len12.gif", "sailboat_B_len12.gif", "horse_A_len12.gif", "book_B_len12.gif",
       "sailboat_A_len12.mp4", "sailboat_B_len12.mp4", "horse_A_len12.mp4", "book_B_len12.mp4"]


def ignore(dir, names):
    drop = {"__pycache__", ".pytest_cache"}
    return [n for n in names if n in drop or n.endswith((".pyc", ".tmp"))]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    if os.path.isdir(OUT):
        for root, _, files in os.walk(OUT):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), 0o666)
                except OSError:
                    pass
        shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(OUT, "可视化"))
    for rel, _ in COPY:
        src = os.path.join(WS, rel)
        dst = os.path.join(OUT, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=ignore)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    for name in VIZ:
        src = os.path.join(WS, "可视化", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT, "可视化", name))

    # environment
    env_dir = os.path.join(OUT, "环境")
    os.makedirs(env_dir, exist_ok=True)
    shutil.copy2(os.path.join(WS, "results", "environment", "python_stack.txt"), env_dir)
    shutil.copy2(os.path.join(WS, "results", "environment", "gpu_nvidia_smi.txt"), env_dir)
    shutil.copy2(os.path.join(WS, "results", "environment", "ffmpeg.txt"), env_dir)
    with open(os.path.join(env_dir, "requirements.txt"), "w", encoding="utf-8") as fh:
        fh.write("# CPU matrix / RQ3\nnumpy==2.3.5\npillow==12.3.0\npandas==3.0.1\n"
                 "# B2 All-In-One (GPU)\n# torch==2.11.0+cu128\ntorchvision==0.26.0+cu128\n"
                 "# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128\n"
                 "opencv-python-headless\nimageio\nimageio-ffmpeg\nmatplotlib\ntqdm\neasydict\n"
                 "tensorboard\nscikit-image\n")

    # third_party note
    tp = os.path.join(OUT, "third_party")
    os.makedirs(tp, exist_ok=True)
    with open(os.path.join(tp, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# Third-party code and weights (not bundled)\n\n"
                 "B2 All-In-One is not redistributed here. Fetch it from the official sources:\n\n"
                 "- code: https://github.com/ChenyangLEI/All-In-One-Deflicker\n"
                 "- weights: https://github.com/ChenyangLEI/cvpr2023_deflicker_public_folder\n\n"
                 "Weights SHA-256 (recorded 2026-11-17):\n\n"
                 "- neural_filter.pth: " + sha(os.path.join(WS, "third_party", "All-In-One-Deflicker",
                                                             "pretrained_weights", "neural_filter.pth")) + "\n"
                 "- local_refinement_net.pth: " + sha(os.path.join(WS, "third_party", "All-In-One-Deflicker",
                                                                    "pretrained_weights", "local_refinement_net.pth")) + "\n"
                 "- raft-things.pth: " + sha(os.path.join(WS, "third_party", "All-In-One-Deflicker",
                                                           "pretrained_weights", "raft-things.pth")) + "\n\n"
                 "The reproduction package does not include these weights; B2 numbers in the report\n"
                 "were produced with them on an RTX 5060 Laptop 8GB.\n")

    # scripts
    with open(os.path.join(OUT, "一键测试.ps1"), "w", encoding="utf-8") as fh:
        fh.write("$ErrorActionPreference='Stop'\n"
                 "$py = $env:LUMA_PY\n"
                 "if (-not $py) { $py = 'C:\\Users\\zk770\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe' }\n"
                 "if (-not (Test-Path $py)) { $py = (Get-Command python).Source }\n"
                 "$env:LUMA_WS = $PSScriptRoot\nSet-Location $PSScriptRoot\n"
                 "& $py -m unittest discover -s project\\tests -v\n"
                 "$env:FREEZE_OUT = Join-Path $env:TEMP 'luma_freeze_check.json'\n"
                 "& $py project\\tools\\verify_numbers.py\n")
    with open(os.path.join(OUT, "一键重算表格.ps1"), "w", encoding="utf-8") as fh:
        fh.write("$ErrorActionPreference='Stop'\n"
                 "$py = $env:LUMA_PY\n"
                 "if (-not $py) { $py = 'C:\\Users\\zk770\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe' }\n"
                 "if (-not (Test-Path $py)) { $py = (Get-Command python).Source }\n"
                 "$env:LUMA_WS = $PSScriptRoot\nSet-Location $PSScriptRoot\n"
                 "& $py project\\scripts\\run_stats.py --run-dir results\\runs\\tierA_matrix_v1 --out results\\tables\\tierA_matrix_v1\n"
                 "& $py project\\scripts\\make_tables.py\n"
                 "& $py project\\scripts\\build_report.py\n"
                 "& $py project\\scripts\\build_workbook.py\n"
                 "& $py project\\tools\\build_rq3_supplement.py\n"
                 "& $py project\\tools\\build_b2_report.py\n"
                 "& $py project\\tools\\build_paper_tables.py\n")
    with open(os.path.join(OUT, "一键可视化.ps1"), "w", encoding="utf-8") as fh:
        fh.write("$ErrorActionPreference='Stop'\n"
                 "$py = $env:LUMA_PY\n"
                 "if (-not $py) { $py = 'C:\\Users\\zk770\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe' }\n"
                 "if (-not (Test-Path $py)) { $py = (Get-Command python).Source }\n"
                 "$env:LUMA_WS = $PSScriptRoot\nSet-Location $PSScriptRoot\n"
                 "# requires data/frames (not bundled; see README_复现包.md)\n"
                 "& $py project\\tools\\build_visualizations.py\n"
                 "& $py project\\tools\\build_html_viewer.py\n"
                 "& $py project\\tools\\build_mp4.py\n"
                 "& $py project\\tools\\build_viz_guide.py\n")

    with open(os.path.join(OUT, "README_复现包.md"), "w", encoding="utf-8") as fh:
        fh.write("""# 复现包（2026-11-17）

本包包含：代码、固定配置、15 个 run 的产物（CSV/JSON/日志）、报告、可视化、文献库与成本台账。
**不包含** 2.4GB VideoDM/Meta 原始帧与 All-In-One 权重，两者按下方官方地址获取。

## 快速验证

```powershell
powershell -ExecutionPolicy Bypass -File .\\一键测试.ps1
```

应看到：37 项单元测试 OK，`results/FREEZE_2026-11-17.json` 中 37 项冻结检查全部 PASS。

## 数据

- 归档：https://huggingface.co/datasets/xrenaa/Blind-Video-Deflickering-Dataset
- `All-In-One-Deflicker-Dataset.zip`，2,485,464,921 B
- SHA-256：737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e
- 逐帧 SHA-256 见 `data/manifest/dataset_manifest.json`。

## 重算表格

```powershell
powershell -ExecutionPolicy Bypass -File .\\一键重算表格.ps1
```

只读现有 run 产物，不重跑矩阵；会重写 `报告/` 与 `results/tables/final/`。

## B2 All-In-One（可选，需 GPU）

按 `third_party/README.md` 获取官方代码与权重，安装 torch cu128 后：

```powershell
python project\\scripts\\run_all_in_one_batch.py
python project\\scripts\\eval_all_in_one.py
```

本机实测：RTX 5060 Laptop 8GB，stage1 约 8.7 分钟/案例，stage2 约 11 秒。

## 目录

- `project/`：核心库、配置、脚本、测试、工具
- `results/runs/`：每个 run 的 run_manifest / per_* / summary / validation
- `results/tables/`：汇总表与统计
- `报告/`：执行报告、RQ3 补充、B2 补充、结果工作簿、文献 BibTeX
- `可视化/`：MP4/GIF/网页播放器（逐帧 PNG 未打包，可用脚本重生成）
- `实验记录/`：实验日志与 runs_index
- `项目计划/`：15 天时间表与成本台账
- `环境/`：Python/GPU/FFmpeg 探测与 requirements
- `paper/tables/`：LaTeX 表

## 诚实边界

- RQ3 预注册测试集 len12 召回 0.744，未达 0.90；论文按边界性发现写。
- B2 是盲全局方法，outFrac≈100% 是任务设定差异，不是 SOTA 排名。
- 数据 13/13 段（VideoDM/Meta 全子集），未达 15；真实 T2V 人工标注未完成。
""")

    # checksums
    lines = []
    for dirpath, dirnames, filenames in os.walk(OUT):
        dirnames[:] = sorted(d for d in dirnames if d not in {"__pycache__"})
        for f in sorted(filenames):
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, OUT).replace("\\", "/")
            lines.append(f"{sha(p)}  {rel}")
    with open(os.path.join(OUT, "SHA256SUMS.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    if os.path.exists(ZIP):
        os.remove(ZIP)
    import zipfile
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dirpath, dirnames, filenames in os.walk(OUT):
            for f in filenames:
                p = os.path.join(dirpath, f)
                z.write(p, os.path.relpath(p, os.path.dirname(OUT)))
    print("package", OUT, "files", len(lines), "zip", round(os.path.getsize(ZIP) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
