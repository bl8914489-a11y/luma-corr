"""Assemble a GitHub-ready repository (code + manuscript + frozen tables)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

WS = Path(r"F:\周四焜哥论文")
REPO = WS / "repository"
if REPO.exists():
    shutil.rmtree(REPO)
REPO.mkdir()

for rel in ["project/src", "project/scripts", "project/configs", "project/tests", "project/tools"]:
    src = WS / rel
    dst = REPO / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

(REPO / "paper/figures").mkdir(parents=True, exist_ok=True)
for f in ["manuscript_v2.md", "manuscript_v2.docx", "manuscript_v2.pdf",
          "Supplementary_v2.docx", "Supplementary_v2.pdf", "references.bib"]:
    src = WS / "paper" / f
    if src.exists():
        shutil.copy2(src, REPO / "paper" / f)
for f in ["fig3_writeback_scope.png", "fig2_b2_example.png"]:
    src = WS / "paper/figures" / f
    if src.exists():
        shutil.copy2(src, REPO / "paper/figures" / f)

(REPO / "results/tables").mkdir(parents=True, exist_ok=True)
for f in ["full13_matrix.csv"]:
    src = WS / "results/tables" / f
    if src.exists():
        shutil.copy2(src, REPO / "results/tables" / f)
for f in WS.glob("results/FREEZE_*.json"):
    shutil.copy2(f, REPO / "results" / f.name)
for f in ["FULL13_MATRIX_2026-11-21.md", "B2_TIMING_2026-11-21.md"]:
    src = WS / "results" / f
    if src.exists():
        shutil.copy2(src, REPO / "results" / f)
(REPO / "data/manifest").mkdir(parents=True, exist_ok=True)
src = WS / "data/manifest"
if src.exists():
    for f in src.glob("*.json"):
        shutil.copy2(f, REPO / "data/manifest" / f.name)

(REPO / "投稿").mkdir(exist_ok=True)
for f in ["Cover_Letter_v2_2026-11-21.docx", "Cover_Letter_v2_2026-11-21.pdf"]:
    src = WS / "投稿" / f
    if src.exists():
        shutil.copy2(src, REPO / "投稿" / f)

(REPO / "LICENSE").write_text("""MIT License

Copyright (c) 2026 [Author Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Data: the Blind-Video-Deflickering-Dataset is used under CC BY 4.0; see
data/manifest and the dataset repository.
""", encoding="utf-8")

(REPO / "README.md").write_text("""# Local brightness correction under known intervals

Code, frozen tables and manuscript for the paper:

> Local Brightness Correction under Known Intervals: A Controlled Benchmark,
> Sensitivity Analysis, and Reproducibility Study.

## What is here

- `project/src` — correction, injection, detection, metrics, statistics.
- `project/scripts` — matrix, detection, B2, multi-interval, evaluation.
- `project/configs` — fixed configurations.
- `project/tests` — 37 unit tests.
- `results/tables/full13_matrix.csv` — full 13-sequence matrix with bootstrap CIs.
- `results/FREEZE_*.json` — frozen numbers and hashes.
- `paper/` — narrowed manuscript v2, Supplementary, figures, references.
- `投稿/` — cover letter.

## Quick start

```bash
python -m unittest discover -s project/tests -v
LUMA_WS=$PWD python project/tools/verify_numbers.py
```

The full one-click package (all run artifacts, reports, hashes) is distributed
separately; see the paper's Data availability statement. Raw frames and
All-In-One weights are not included (size/licence); download them from the
official sources listed in `data/manifest/`.

## Data

Blind-Video-Deflickering-Dataset (VideoDM/Meta subset), CC BY 4.0.
Archive SHA-256: 737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e.

## License

Code: MIT. Manuscript: CC BY 4.0. Dataset: CC BY 4.0.

## Repository URL

Replace the placeholder in the manuscript and README with the final GitHub URL:
`https://github.com/[your-account]/luma-corr`.
""", encoding="utf-8")

(REPO / "CITATION.cff").write_text("""cff-version: 1.2.0
message: "If you use this code, please cite the paper."
title: "Local Brightness Correction under Known Intervals: A Controlled Benchmark, Sensitivity Analysis, and Reproducibility Study"
authors:
  - family-names: "[Author]"
    given-names: "[Name]"
year: 2026
repository-code: "https://github.com/[your-account]/luma-corr"
license: MIT
""", encoding="utf-8")

(REPO / ".gitignore").write_text("""__pycache__/
*.pyc
data/frames/
third_party/
交付/
*.zip
""", encoding="utf-8")
print("repo built", REPO)
