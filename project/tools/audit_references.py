"""Audit citations: keys resolve in BibTeX, numbering is complete, no placeholders."""
from __future__ import annotations

import os
import re

from docx import Document

WS = r"F:\周四焜哥论文"
MD = os.path.join(WS, "paper", "manuscript.md")
BIB = os.path.join(WS, "paper", "references.bib")
DOCX = os.path.join(WS, "paper", "manuscript_draft_2026-11-17.docx")
OUT = os.path.join(WS, "results", "reference_audit.md")


def main():
    md = open(MD, encoding="utf-8").read()
    keys = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", md):
        for k in (x.strip() for x in m.group(1).split(",")):
            if k and k not in keys:
                keys.append(k)
    bib = open(BIB, encoding="utf-8").read()
    bibkeys = set(re.findall(r"@\w+\{([^,]+),", bib))
    missing = [k for k in keys if k not in bibkeys]

    doc = Document(DOCX)
    text = "\n".join(p.text for p in doc.paragraphs)
    refs = re.findall(r"^\[(\d+)\]\s+", text, flags=re.M)
    nums = sorted({int(x) for x in refs})
    complete = nums == list(range(1, len(keys) + 1))
    placeholders = text.count("[?]")

    lines = ["# Reference audit", "",
             f"- cited keys: {len(keys)}",
             f"- BibTeX entries: {len(bibkeys)}",
             f"- missing in BibTeX: {len(missing)}" + (f" -> {missing}" if missing else ""),
             f"- numbered entries in DOCX: {len(refs)}",
             f"- numbering complete 1..N: {'PASS' if complete else 'FAIL'}",
             f"- placeholder [ ? ] occurrences: {placeholders}",
             "", "STATUS: " + ("PASS" if not missing and complete and placeholders == 0 else "FAIL")]
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    raise SystemExit(0 if lines[-1].endswith("PASS") else 1)


if __name__ == "__main__":
    main()
