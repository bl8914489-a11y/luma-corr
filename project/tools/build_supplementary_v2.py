"""Build the Supplementary Material for the narrowed manuscript."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

WS = r"F:\周四焜哥论文"
OUT = os.path.join(WS, "paper", "Supplementary_v2.docx")

FULL = {
    "A": {"A1": (19.90, 19.89, 19.90), "A2": (2.29, 18.26, 19.52), "A3": (2.06, 1.48, 2.40),
          "A4": (2.29, 18.26, 19.52), "A5": (2.02, 1.87, 3.09), "A6": (20.35, 20.25, 20.31),
          "A7": (3.37, 3.25, 3.81), "A7f": (32.87, 33.02, 33.11), "A8": (7.94, 18.88, 20.36),
          "A9": (2.14, 1.98, 3.42)},
    "B": {"A1": (53.62, 53.68, 54.02), "A2": (8.55, 52.05, 53.66), "A3": (8.16, 7.65, 8.07),
          "A4": (8.55, 52.05, 53.66), "A5": (2.53, 2.40, 3.52), "A6": (33.64, 33.33, 33.51),
          "A7": (2.59, 1.97, 2.95), "A7f": (1.46, 1.48, 1.45), "A8": (8.37, 50.42, 53.48),
          "A9": (8.35, 8.17, 8.75)},
    "B13": {"A1": (20.49, 20.54, 20.63), "A2": (4.18, 18.83, 20.26), "A3": (3.92, 3.20, 4.03),
            "A4": (4.18, 18.83, 20.26), "A5": (2.12, 1.97, 3.16), "A6": (21.30, 21.16, 21.27),
            "A7": (2.11, 1.48, 2.50), "A7f": (32.24, 32.39, 32.42), "A8": (7.84, 19.54, 21.16),
            "A9": (3.93, 3.79, 4.77)},
}


_DOC = None


def p(text, bold=False, size=10.5):
    par = _DOC.add_paragraph(); par.paragraph_format.space_after = Pt(4)
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text); r.font.size = Pt(size); r.font.bold = bold
    r.font.name = "Times New Roman"
    r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def table(doc, headers, rows, widths=None, size=8):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    trPr = t.rows[0]._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for i, x in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(str(x)); r.font.bold = True; r.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(x)); r.font.size = Pt(size)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()


doc = Document(); _DOC = doc
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(1.8); s.top_margin = s.bottom_margin = Cm(1.8)
st = doc.styles["Normal"]; st.font.name = "宋体"; st.font.size = Pt(10.5)

doc.add_heading("Supplementary Material", level=0)
p("Local Brightness Correction under Known Intervals: A Controlled Benchmark, Sensitivity Analysis, and Reproducibility Study", size=11)

doc.add_heading("S1  Full 10-method matrix (13 sequences)", level=1)
p("Y-MAE, lower is better; means over 13 sequences. The main paper reports seven representative methods; this table is the complete matrix. Bootstrap 95% CIs are in `results/tables/full13_matrix.csv`.")
for inj, label in (("A", "A: offset −20"), ("B", "B: gamma 2.0"), ("B′", "B′: gamma 1.3")):
    key = "B13" if inj == "B′" else inj
    p(label, bold=True)
    table(doc, ["Method", "len1", "len4", "len12"], [
        [m, f"{FULL[key][m][0]:.2f}", f"{FULL[key][m][1]:.2f}", f"{FULL[key][m][2]:.2f}"]
        for m in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A7f", "A8", "A9")
    ], [3.0, 3.0, 3.0, 3.0])

doc.add_heading("S2  Detection (removed from the main paper)", level=1)
p("Frame-level detection over 13 sequences and three injections. The main paper only states the held-out boundary result; the full study is here.")
table(doc, ["Detector", "R@1", "P@1", "R@4", "P@4", "R@12", "P@12", "Clean FP"], [
    ["Local median (legacy)", "1.000", "0.104", "0.462", "0.144", "0.263", "0.210", "0.214"],
    ["BlazeBVD Eq. (5), KL", "1.000", "0.045", "0.686", "0.111", "0.280", "0.146", "0.328"],
    ["Global-hist. JS + hysteresis", "0.667", "0.052", "0.853", "0.289", "0.761", "0.499", "0.187"],
    ["Rolling-hist. JS + CUSUM", "0.846", "0.135", "0.897", "0.383", "0.825", "0.737", "0.100"],
], [4.6, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 2.0])
p("The held-out nine-sequence test split gives 0.744 recall / 0.641 precision for CUSUM. Fixed-length scan reaches 0.772/0.772 at len12 but 0.370/0.630 at len1/4; multi-interval scan reaches 0.925/0.530 (two intervals) and 0.928/0.546 (three), with 2.8 spans for four true intervals. These are boundary results, not a detector claim.")

doc.add_heading("S3  Natural-clip annotation (single annotator)", level=1)
p("100 clips of 24 frames from the same 13 sequences, 73 positives; single annotator, no second annotator, no kappa. Frame numbers were supplied 1-based and converted to 0-based. The evaluation is detection only: natural clips have no clean reference, so no correction Y-MAE is reported.")
table(doc, ["Metric", "Value"], [
    ["clip precision / recall", "0.720 / 0.247"],
    ["clip TP/FP/FN/TN", "18 / 7 / 55 / 20"],
    ["interval recall", "0.101"],
    ["flicker clip recall", "0.000 (0/19)"],
    ["exposure / gamma clip recall", "0.281 / 0.412"],
], [6.0, 8.0])
p("CUSUM is tuned for sustained plateaus; it does not transfer to natural flicker. This is a limitation, not a main result.")

doc.add_heading("S4  Detection-to-correction propagation", level=1)
p("CUSUM-predicted spans replace the true interval; correction is applied to the predicted spans and evaluated on the true interval. Oracle applies the same corrector to the true interval.")
table(doc, ["Method", "Oracle Y-MAE", "Detected Y-MAE", "Detected OutFrac"], [
    ["A3", "4.47", "7.57", "4.0%"],
    ["A5", "2.67", "5.66", "4.6%"],
    ["A7", "2.66", "5.85", "3.9%"],
    ["A7f", "22.31", "21.60", "5.5%"],
], [3.0, 3.2, 3.2, 3.2])
table(doc, ["Injection", "A3 oracle→detected", "A5 oracle→detected", "A7 oracle→detected"], [
    ["A", "1.94→4.86", "2.48→5.28", "3.53→6.34"],
    ["B", "7.86→10.60", "2.96→5.60", "2.46→5.36"],
    ["B′", "3.62→7.25", "2.56→6.09", "1.99→5.85"],
], [2.4, 4.0, 4.0, 4.0])
p("Detection error inflates correction error by 1.4–3.0× and changes 3.9–5.5% of true-outside pixels. When the interval is uncertain, A5 is the most robust choice.")

doc.add_heading("S5  Multi-interval defects", level=1)
table(doc, ["Setting", "A3", "A7", "OutFrac", "CUSUM recall"], [
    ["Two intervals, len4/12", "1.68–2.25", "2.41–2.80", "0%", "0.60–0.88"],
    ["Three intervals, mixed", "4.92", "2.79", "0%", "0.60"],
    ["Three intervals, same A", "2.10", "3.82", "0%", "0.50"],
    ["Four intervals, mixed", "3.21", "2.77", "0%", "0.62"],
], [5.0, 2.6, 2.6, 2.4, 3.2])
p("Correction remains stable and leaves the outside untouched; detection degrades (0.50–0.88) and multi-span scan trades precision for recall. This is an open problem.")

doc.add_heading("S6  Reproducibility", level=1)
p("The package contains code, configurations, 46 run directories, 16 freeze files, 37 unit tests and a one-click test. The final package has 575 files and 575/575 matching SHA-256 entries after the test; the test no longer rewrites the frozen JSON. Original frames and All-In-One weights are not bundled because of size/licence and must be downloaded from the official sources.")

doc.save(OUT)
print("saved", OUT)
