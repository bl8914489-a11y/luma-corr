"""Add selected VideoDM/Meta sequences from the verified upstream archive.

Usage:
  python tools/add_from_archive.py --zip ... --out F:\\周四焜哥论文 --names yoga
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone

from PIL import Image

DEV = ["sailboat", "book", "horse"]
REAL_T2V = ["book", "asteroids", "astronaut"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--names", nargs="+", required=True)
    args = ap.parse_args()

    manifest_path = os.path.join(args.out, "data", "manifest", "dataset_manifest.json")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    with zipfile.ZipFile(args.zip) as z:
        for name in args.names:
            prefix = f"All-In-One-Deflicker-Dataset/VideoDM/Meta/{name}/"
            members = sorted((n for n in z.namelist() if n.startswith(prefix) and n.endswith(".jpg")),
                             key=lambda n: int(os.path.basename(n).split(".")[0]))
            if not members:
                raise FileNotFoundError(f"{name} not found in archive")
            dst = os.path.join(args.out, "data", "frames", name)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            os.makedirs(dst)
            records = []
            for i, m in enumerate(members):
                b = z.read(m)
                f = os.path.basename(m)
                assert int(f.split(".")[0]) == i
                with Image.open(io.BytesIO(b)) as im:
                    w, h = im.size
                with open(os.path.join(dst, f), "wb") as fh:
                    fh.write(b)
                records.append({"index": i, "file": f, "sha256": sha(b), "bytes": len(b)})
            manifest["sequences"][name] = {
                "member": f"All-In-One-Deflicker-Dataset/VideoDM/Meta/{name}",
                "frame_count": len(records), "width": w, "height": h,
                "frames": records, "split": "dev" if name in DEV else "expansion",
                "real_t2v": name in REAL_T2V,
                "source": "extracted verbatim from the verified upstream archive",
            }
            print(f"added {name}: {len(records)} frames {w}x{h}")

    manifest["updated_utc"] = datetime.now(timezone.utc).isoformat()
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, manifest_path)
    print("manifest updated")


if __name__ == "__main__":
    main()
