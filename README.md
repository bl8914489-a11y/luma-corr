# Local brightness correction under known intervals

Code, frozen tables and manuscript for the paper:

> Local Brightness Correction under Known Intervals: A Controlled Benchmark,
> Sensitivity Analysis, and Reproducibility Study.

## What is here

- `project/src` — correction, injection, detection, metrics, statistics.
- `project/scripts` — matrix, detection, B2, multi-interval, evaluation.
- `project/configs` — fixed configurations.
- `project/tests` — 37 unit tests.
- `results/tables/full13_matrix.csv` — full 13-sequence matrix with bootstrap CIs.
- `results/FREEZE_*.json` — frozen numbers and hashes.
- `paper/` — narrowed manuscript v2, Supplementary, figures, references.
- `投稿/` — cover letter.

## Quick start

```bash
python -m unittest discover -s project/tests -v
LUMA_WS=$PWD python project/tools/verify_numbers.py
```

The full one-click package (all run artifacts, reports, hashes) is distributed
separately; see the paper's Data availability statement. Raw frames and
All-In-One weights are not included (size/licence); download them from the
official sources listed in `data/manifest/`.

## Data

Blind-Video-Deflickering-Dataset (VideoDM/Meta subset), CC BY 4.0.
Archive SHA-256: 737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e.

## License

Code: MIT. Manuscript: CC BY 4.0. Dataset: CC BY 4.0.

## Repository URL

Replace the placeholder in the manuscript and README with the final GitHub URL:
`https://github.com/[your-account]/luma-corr`.
