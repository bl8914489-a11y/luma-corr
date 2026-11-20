"""Reproducibility plumbing: canonical config hashing, code-tree hashing,
environment capture, atomic JSON writes.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import numpy as np
import PIL


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def config_sha256(cfg) -> str:
    return sha256_text(canonical_json(cfg))


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def code_tree_sha256(paths: list[str]) -> str:
    """Hash of (relative path, file sha256) pairs over the given source trees."""
    items = []
    for root in paths:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for f in sorted(filenames):
                if f.endswith((".py", ".json", ".md")):
                    p = os.path.join(dirpath, f)
                    items.append((os.path.relpath(p, os.path.dirname(root)),
                                  sha256_file(p)))
    items.sort()
    return sha256_text("\n".join(f"{p} {h}" for p, h in items))


def _gpu_info() -> dict:
    info = {"nvidia_smi_available": False, "gpus": [], "torch_available": False,
            "torch_cuda_available": False, "torch_version": None}
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and r.stdout.strip():
            info["nvidia_smi_available"] = True
            for line in r.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                info["gpus"].append({"name": parts[0], "memory_total_mib": parts[1],
                                     "driver": parts[2], "compute_cap": parts[3] if len(parts) > 3 else None})
    except Exception as exc:  # noqa: BLE001 - environment probe must never break a run
        info["nvidia_smi_error"] = str(exc)
    try:
        import torch  # type: ignore
        info["torch_available"] = True
        info["torch_version"] = torch.__version__
        info["torch_cuda_available"] = bool(torch.cuda.is_available())
        info["torch_cuda_version"] = getattr(torch.version, "cuda", None)
    except Exception:  # noqa: BLE001
        pass
    return info


def env_info() -> dict:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "pillow": PIL.__version__,
        "cpu_count": os.cpu_count(),
        "gpu": _gpu_info(),
        "utc": datetime.now(timezone.utc).isoformat(),
    }


def write_json_atomic(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
