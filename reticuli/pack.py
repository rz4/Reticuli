"""Pack a project into a self-record.

Declare a project's code as produce outputs (free — the implementation), its
check harness as dry seeds, and a gate that runs the check. Sealing makes the
project a Reticuli record: `ret realize .` regrows a fresh implementation, runs
the gate, and — because the code is free and the root is the claim — lands on the
*same root*. A project that passes its own check is a point in its own basin.
"""
from __future__ import annotations

import glob
import os
import subprocess

from . import kernel, render


def _match(root: str, patterns: list[str]) -> list[str]:
    files: list[str] = []
    for pat in patterns:
        for f in sorted(glob.glob(pat, root_dir=root, recursive=True)):
            if os.path.isfile(os.path.join(root, f)) and f not in files:
                files.append(f)
    return files


def pack(root: str, name: str, produce: list[str], seeds: list[str],
         gate: str, gate_output: str) -> dict:
    root = os.path.abspath(root)
    seed_files = _match(root, seeds)
    produce_files = [f for f in _match(root, produce) if f not in seed_files]
    if not produce_files:
        raise kernel.ReticuliError("pack: no produce files matched")

    recipe = {
        "record": {"name": name, "inputs": seed_files},
        "step": [{"kind": "produce", "output": f, "request": f"regenerate {f} to pass the gate",
                  "class": "free"} for f in produce_files]
                + [{"kind": "gate", "output": gate_output, "run": gate, "class": "validated"}],
    }
    with open(os.path.join(root, kernel.RECIPE), "w", encoding="utf-8") as f:
        f.write(render.dump_recipe(recipe))

    r = subprocess.run(gate, shell=True, cwd=root, check=False,
                       env={**os.environ, "RETICULI": "1"})
    if r.returncode != 0 or not os.path.isfile(os.path.join(root, gate_output)):
        raise kernel.ReticuliError(f"pack: the gate did not pass warm ({gate})")

    manifest = kernel.seal(root)
    return {"ok": True, "name": name, "root": manifest["root"],
            "produce": len(produce_files), "seeds": len(seed_files)}
