"""Portability: pack a record into a deterministic tar, and unpack it back.

The tar is byte-deterministic (mtime 0, uid/gid 0, sorted) so the same record
exports to the same bytes. Import unpacks into a fresh directory and verifies —
the record travels by content and re-derives its own root, exactly like a
git-cloned record.
"""
from __future__ import annotations

import os
import tarfile

from . import kernel


def export(d: str, tar_path: str) -> dict:
    """Deterministic tar of a record directory. Volatile history (the trace,
    the cost ledger) stays home — identity travels, events don't."""
    d = os.path.abspath(d)
    if kernel.phase(d) == "vapor":
        raise kernel.ReticuliError(f"no record in {d} (seal or condense first)")
    members = []
    for root_dir, dirs, files in os.walk(d):
        dirs.sort()
        for f in sorted(files):
            full = os.path.join(root_dir, f)
            rel = os.path.relpath(full, d).replace(os.sep, "/")
            if f in ("vapor.jsonl", "ledger.jsonl") and kernel.STORE in rel.split("/"):
                continue
            members.append((rel, full))
    members.sort()
    with tarfile.open(tar_path, "w") as tar:
        for rel, full in members:
            info = tarfile.TarInfo(rel)
            info.size = os.path.getsize(full)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o644
            with open(full, "rb") as fh:
                tar.addfile(info, fh)
    return {"ok": True, "tar": tar_path, "members": len(members)}


def import_(tar_path: str, into: str) -> dict:
    """Unpack a record into a fresh directory and verify it."""
    into = os.path.abspath(into)
    if os.path.exists(into):
        raise kernel.ReticuliError(f"import: target exists: {into}")
    os.makedirs(into)
    with tarfile.open(tar_path, "r") as tar:
        for m in tar:
            name = m.name.replace("\\", "/")
            parts = name.split("/")
            if not m.isfile() or name.startswith("/") or ".." in parts:
                raise kernel.ReticuliError(f"import: unsafe member: {name}")
            src = tar.extractfile(m)
            if src is None:
                continue
            dst = os.path.join(into, *parts)
            os.makedirs(os.path.dirname(dst) or into, exist_ok=True)
            with open(dst, "wb") as f:
                f.write(src.read())
    v = kernel.verify(into)
    return {"ok": v["ok"], "into": into, "root": v["root"],
            "verdict": "fresh" if v["ok"] else "broken"}
