from pathlib import Path

p = Path(r"F:\周四焜哥论文\project\tools\verify_numbers.py")
s = p.read_text(encoding="utf-8")
s = s.replace(
    'OUT = os.path.join(WS, "results", "FREEZE_2026-11-17.json")',
    'OUT = os.environ.get("FREEZE_OUT", os.path.join(WS, "results", "FREEZE_2026-11-17.json"))',
)
p.write_text(s, encoding="utf-8")

p = Path(r"F:\周四焜哥论文\project\tools\build_repro_package.py")
lines = p.read_text(encoding="utf-8").splitlines()
out = []
for line in lines:
    if "verify_numbers.py" in line and "& $py" in line:
        out.append('                 "$env:FREEZE_OUT = Join-Path $env:TEMP \'luma_freeze_check.json\'\\n"')
    out.append(line)
p.write_text("\n".join(out) + "\n", encoding="utf-8")
print("patched")
