"""Audit all user-facing documents for stale numbers left by earlier revisions."""
from __future__ import annotations

import os
import re

from docx import Document

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "results", "AUDIT_document_consistency.md")

DOCS = [
    "README.md",
    "paper/manuscript.md",
    "paper/main.tex",
    "报告/实验执行报告_2026-11-17.docx",
    "报告/RQ3_D1D2补充实验_2026-11-17.docx",
    "报告/B2_All-In-One补充实验_2026-11-18.docx",
    "投稿/Cover_Letter_2026-11-17.docx",
    "实验记录/实验日志_2026-11-17.md",
    "项目计划/时间表与成本_2026-11-17.md",
]
# stale patterns from earlier revisions; each is a regex with a human label
PATTERNS = [
    (r"\b6 个案例\b", "old B2 case count (6)"),
    (r"\bsix injected\b", "old B2 case count (six)"),
    (r"\b75\.3\s*%?", "old B2 reduction (75.3%)"),
    (r"\b9\.17\b", "old B2 Y-MAE (9.17)"),
    (r"\b2\.23\s*[x×]", "old B2 ratio (2.23x)"),
    (r"four of six", "old boundary count"),
    (r"(?<![\d.])283(?![\d.])", "old package file count (283)"),
    (r"(?<![\d.])286(?![\d.])", "old package file count (286)"),
    (r"(?<![\d.])289(?![\d.])", "old package file count (289)"),
    (r"(?<![\d.])295(?![\d.])", "old package file count (295)"),
    (r"\b33\.2\s*MB", "old package size (33.2 MB)"),
    (r"\b33\.8\s*MB", "old package size (33.8 MB)"),
    (r"\b13\.39\b", "old B2 mean (13.39)"),
    (r"\b64\.1\s*%", "old B2 reduction (64.1%)"),
    (r"\b99\.96\s*%", "old B2 outFrac (99.96%)"),
    (r"\b14 个案例\b", "old B2 case count (14)"),
    (r"fourteen injected", "old B2 count (fourteen)"),
    (r"¥\s*0\.14", "old cost (0.14)"),
    (r"\b0\.88\s*(?:h|小时|GPU)", "old GPU hours (0.88)"),
]


def text_of(path):
    if path.endswith(".docx"):
        d = Document(path)
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.extend(c.text for c in row.cells)
        return "\n".join(parts)
    return open(path, encoding="utf-8").read()


def main():
    lines = ["# Document consistency audit", ""]
    hits = 0
    for rel in DOCS:
        p = os.path.join(WS, rel)
        if not os.path.exists(p):
            lines.append(f"- MISSING: {rel}"); continue
        txt = text_of(p)
        for pat, label in PATTERNS:
            for m in re.finditer(pat, txt):
                a = max(0, m.start() - 45); b = min(len(txt), m.end() + 45)
                ctx = txt[a:b].replace("\n", " ")
                lines.append(f"- `{rel}` | {label} | …{ctx}…")
                hits += 1
    lines.insert(1, f"Total hits: {hits}")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("hits", hits, "->", OUT)
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    main()
