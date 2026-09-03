"""Seal the repo as a *layered* self-record. Run from the repo root:

    python scripts/selfrecord.py

Eight rungs, inner to outer, ordered by interface volatility — each record
carries everything below it and layers its own stratum on top as free code
supplied `from` its predecessor:

  kernel-core   reticuli/{__init__,kernel}.py            the invariant
  exchange      + reticuli/{registry,transfer,attest}.py  records meet records, and other parties
  authoring     + reticuli/{render,condense,feedback,pack}.py   sessions -> records
  agents        + reticuli/hooks.py                      the agent handshake
  surface       + reticuli/{cli,__main__}.py             the human handshake
  workshop      + scripts/*.py + tests/*.py              the bench (free, with teeth)
  vessel        + pyproject, CI, docs, example, git skin  the skin it ships in
                  (seeds: LICENSE + logo.png — the law and the mark, pinned)
  reticuli      + README.md, docs/guide.md  (repo root)    documentation: the hand-off

Each rung is gated by its own check — the checks are the claims. `ret verify .`
holds, `ret realize . --recursive` rehydrates the chain leaf-first, each rung
paying its own ledger — the per-layer cost envelope. Deterministic — re-running
reproduces every root (a lockfile).
"""
import glob
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, pack

KERNEL_FILES = ["reticuli/__init__.py", "reticuli/kernel.py"]


def _g(*patterns: str) -> list[str]:
    out: list[str] = []
    for p in patterns:
        out += sorted(f for f in glob.glob(p, root_dir=ROOT)
                      if os.path.isfile(os.path.join(ROOT, f)) and "__pycache__" not in f)
    return out


VESSEL_FREE = _g("pyproject.toml", ".gitignore", ".gitattributes",
                 ".github/workflows/*.yml")

# (name, own stratum, produce globs, check, verdict, extra seeds)
RUNGS = [
    ("exchange", ["reticuli/registry.py", "reticuli/transfer.py", "reticuli/attest.py"],
     ["reticuli/*.py"], "checks/exchange_check.py", "EXCHANGE_OK", []),
    ("authoring", ["reticuli/render.py", "reticuli/condense.py",
                   "reticuli/feedback.py", "reticuli/pack.py"],
     ["reticuli/*.py"], "checks/authoring_check.py", "AUTHORING_OK", []),
    ("agents", ["reticuli/hooks.py"], ["reticuli/*.py"],
     "checks/agents_check.py", "AGENTS_OK", []),
    ("surface", ["reticuli/cli.py", "reticuli/__main__.py"], ["reticuli/*.py"],
     "checks/surface_check.py", "SURFACE_OK", []),
    ("workshop", _g("scripts/*.py", "tests/*.py"),
     ["reticuli/*.py", "scripts/*.py", "tests/*.py"],
     "checks/workshop_check.py", "WORKSHOP_OK", []),
    ("vessel", VESSEL_FREE,
     ["reticuli/*.py", "scripts/*.py", "tests/*.py", "pyproject.toml",
      ".gitignore", ".gitattributes", ".github/workflows/*.yml"],
     "checks/vessel_check.py", "VESSEL_OK", ["LICENSE", "logo.png"]),
]

WHOLE_GLOBS = ["reticuli/*.py", "scripts/*.py", "tests/*.py", "pyproject.toml",
               ".gitignore", ".gitattributes", ".github/workflows/*.yml",
               "docs/guide.md", "README.md"]


def _drawer(name: str) -> str:
    return os.path.join(ROOT, kernel.STORE, "liquid", name)


def _build(name: str, files: list[str], globs: list[str], check: str,
           verdict: str, component: dict | None, seeds: list[str]) -> str:
    d = _drawer(name)
    if os.path.exists(d):
        shutil.rmtree(d)
    for f in [*files, check, *seeds]:
        dst = os.path.join(d, f)
        os.makedirs(os.path.dirname(dst) or d, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, f), dst)
    r = pack.pack(d, name, globs, [check, *seeds],
                  f"python3 {check}", verdict, component=component)
    return r["root"]


if __name__ == "__main__":
    roots = {"kernel-core": _build("kernel-core", KERNEL_FILES, ["reticuli/*.py"],
                                   "checks/kernel_check.py", "KERNEL_OK", None, [])}
    prev, supplied = "kernel-core", list(KERNEL_FILES)
    for name, own, globs, check, verdict, seeds in RUNGS:
        component = {"name": prev, "record": _drawer(prev), "outputs": list(supplied)}
        supplied += own
        roots[name] = _build(name, supplied, globs, check, verdict, component, seeds)
        prev = name
    whole = pack.pack(ROOT, "reticuli", WHOLE_GLOBS,
                      ["checks/docs_check.py"], "python3 checks/docs_check.py", "VERIFIED",
                      component={"name": prev, "record": _drawer(prev),
                                 "outputs": list(supplied)})
    roots["reticuli"] = whole["root"]
    for name, root in roots.items():
        print(f"{name:<12} {root}")
    for name in roots:
        d = ROOT if name == "reticuli" else _drawer(name)
        assert kernel.verify(d)["ok"], f"{name} must verify fresh"
    print(f"verify: all {len(roots)} rungs fresh")
