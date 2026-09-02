"""Seal the repo as a *layered* self-record. Run from the repo root:

    python scripts/selfrecord.py

Four rungs, inner to outer, ordered by interface volatility — each record
carries everything below it and layers its own stratum on top as free code
supplied `from` its predecessor:

  kernel-core   reticuli/{__init__,kernel}.py            the invariant
  exchange      + reticuli/{registry,transfer,attest}.py  records meet records, and other parties
  authoring     + reticuli/{render,condense,feedback,pack}.py   sessions -> records
  agents        + reticuli/hooks.py                      the agent handshake
  reticuli      + reticuli/{cli,__main__}.py  (repo root) the human handshake

Each rung is gated by its own check (kernel_check, exchange_check,
authoring_check, whole_check) — the checks are the claims. `ret verify .` holds,
`ret realize . --recursive` rehydrates the chain leaf-first, each rung paying
its own ledger — the per-layer cost envelope. Deterministic — re-running
reproduces every root (a lockfile).
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, pack

KERNEL_FILES = ["reticuli/__init__.py", "reticuli/kernel.py"]

# (name, own stratum, check, verdict) — cumulative, inner to outer
RUNGS = [
    ("exchange", ["reticuli/registry.py", "reticuli/transfer.py", "reticuli/attest.py"],
     "exchange_check.py", "EXCHANGE_OK"),
    ("authoring", ["reticuli/render.py", "reticuli/condense.py",
                   "reticuli/feedback.py", "reticuli/pack.py"],
     "authoring_check.py", "AUTHORING_OK"),
    ("agents", ["reticuli/hooks.py"], "agents_check.py", "AGENTS_OK"),
]


def _drawer(name: str) -> str:
    return os.path.join(ROOT, kernel.STORE, "liquid", name)


def _build(name: str, files: list[str], check: str, verdict: str,
           component: dict | None) -> str:
    d = _drawer(name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(os.path.join(d, "reticuli"))
    for f in files:
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(d, f))
    shutil.copyfile(os.path.join(ROOT, check), os.path.join(d, check))
    r = pack.pack(d, name, ["reticuli/*.py"], [check],
                  f"python3 {check}", verdict, component=component)
    return r["root"]


if __name__ == "__main__":
    roots = {"kernel-core": _build("kernel-core", KERNEL_FILES,
                                   "kernel_check.py", "KERNEL_OK", None)}
    prev, supplied = "kernel-core", list(KERNEL_FILES)
    for name, own, check, verdict in RUNGS:
        component = {"name": prev, "record": _drawer(prev), "outputs": list(supplied)}
        supplied += own
        roots[name] = _build(name, supplied, check, verdict, component)
        prev = name
    whole = pack.pack(ROOT, "reticuli", ["reticuli/*.py"], ["whole_check.py"],
                      "python3 whole_check.py", "VERIFIED",
                      component={"name": prev, "record": _drawer(prev),
                                 "outputs": list(supplied)})
    roots["reticuli"] = whole["root"]
    for name, root in roots.items():
        print(f"{name:<12} {root}")
    for name in roots:
        d = ROOT if name == "reticuli" else _drawer(name)
        assert kernel.verify(d)["ok"], f"{name} must verify fresh"
    print(f"verify: all {len(roots)} rungs fresh")
