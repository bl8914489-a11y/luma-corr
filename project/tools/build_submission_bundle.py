"""Assemble the journal submission bundle (manuscript, cover letter, figures, tables, supplement)."""
from __future__ import annotations

import os
import shutil
import zipfile

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "投稿", "投稿包_2026-11-18")
ZIP = os.path.join(WS, "投稿", "投稿包_2026-11-18.zip")

FILES = {
    "01_Manuscript": [
        ("paper/manuscript_draft_2026-11-17.docx", "Manuscript.docx"),
        ("paper/manuscript_draft_2026-11-17.pdf", "Manuscript.pdf"),
    ],
    "02_Cover_Letter": [
        ("投稿/Cover_Letter_2026-11-17.docx", "Cover_Letter.docx"),
        ("投稿/Cover_Letter_2026-11-17.pdf", "Cover_Letter.pdf"),
    ],
    "03_Figures": [
        ("paper/figures/fig3_writeback_scope.png", "Figure1_writeback_scope.png"),
        ("paper/figures/fig2_detection_scores.png", "Figure2_detection_scores.png"),
        ("报告/assets/b2_sailboat_B_034.png", "Figure3_B2_example.png"),
    ],
    "04_Tables": [
        ("paper/tables/rq1.tex", "Table1_RQ1.tex"),
        ("paper/tables/rq2.tex", "Table2_RQ2.tex"),
        ("paper/tables/rq3.tex", "Table3_RQ3.tex"),
        ("paper/tables/b2.tex", "Table4_B2.tex"),
        ("paper/tables/ablation_k.tex", "Table5_k_ablation.tex"),
    ],
    "05_Supplementary": [
        ("报告/RQ3_测试集逐序列_2026-11-18.xlsx", "RQ3_test_per_sequence.xlsx"),
        ("报告/RQ3_D1D2补充实验_2026-11-17.pdf", "RQ3_supplement.pdf"),
        ("报告/B2_All-In-One补充实验_2026-11-18.pdf", "B2_supplement.pdf"),
        ("报告/B2_长度扩展_2026-11-18.pdf", "B2_length_extension.pdf"),
        ("报告/RQ3_扫描检测器补充_2026-11-18.pdf", "RQ3_scan_detector.pdf"),
        ("报告/位置敏感性补充_2026-11-18.pdf", "position_sensitivity.pdf"),
        ("报告/多区间缺陷补充_2026-11-18.pdf", "multi_interval.pdf"),
        ("报告/三段多区间补充_2026-11-18.pdf", "multi_mixed.pdf"),
        ("报告/多区间专用检测器补充_2026-11-18.pdf", "multi_scan_detector.pdf"),
        ("报告/边缘感知估计器补充_2026-11-18.pdf", "edge_aware_A3e.pdf"),
        ("报告/三段多区间检测补充_2026-11-18.pdf", "multi_scan_three.pdf"),
        ("报告/B2_两区间缺陷_2026-11-19.pdf", "B2_multi_interval.pdf"),
        ("报告/B2_三段缺陷_2026-11-19.pdf", "B2_three_interval.pdf"),
        ("报告/四段多区间补充_2026-11-19.pdf", "multi_four.pdf"),
        ("报告/B2_四段缺陷_2026-11-19.pdf", "B2_four_interval.pdf"),
        ("报告/四段多区间检测补充_2026-11-19.pdf", "multi_scan_four.pdf"),
        ("报告/自然标注预实验_2026-11-19.pdf", "natural_annotation_preliminary.pdf"),
        ("报告/自然标注_单标注_2026-11-20.pdf", "natural_annotation_single.pdf"),
        ("报告/研究报告与复现说明_2026-11-20.pdf", "research_report_reproducibility.pdf"),
        ("报告/内容补强_全13段与端到端_2026-11-21.pdf", "content_strengthening_full13_e2e.pdf"),
        ("报告/边界位置补充_2026-11-18.pdf", "edge_position.pdf"),
    ],
    "06_Metadata": [
        ("投稿/Highlights_2026-11-18.txt", "Highlights.txt"),
        ("投稿/submission_metadata_2026-11-18.json", "submission_metadata.json"),
    ],
}

README = """# 投稿包（2026-11-18）

期刊：Signal, Image and Video Processing (Springer)

## 上传建议

- `01_Manuscript/Manuscript.docx` 或 `.pdf`：正文（12 页、5 表、3 图、41 条引用）
- `02_Cover_Letter/Cover_Letter.pdf`：cover letter
- `03_Figures/`：Figure 1–3，300 dpi PNG
- `04_Tables/`：Table 1–5 的 LaTeX 源码（Word 版表格已在正文内）
- `05_Supplementary/`：RQ3 逐序列表、RQ3 补充、B2 补充
- `06_Metadata/`：Highlights 与投稿元数据

## 仍待作者补

- 作者、单位、通讯作者、基金；
- Springer 模板排版、参考文献样式、英文母语润色、查重；
- 上传系统后核对生成的 PDF。

## 不伪造声明

正文所有头条数字来自 `results/FREEZE_2026-11-17.json`（37/37 PASS）。
RQ3 测试集召回 0.744（95% CI 0.485-0.982），未达 0.90；B1 代码未公开，B3–B5 未运行。
"""


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for sub, items in FILES.items():
        d = os.path.join(OUT, sub); os.makedirs(d)
        for src, dst in items:
            s = os.path.join(WS, src)
            if not os.path.exists(s):
                print("MISSING", src); continue
            shutil.copy2(s, os.path.join(d, dst))
    with open(os.path.join(OUT, "README_投稿包.md"), "w", encoding="utf-8") as fh:
        fh.write(README)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, os.path.dirname(OUT)))
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print("bundle", OUT, "files", n, "zip", round(os.path.getsize(ZIP) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
