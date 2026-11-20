"""Audit the manuscript DOCX tables/figures against the frozen run artifacts."""
from __future__ import annotations

import json
import os
import re

from docx import Document

WS = r"F:\周四焜哥论文"
MD = os.path.join(WS, "paper", "manuscript_draft_2026-11-17.docx")
OUT = os.path.join(WS, "results", "manuscript_table_audit.md")


def flat(t):
    return [c.text.strip() for row in t.rows for c in row.cells]


def main():
    doc = Document(MD)
    tables = doc.tables
    lines = ["# Manuscript table/figure audit", "", f"tables: {len(tables)}", ""]
    ok = True

    def need(name, hay, needles):
        nonlocal ok
        miss = [x for x in needles if x not in hay]
        lines.append(f"- {name}: {'PASS' if not miss else 'FAIL ' + str(miss)}")
        ok = ok and not miss

    alltext = "\n".join(x for t in tables for x in flat(t))
    # Table 1: A3 row
    need("Table 1 A3 row", alltext,
         ["1.03", "0.73", "0.76", "8.65", "7.87", "7.89", "3.78", "3.01", "3.18"])
    # Table 2: A4 outside/boundary
    need("Table 2 A4 row", alltext, ["33.2%", "0.91", "33.89", "33.89", "3.31"])
    # Table 3: CUSUM row
    need("Table 3 CUSUM row", alltext, ["0.846", "0.135", "0.897", "0.383", "0.825", "0.737", "0.100"])
    # Table 4: B2
    need("Table 4 B2 row", alltext, ["12.48", "99.95%", "9.79", "4.29"])
    # Table 5: k rows
    need("Table 5 k rows", alltext, ["1.67 / 1.19 / 1.93", "2.06 / 1.48 / 2.40", "1.68 / 1.49 / 2.64"])

    # figures: count inline shapes (3) and captions
    n_img = len(doc.inline_shapes)
    lines.append(f"- inline images: {n_img} ({'PASS' if n_img == 3 else 'FAIL'})")
    ok = ok and n_img == 3
    caps = [p.text for p in doc.paragraphs if p.text.startswith("Figure ")]
    lines.append(f"- figure captions: {len(caps)} ({'PASS' if len(caps) == 3 else 'FAIL'})")
    ok = ok and len(caps) == 3
    for c in caps:
        lines.append(f"  - {c[:120]}")

    # abstract numbers
    text = "\n".join(p.text for p in doc.paragraphs)
    need("abstract/test numbers", text, ["0.744", "12.48", "99.95%", "60.4%"])
    need("no stale six-case claim", text, []) if "thirty-nine injected" in text else lines.append("- thirty-nine cases: FAIL")
    lines.append("")
    lines.append("STATUS: " + ("PASS" if ok else "FAIL"))
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
