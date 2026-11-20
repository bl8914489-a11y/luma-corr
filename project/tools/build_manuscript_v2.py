"""Create the narrowed minimal-compliance manuscript v2 from the full draft."""
from __future__ import annotations

import re
from pathlib import Path

WS = Path(r"F:\周四焜哥论文")
src = (WS / "paper/manuscript.md").read_text(encoding="utf-8")

# keep a copy of v1
(WS / "paper/manuscript_v1.md").write_text(src, encoding="utf-8")


def cut(text: str, start: str, end: str, repl: str) -> str:
    a = text.index(start); b = text.index(end, a)
    return text[:a] + repl + text[b:]


# title + author placeholder
src = src.replace(
    "# Local Brightness Correction for Known Defect Intervals in Generated Video: A Reproducible Empirical Study",
    "# Local Brightness Correction under Known Intervals: A Controlled Benchmark, Sensitivity Analysis, and Reproducibility Study\n\n"
    "**Authors:** [Author Name]¹, [Corresponding Author]¹✉  \n"
    "**Affiliations:** [Department, University, City, Country]  \n"
    "**Corresponding email:** [corresponding@example.edu]  \n"
    "**ORCID:** [0000-0000-0000-0000]",
)

# abstract
abstract = """## Abstract

Blind video deflickering methods process a whole sequence and are scored on overall quality, but editing and quality-control pipelines often know, or can verify, the defective interval. We study this known-interval setting as a controlled empirical problem: how accurately can a deterministic corrector restore the interval, what happens outside it, and which corrector should be chosen? We build a reproducible benchmark of 13 sequences, 3 injections (additive offset, gamma 2.0, gamma 1.3), 3 interval lengths and 10 deterministic correctors (1,170 conditions). On all 13 sequences, the outside-linear estimator A3 reduces interval Y-MAE from 19.90 to 2.06/1.48/2.40 for offsets of length 1/4/12. Under gamma 2.0, A3 leaves 8.16/7.65/8.07, whereas a fixed inverse-gamma reference (A7f) reaches 1.46/1.48/1.45 and the adaptive A7 reaches 2.59/1.97/2.95. Local write-back changes 0% of outside pixels; the same estimator with full-sequence write-back changes 33.2%. All-In-One, an open deep blind baseline, reaches 12.48 Y-MAE but rewrites 99.95% of outside pixels. We also report sensitivity, position, edge behaviour, CPU cost and a one-click reproduction package. Detection is deliberately left to the supplement: its held-out recall is 0.744, and natural flicker is not solved. The contribution is a controlled, reproducible reference for a practically relevant but often implicit setting, not a new deflickering network.

**Keywords:** video deflickering; local brightness correction; controlled benchmark; reproducibility; exposure correction
"""
src = cut(src, "## Abstract", "## 1 Introduction", abstract)

# Table 1 -> full 13 sequences, 7 representative methods
table1 = """**Table 1.** Interval Y-MAE over all 13 sequences (lower is better; mean of 13). The full 10-method matrix is in Supplementary Table S1.

| Method | A: 1 / 4 / 12 | B: 1 / 4 / 12 | B′: 1 / 4 / 12 |
|---|---|---|---|
| A1 No-op | 19.90 / 19.89 / 19.90 | 53.62 / 53.68 / 54.02 | 20.49 / 20.54 / 20.63 |
| A2 Local median-7 | 2.29 / 18.26 / 19.52 | 8.55 / 52.05 / 53.66 | 4.18 / 18.83 / 20.26 |
| A3 Outside linear k=3 | 2.06 / 1.48 / 2.40 | 8.16 / 7.65 / 8.07 | 3.92 / 3.20 / 4.03 |
| A4 Full-seq median-7 | 2.29 / 18.26 / 19.52 | 8.55 / 52.05 / 53.66 | 4.18 / 18.83 / 20.26 |
| A5 STE histogram | 2.02 / 1.87 / 3.09 | 2.53 / 2.40 / 3.52 | 2.12 / 1.97 / 3.16 |
| A7 Adaptive gamma | 3.37 / 3.25 / 3.81 | 2.59 / 1.97 / 2.95 | 2.11 / 1.48 / 2.50 |
| A9 Kalman/RTS | 2.14 / 1.98 / 3.42 | 8.35 / 8.17 / 8.75 | 3.93 / 3.79 / 4.77 |

Table 1 uses all 13 sequences, not a development subset. Under A, A3 is the best corrector (2.06/1.48/2.40), but A5 is slightly better at length 1 (2.02). Under B, A3 leaves about 8, A7 reduces this to 2.59/1.97/2.95, and the gamma-known reference A7f reaches 1.46/1.48/1.45. Under B′, A7 is best (2.11/1.48/2.50) and A5 is close (2.12/1.97/3.16). A3 is therefore not universally best, and A7 is not the universal gamma solution: the correct choice depends on the injection family and on whether the gamma is known.

"""
src = cut(src, "**Table 1.**", "### 4.3 Clipping attribution under gamma", table1)

# detection subsection -> short pointer
src = cut(src, "### 3.5 Detection and interval post-processing", "### 3.6 Metrics",
          """### 3.5 Detection (supplementary)

Detection is outside the minimal claim set: the main experiments assume the interval is known. The full detector study (1,300 conditions, Eq. (5) reimplementation, CUSUM, scan and multi-interval variants), the natural-clip annotation (100 clips, single annotator, no kappa) and the end-to-end propagation analysis are reported in the Supplementary Material. For transparency, the held-out CUSUM recall is 0.744 and natural flicker is not solved; neither is used as a main contribution.

""")

# remove RQ3 main section
src = cut(src, "### 4.5 RQ3: detection and its generalisation gap", "### 4.6 B2",
          """### 4.5 Detection boundary (supplementary)

The held-out CUSUM detector reaches 0.744 recall and 0.641 precision on the nine test sequences, and the natural-clip check detects 0/19 flicker clips. Both results are reported in full in the Supplementary Material. They define the boundary of the present contribution: the correction benchmark assumes a known interval, and the detector is not claimed to be a solution.

""")

# remove end-to-end section
src = cut(src, "### 4.8 End-to-end: detection error propagates into correction error", "### 4.9 Reproducibility checks", "")

# renumber remaining experiment subsections
src = src.replace("### 4.6 B2: a deep blind baseline under the same constraint", "### 4.6 B2: a deep blind baseline under the same constraint")
src = src.replace("### 4.7 Ablations", "### 4.7 Sensitivity, position and ablations")
src = src.replace("### 4.9 Reproducibility checks", "### 4.8 Reproducibility checks")

# renumber B2 table 4 -> 3, ablation table 5 -> 4
src = src.replace("**Table 4.** Deep blind baseline", "**Table 3.** Deep blind baseline")
src = src.replace("Table 4 summarises", "Table 3 summarises")
src = src.replace("Table 4 reports", "Table 3 reports")
src = src.replace("**Table 5.** Context-window ablation", "**Table 4.** Sensitivity of the offset estimator to the context window k")

# discussion: replace detection subsection with scope and selection
src = cut(src, "### 5.2 Detection is the bottleneck, and the prior art is real", "### 5.3 The deep baseline optimises a different objective",
          """### 5.2 Scope and practical selection

The practical question is not "which corrector is best" but "which corrector fits the interval and the available side information". For an additive offset with a reliable interval, A3 is the natural default (2.06/1.48/2.40) and costs about 22 ms per frame. If the gamma is known to be 2.0, the fixed inverse-gamma reference A7f is clearly better (1.46/1.48/1.45); if the gamma is unknown but the defect is gamma-like, A7 (2.59/1.97/2.95) is preferable to A3. For the weaker gamma 1.3, A7 (2.11/1.48/2.50) and A5 (2.12/1.97/3.16) are both reasonable, while A7f is unusable (about 32). When the interval is uncertain, the ranking changes: A5 is the most robust choice, and A3 loses much of its advantage. A3e mitigates edge cases (start 0: 9.41 to 3.06 for length 1) but does not fully close the gap. This selection table, rather than a single SOTA number, is the practical output of the study.

""")

# limitations: append detection/natural/single annotator
src = src.replace("### 5.4 Limitations\n", "### 5.4 Limitations\n\nThe scope is deliberately narrow. The benchmark contains 13 sequences from one public subset and synthetic injections; it does not establish correction accuracy on natural defects. The natural-clip study is single-annotated, has no kappa and only evaluates detection, not correction. Detection remains unsolved (0.744 held-out recall; 0/19 flicker clips). B2 is the only open deep baseline, and B1/B3-B5 were unavailable. The cost, edge and multi-interval results are included to show where the conclusions stop, not to claim generality.\n")

# statements replace data availability
statements = """## Statements and Declarations

**Funding:** The authors received no specific funding for this work.

**Competing interests:** The authors have no relevant financial or non-financial interests to disclose.

**Ethics approval:** This study used a public dataset (CC BY 4.0); no ethical approval was required.

**Consent to participate:** Not applicable.

**Consent for publication:** Not applicable.

**Data availability:** The dataset is publicly available at [repository/DOI to be inserted]. The code, configurations, run artifacts and reproduction package are available at [repository/DOI to be inserted]; the package contains per-frame hashes and a one-click test.

**Author contributions:** [Author Name] conceived the study, implemented the code, ran the experiments and wrote the manuscript. [Corresponding Author] supervised the work and revised the manuscript. All authors read and approved the final manuscript.

**Use of AI tools:** [If applicable, state tool and purpose; otherwise: The authors did not use generative AI tools to draft the manuscript.]
"""
idx = src.index("## Data and code availability")
src = src[:idx] + statements

# remove any duplicate table-number references left from the deleted detection section
src = re.sub(r"Table 3 summarises the detectors.*?\n\n", "", src, flags=re.S)

(WS / "paper/manuscript_v2.md").write_text(src, encoding="utf-8")
print("words", len(re.findall(r"\b\w+\b", src)))
print("headings", [l for l in src.splitlines() if l.startswith("## ") or l.startswith("### ")])
