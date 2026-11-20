"""Convert paper/manuscript.md into a submission-style DOCX with numbered citations."""
from __future__ import annotations

import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

WS = r"F:\周四焜哥论文"
MD = os.environ.get("MD", os.path.join(WS, "paper", "manuscript.md"))
BIB = os.path.join(WS, "paper", "references.bib")
OUT = os.environ.get("OUT", os.path.join(WS, "paper", "manuscript_draft_2026-11-17.docx"))

sys.path.insert(0, os.path.join(WS, "project", "tools"))
from export_literature_bib import split_fields  # noqa: E402


def load_bib():
    text = open(BIB, encoding="utf-8").read()
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        start = m.end()
        # find matching closing brace of this entry
        depth, i = 1, start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        entries[m.group(2).strip()] = (m.group(1).lower(), body)
    return entries


def fields_of(body):
    try:
        return split_fields(body)
    except Exception:
        return {}


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[{}]", "", s or "")).strip()


def format_ref(key, entries):
    if key not in entries:
        return key
    etype, body = entries[key]
    f = fields_of(body)
    authors = clean(f.get("author", ""))
    authors = authors.replace(" and ", ", ")
    title = clean(f.get("title", ""))
    venue = clean(f.get("journal") or f.get("booktitle") or f.get("publisher") or f.get("howpublished") or "")
    year = clean(f.get("year", ""))
    volume = clean(f.get("volume", ""))
    number = clean(f.get("number", ""))
    pages = clean(f.get("pages", ""))
    doi = clean(f.get("doi", ""))
    eprint = clean(f.get("eprint", ""))
    out = f"{authors}. {title}."
    if venue:
        out += f" {venue}"
        if volume:
            out += f", {volume}"
        if number:
            out += f"({number})"
        if pages:
            out += f", {pages}"
        if year:
            out += f", {year}"
        out += "."
    elif year:
        out += f" {year}."
    if eprint:
        out += f" arXiv:{eprint}."
    if doi:
        out += f" https://doi.org/{doi}."
    return out


def latex_to_text(s):
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = s.replace(r"\ell", "l").replace(r"\gamma", "gamma").replace(r"\times", "x")
    s = s.replace(r"\in", " in ").replace(r"\dots", "...")
    s = s.replace(r"\hat I", "I_hat")
    s = re.sub(r"_\{([^}]*)\}", r"[\1]", s)
    s = re.sub(r"\^\{([^}]*)\}", r"^\1", s)
    s = re.sub(r"\\[a-zA-Z]+", "", s)
    s = s.replace("$", "").replace("{", "").replace("}", "")
    return s


def add_runs(par, text, size=10.5, base_bold=False):
    text = latex_to_text(text)
    for part in re.split(r"(\*\*.+?\*\*|\*[^*]+?\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            bold, italic, chunk = True, False, part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            bold, italic, chunk = base_bold, True, part[1:-1]
        else:
            bold, italic, chunk = base_bold, False, part
        r = par.add_run(chunk)
        r.font.size = Pt(size)
        r.font.name = "Times New Roman"
        r.font.bold = bold
        r.font.italic = italic
        r._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def add_table(doc, rows):
    header, body = rows[0], rows[1:]
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(8.0)
        r.font.name = "Times New Roman"
    trPr0 = t.rows[0]._tr.get_or_add_trPr()
    from docx.oxml import OxmlElement as _OE
    trPr0.append(_OE("w:tblHeader")); trPr0.append(_OE("w:cantSplit"))
    for row in body:
        tr = t.add_row()
        tr._tr.get_or_add_trPr().append(_OE("w:cantSplit"))
        cells = tr.cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(v); r.font.size = Pt(8.0)
            r.font.name = "Times New Roman"
    doc.add_paragraph()


def main():
    entries = load_bib()
    md = open(MD, encoding="utf-8").read()
    # citation numbering in order of appearance
    order = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", md):
        for k in (x.strip() for x in m.group(1).split(",")):
            if k and k not in order:
                order.append(k)
    num = {k: i + 1 for i, k in enumerate(order)}

    def cite_repl(m):
        keys = [x.strip() for x in m.group(1).split(",")]
        return "[" + ",".join(str(num.get(k, "?")) for k in keys) + "]"

    md = re.sub(r"\\cite\{([^}]+)\}", cite_repl, md)
    md = md.replace("$", "")

    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(10.5)

    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(line[2:]); r.font.size = Pt(16); r.font.bold = True; r.font.name = "Times New Roman"
            i += 1
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=1)
            i += 1
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=2)
            i += 1
        elif line.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if m:
                path = os.path.normpath(os.path.join(os.path.dirname(MD), m.group(2)))
                if os.path.exists(path):
                    doc.add_picture(path, width=Cm(16.0))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = cap.add_run(m.group(1)); r.font.size = Pt(8.0); r.font.italic = True
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                add_table(doc, rows)
        elif line.startswith("- "):
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            add_runs(p, line[2:].strip())
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                add_runs(p, " " + lines[i].strip())
                i += 1
        else:
            buf = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "![")):
                buf.append(lines[i].strip())
                i += 1
            text = " ".join(buf)
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_runs(p, text)

    doc.add_heading("References", level=1)
    for k in order:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        r = p.add_run(f"[{num[k]}] {format_ref(k, entries)}")
        r.font.size = Pt(8.0); r.font.name = "Times New Roman"

    doc.save(OUT)
    print("saved", OUT, "citations", len(order))


if __name__ == "__main__":
    main()
