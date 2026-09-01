"""Seal the repo as a *layered* self-record. Run from the repo root:

    python scripts/selfrecord.py

Two records, bottom-up:

  kernel-core   .reticuli/liquid/kernel-core/   free: reticuli/{__init__,kernel}.py
                                                 seed: kernel_check.py  gate -> KERNEL_OK
  reticuli      .  (repo root)                   free: the rest of reticuli/*.py
                                                 from kernel-core: reticuli/{__init__,kernel}.py
                                                 seed: whole_check.py   gate -> VERIFIED

Then `ret verify .` holds and `ret realize . --recursive` rehydrates kernel-core
first, threads its kernel up, regrows the toolchain over it, and lands on the
same whole root. Deterministic — re-running reproduces both roots (a lockfile).
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, pack

KERNEL_FILES = ["reticuli/__init__.py", "reticuli/kernel.py"]
CORE_DIR = os.path.join(ROOT, kernel.STORE, "liquid", "kernel-core")


def build_kernel_core() -> str:
    if os.path.exists(CORE_DIR):
        shutil.rmtree(CORE_DIR)
    os.makedirs(os.path.join(CORE_DIR, "reticuli"))
    for f in KERNEL_FILES:
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(CORE_DIR, f))
    shutil.copyfile(os.path.join(ROOT, "kernel_check.py"),
                    os.path.join(CORE_DIR, "kernel_check.py"))
    r = pack.pack(CORE_DIR, "kernel-core", ["reticuli/*.py"], ["kernel_check.py"],
                  "python3 kernel_check.py", "KERNEL_OK")
    return r["root"]


def build_whole() -> str:
    r = pack.pack(ROOT, "reticuli", ["reticuli/*.py"], ["whole_check.py"],
                  "python3 whole_check.py", "VERIFIED",
                  component={"name": "kernel-core", "record": CORE_DIR, "outputs": KERNEL_FILES})
    return r["root"]


if __name__ == "__main__":
    core = build_kernel_core()
    whole = build_whole()
    print(f"kernel-core  {core}")
    print(f"reticuli     {whole}")
    assert kernel.verify(ROOT)["ok"], "the whole record must verify fresh"
    assert kernel.verify(CORE_DIR)["ok"], "kernel-core must verify fresh"
    print("verify: both fresh")
