"""Materialise the VideoDM/Meta development corpus into data/frames and write a
per-frame SHA-256 provenance manifest.

Sources (both ultimately the same upstream archive
All-In-One-Deflicker-Dataset.zip, SHA-256 737252c0...0626e):

* nine sequences already extracted by the predecessor project:
  .../D_九序列输入帧与来源清单/inputs/{fish,horse,knight,...}
* three sequences shipped inside the three-sequence bundle zip
  (asteroids, astronaut, book).

No pixel is re-encoded: the JPEG bytes are copied verbatim.
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

ARCHIVE = {
    "name": "All-In-One-Deflicker-Dataset.zip",
    "url": "https://huggingface.co/datasets/xrenaa/Blind-Video-Deflickering-Dataset",
    "bytes": 2485464921,
    "sha256": "737252c0aa5f3a73972bec126c7edfe0ec7e19798dce6bc63eb4becd3ae0626e",
    "license": "CC BY 4.0",
    "note": "VideoDM/Meta subset; JPEG frames, 76 per sequence, 512x512 RGB",
}
DEV = ["sailboat", "book", "horse"]
REAL_T2V = ["book", "asteroids", "astronaut"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def frame_bytes_ok(b: bytes) -> tuple[int, int]:
    im = Image.open(io.BytesIO(b))
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im.size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nine", required=True)
    ap.add_argument("--small-zip", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frames_root = os.path.join(args.out, "data", "frames")
    manifest_path = os.path.join(args.out, "data", "manifest", "dataset_manifest.json")
    os.makedirs(frames_root, exist_ok=True)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

    sequences: dict = {}
    # --- nine already-extracted sequences -----------------------------------
    for name in sorted(os.listdir(args.nine)):
        src = os.path.join(args.nine, name)
        if not os.path.isdir(src):
            continue
        files = sorted(f for f in os.listdir(src) if f.lower().endswith(".jpg"))
        records = []
        dst = os.path.join(frames_root, name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(dst)
        for i, f in enumerate(files):
            b = open(os.path.join(src, f), "rb").read()
            assert int(f.split(".")[0]) == i, f"non-contiguous frame index {f}"
            w, h = frame_bytes_ok(b)
            with open(os.path.join(dst, f), "wb") as fh:
                fh.write(b)
            records.append({"index": i, "file": f, "sha256": sha(b), "bytes": len(b)})
        sequences[name] = {
            "member": f"All-In-One-Deflicker-Dataset/VideoDM/Meta/{name}",
            "frame_count": len(records), "width": w, "height": h,
            "frames": records, "split": "dev" if name in DEV else "expansion",
            "real_t2v": name in REAL_T2V,
            "source": "predecessor extraction of the upstream archive (verbatim JPEG bytes)",
        }

    # --- three sequences from the small bundle zip --------------------------
    with zipfile.ZipFile(args.small_zip) as z:
        prov = json.loads(z.read("sample_provenance.json").decode("utf-8"))
        for s in prov["samples"]:
            name = s["sample_id"].replace("videodm_meta_", "")
            prefix = f"input_frames/{s['sample_id']}/"
            members = sorted((n for n in z.namelist() if n.startswith(prefix) and n.endswith(".jpg")),
                             key=lambda n: int(os.path.basename(n).split(".")[0]))
            dst = os.path.join(frames_root, name)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            os.makedirs(dst)
            records = []
            for i, n in enumerate(members):
                b = z.read(n)
                f = os.path.basename(n)
                assert int(f.split(".")[0]) == i
                w, h = frame_bytes_ok(b)
                with open(os.path.join(dst, f), "wb") as fh:
                    fh.write(b)
                records.append({"index": i, "file": f, "sha256": sha(b), "bytes": len(b)})
            assert len(records) == 76, (name, len(records))
            sequences[name] = {
                "member": s["archive_sequence_path"],
                "frame_count": len(records), "width": w, "height": h,
                "frames": records, "split": "dev" if name in DEV else "expansion",
                "real_t2v": name in REAL_T2V,
                "source": "three-sequence bundle zip (verbatim JPEG bytes), source hashes re-verified",
            }

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "archive": ARCHIVE,
        "selection": {
            "dev_sequences": DEV,
            "real_t2v_sequences": REAL_T2V,
            "rule": "dev = the three sequences used by the prior project (book/horse/sailboat); "
                    "expansion = every other 76x512x512 sequence available from the same archive "
                    "without re-encoding; real_t2v = VideoDM/Meta sequences reserved for the "
                    "manual brightness-transition annotation study.",
        },
        "sequences": sequences,
    }
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, manifest_path)

    total = sum(v["frame_count"] for v in sequences.values())
    print(f"sequences={len(sequences)} frames={total}")
    for k, v in sorted(sequences.items()):
        print(f"  {k:12s} {v['frame_count']} {v['width']}x{v['height']} split={v['split']}")


if __name__ == "__main__":
    main()
