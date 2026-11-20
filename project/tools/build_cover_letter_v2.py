"""Build the SIVP cover letter for the narrowed manuscript."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "投稿", "Cover_Letter_v2_2026-11-21.docx")

doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2); s.top_margin = s.bottom_margin = Cm(2.0)
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)


def p(text, bold=False, size=11):
    par = doc.add_paragraph(); par.paragraph_format.space_after = Pt(6)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


p("Cover Letter", bold=True, size=14)
p("Manuscript: Local Brightness Correction under Known Intervals: A Controlled Benchmark, Sensitivity Analysis, and Reproducibility Study")
p("Journal: Signal, Image and Video Processing (SIVP)")
p("Date: 21 November 2026")
p("Dear Editor,")
p("We submit the enclosed manuscript for consideration as an original research article in Signal, Image and Video Processing. "
  "The manuscript studies a practically relevant but often implicit setting: the defective interval is known, and a deterministic "
  "corrector must restore it without changing the rest of the video. This differs from blind deflickering, which processes the whole "
  "sequence and is scored on whole-video quality.")
p("The contribution is a controlled, reproducible empirical study, not a new network. It contains three parts: "
  "(i) a 1,170-condition benchmark over 13 sequences, three injections and ten deterministic correctors; "
  "(ii) a local-versus-global write-back comparison with an explicit boundary decomposition; "
  "and (iii) a clipping attribution for gamma residuals, together with an open deep baseline (All-In-One) and a one-click reproduction package.")
p("We deliberately do not claim state-of-the-art performance. Detection, natural-clip annotation and end-to-end propagation are "
  "reported in the Supplementary Material, including the negative detection result (0.744 held-out recall; 0/19 natural flicker clips). "
  "The main paper is limited to claims that the controlled experiments support.")
p("The manuscript is original, has not been published previously, and is not under consideration elsewhere. All authors have approved "
  "the submission and declare no competing interests. The data and code availability statement is included; the reproduction package "
  "contains per-frame hashes, 37 unit tests and 37 frozen checks.")
p("We suggest that the work fits the journal's interest in practical video-processing developments and reproducible experimental accounts. "
  "We would be grateful for your consideration.")
p("Sincerely,")
p("[Author Name], on behalf of all authors")
p("[Affiliation]")
p("[Email]")
p("[ORCID]")
doc.save(OUT)
print("saved", OUT)
