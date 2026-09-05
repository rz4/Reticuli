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

from . import kernel, render


def _match(root: str, patterns: list[str]) -> list[str]:
    files: list[str] = []
    for pat in patterns:
        for f in sorted(glob.glob(pat, root_dir=root, recursive=True)):
            if os.path.isfile(os.path.join(root, f)) and f not in files:
                files.append(f)
    return files


def _produce_step(f: str, component: dict | None) -> dict:
    step = {"kind": "produce", "output": f, "request": f"regenerate {f} to pass the gate",
            "class": "free"}
    if component and f in component["outputs"]:
        step["from"] = component["name"]           # supplied by a component, still free
        step["request"] = f"supplied by the {component['name']} component"
    return step


def pack(root: str, name: str, produce: list[str], seeds: list[str],
         gate: str, gate_output: str, component: dict | None = None) -> dict:
    """Seal a project as a self-record. With `component` ({name, record, outputs})
    the listed produce files are declared `from` that component — free code the
    record layers on: `ret realize --recursive` rehydrates the component first
    and threads its output up, so the self-host becomes layered."""
    root = os.path.abspath(root)
    seed_files = _match(root, seeds)
    produce_files = [f for f in _match(root, produce) if f not in seed_files]
    if not produce_files:
        raise kernel.ReticuliError("pack: no produce files matched")

    links = None
    if component:
        missing = [f for f in component["outputs"] if f not in produce_files]
        if missing:
            raise kernel.ReticuliError(f"pack: component outputs not among produce files: {missing}")
        root_c = kernel.read_manifest(component["record"])["root"]
        links = [{"input": f, "component": component["name"], "root": root_c, "output": f}
                 for f in component["outputs"]]

    recipe = {
        "record": {"name": name, "inputs": seed_files},
        "step": [_produce_step(f, component) for f in produce_files]
                + [{"kind": "gate", "output": gate_output, "run": gate, "class": "validated"}],
    }
    with open(os.path.join(root, kernel.RECIPE), "w", encoding="utf-8") as f:
        f.write(render.dump_recipe(recipe))

    r, _ = kernel.run_gate(gate, root, recipe)   # scrubbed + bounded, via the one gate entry point
    if r.stdout:
        print(r.stdout, end="")                       # the gate's own voice
    if r.returncode != 0 or not os.path.isfile(os.path.join(root, gate_output)):
        raise kernel.ReticuliError(
            f"pack: the gate did not pass warm ({gate}): {(r.stderr or '').strip()[:200]}")

    manifest = kernel.seal(root, components=links)
    return {"ok": True, "name": name, "root": manifest["root"],
            "produce": len(produce_files), "seeds": len(seed_files),
            "component": component["name"] if component else None}
