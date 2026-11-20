"""Fetch BibTeX metadata for the curated literature library via doi.org.

Reads data/literature/文献基线库_精选(1).xlsx, resolves every DOI through
content negotiation (Accept: application/x-bibtex), normalises citation keys,
and writes a consolidated .bib plus a per-entry status CSV.  Entries without a
DOI get a minimal @misc record that is explicitly marked as incomplete.
"""
from __future__ import annotations

import csv
import os
import re
import time
import urllib.error
import urllib.request

import openpyxl

WS = os.environ.get("LUMA_WS", r"F:\周四焜哥论文")
SRC = os.path.join(WS, "data", "literature", "文献基线库_精选(1).xlsx")
OUT_DIR = os.path.join(WS, "报告", "refs")
BIB = os.path.join(WS, "报告", "参考文献_精选99_2026-11-17.bib")
STATUS = os.path.join(OUT_DIR, "doi_fetch_status.csv")
RAW = os.path.join(OUT_DIR, "raw")
UA = "dsh-literature/1.0 (research reference export)"


def fetch_bibtex(doi: str) -> tuple[str | None, str]:
    url = "https://doi.org/" + doi
    req = urllib.request.Request(url, headers={"Accept": "application/x-bibtex", "User-Agent": UA})
    last = ""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace"), "ok"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            last = type(e).__name__
        time.sleep(1.0 + attempt)
    return None, last


def split_fields(body: str) -> dict[str, str]:
    """Split the inside of a BibTeX entry into top-level fields."""
    fields: dict[str, str] = {}
    i, n = 0, len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        m = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[i:])
        if not m:
            break
        name = m.group(1).lower()
        i += m.end()
        if i >= n:
            break
        if body[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value = body[i + 1:j - 1]
            i = j
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            value = body[i + 1:j]
            i = j + 1
        else:
            m2 = re.match(r"[^,\n]+", body[i:])
            value = m2.group(0).strip() if m2 else ""
            i += m2.end() if m2 else 0
        fields[name] = " ".join(value.split())
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i < n and body[i] == ",":
            i += 1
    return fields


def parse_entry(txt: str) -> tuple[str, dict[str, str]]:
    m = re.match(r"\s*@(\w+)\s*\{\s*([^,]+),", txt)
    if not m:
        return "misc", {}
    etype = m.group(1).lower()
    start = m.end()
    body = txt[start:]
    # strip the final closing brace of the entry
    if body.rstrip().endswith("}"):
        body = body.rstrip()[:-1]
    return etype, split_fields(body)


def first_surname(author: str) -> str:
    if not author:
        return "anon"
    first = author.split(" and ")[0].strip()
    if "," in first:
        sur = first.split(",")[0]
    else:
        sur = first.split()[-1] if first.split() else "anon"
    sur = re.sub(r"[^A-Za-z]", "", sur)
    return sur.lower() or "anon"


STOP = {"a", "an", "the", "on", "of", "for", "towards", "toward", "via", "with", "and"}


def title_word(title: str) -> str:
    for w in re.findall(r"[A-Za-z0-9]+", title.lower()):
        if w not in STOP and len(w) > 2:
            return w
    return "ref"


def make_key(fields: dict[str, str], idx: int) -> str:
    sur = first_surname(fields.get("author", ""))
    year = re.sub(r"[^0-9]", "", fields.get("year", ""))[:4] or "0000"
    word = title_word(fields.get("title", ""))
    return f"{sur}{year}{word}"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    wb = openpyxl.load_workbook(SRC, data_only=True)
    ws = wb["精选基线库"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    data = [dict(zip(hdr, r)) for r in rows[1:] if r[0] is not None]

    statuses = []
    entries = []
    used: dict[str, int] = {}
    for d in data:
        idx = int(d["序号"])
        doi = (d["DOI"] or "").strip() if d["DOI"] else ""
        txt, status = (fetch_bibtex(doi) if doi else (None, "no DOI in source"))
        if txt:
            etype, fields = parse_entry(txt)
            with open(os.path.join(RAW, f"{idx:03d}.bib"), "w", encoding="utf-8") as fh:
                fh.write(txt)
        else:
            etype, fields = "misc", {
                "title": d["标题"], "year": str(d["年份"]),
                "howpublished": d["期刊/会议"] or "", "note": "DOI unavailable in source library",
            }
            txt = None
        if not fields.get("title"):
            fields["title"] = d["标题"]
        if not fields.get("year"):
            fields["year"] = str(d["年份"])
        key = make_key(fields, idx)
        used[key] = used.get(key, 0) + 1
        if used[key] > 1:
            key = f"{key}{chr(96 + used[key])}"
        fields["_key"] = key
        fields["_type"] = etype
        entries.append((idx, d, fields))
        statuses.append({
            "序号": idx, "主题": d["主题"], "年份": d["年份"], "DOI": doi,
            "fetch_status": status, "cite_key": key, "bib_type": etype,
            "first_author": first_surname(fields.get("author", "")),
            "title": fields.get("title", ""), "venue": fields.get("booktitle") or fields.get("journal") or d["期刊/会议"],
            "grade": d["可复现等级"],
        })
        print(f"{idx:3d} {status:10s} {key}", flush=True)
        time.sleep(0.15)

    lines = ["% BibTeX exported from 文献基线库_精选(1).xlsx",
             "% DOI metadata fetched via doi.org content negotiation on 2026-11-17.",
             "% Entries marked 'no DOI in source' are incomplete and need manual completion.",
             ""]
    for idx, d, fields in entries:
        key = fields.pop("_key")
        etype = fields.pop("_type")
        lines.append(f"% [{idx}] {d['主题']} | grade {d['可复现等级']} | source DOI: {d['DOI'] or 'none'}")
        lines.append(f"@{etype}{{{key},")
        for k, v in fields.items():
            if k in ("_key", "_type") or not v:
                continue
            lines.append(f"  {k} = {{{v}}},")
        lines.append("}")
        lines.append("")
    with open(BIB, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    with open(STATUS, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(statuses[0]))
        w.writeheader()
        w.writerows(statuses)

    ok = sum(1 for s in statuses if s["fetch_status"] == "ok")
    print(f"done: {ok}/{len(statuses)} fetched, bib={BIB}")


if __name__ == "__main__":
    main()
