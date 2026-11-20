from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

WS = Path(r"F:\周四焜哥论文")


def freeze(fid: str, run_dir: Path, files: list[str], expected: int, extra: dict | None = None) -> None:
    rows = list(csv.DictReader((run_dir / files[0]).open(encoding="utf-8")))
    arts = {}
    for f in files:
        arts[f] = {"sha256": hashlib.sha256((run_dir / f).read_bytes()).hexdigest()}
    out = {"freeze_id": fid, "status": "PASS" if len(rows) == expected else "FAIL",
           "n_rows": len(rows), "artifacts": arts}
    if extra:
        out.update(extra)
    (WS / "results" / f"FREEZE_{fid}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(fid, out["status"], len(rows))


freeze("E2E_2026-11-21", WS / "results/runs/e2e_detection_correction_v1",
       ["per_condition.csv", "summary.json"], 624)
freeze("FULL13_2026-11-21", WS / "results/tables",
       ["full13_matrix.csv"], 90)

# add package artifacts
p = WS / "project/tools/build_repro_package.py"
lines = p.read_text(encoding="utf-8").splitlines()
out = []
for line in lines:
    out.append(line)
    if 'results/FREEZE_NATURAL_SINGLE_2026-11-20.json' in line:
        out.append('    ("results/FREEZE_E2E_2026-11-21.json", None),')
        out.append('    ("results/FREEZE_FULL13_2026-11-21.json", None),')
        out.append('    ("results/FULL13_MATRIX_2026-11-21.md", None),')
        out.append('    ("results/B2_TIMING_2026-11-21.md", None),')
        out.append('    ("results/b2_logs", None),')
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("package COPY updated")
