"""The kernel: the whole invariant, and nothing else.

A claim is valid iff an independent *redo* satisfies the same check as the
original. Everything composes toward `three_machine`.

The one idea that keeps it small — **the root is the claim.** A record's identity
is `hash(recipe + dry seeds + pinned verdicts)`, and it *excludes* the free
outputs (the implementation). So two valid realizations of one claim share a
root, and the three-machine test collapses to root equality. The basin of
attraction is exactly the preimage of the root.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tomllib

STORE = ".reticuli"
RECIPE = "reticuli.toml"


class ReticuliError(Exception):
    """A refusal with a reason — the only kind of error the kernel raises."""


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _hf(path: str) -> str:
    with open(path, "rb") as f:
        return _h(f.read())


def _out(step: dict) -> str:
    return step["output"]


def _seeds(recipe: dict) -> list[str]:
    """Dry seeds live under [record] (they are part of the record's identity)."""
    return recipe.get("record", {}).get("inputs", [])


def load_recipe(d: str) -> dict:
    with open(os.path.join(d, RECIPE), "rb") as f:
        return tomllib.load(f)


# -- the claim: recipe + dry seeds + pinned verdicts (free outputs excluded) --


def claim(recipe: dict, d: str) -> str:
    """The root. Two realizations that pass the same checks hash to the same
    value; the free implementation never enters it."""
    parts: dict[str, str] = {"recipe": json.dumps(recipe, sort_keys=True)}
    for seed in _seeds(recipe):
        parts[f"seed:{seed}"] = _hf(os.path.join(d, seed))
    for step in recipe.get("step", []):
        if step.get("class", "exact") != "free":          # a pinned verdict
            parts[f"pin:{_out(step)}"] = _hf(os.path.join(d, _out(step)))
    return _h(json.dumps(parts, sort_keys=True).encode())


def phase(d: str) -> str:
    """vapor (no record) · liquid (sealed) · solid (freeze-dried, proven)."""
    m = os.path.join(d, STORE, "manifest.json")
    if not os.path.isfile(m):
        return "vapor"
    return "solid" if _read(m).get("proof") else "liquid"


# -- seal / verify: identity ------------------------------------------------


def seal(d: str, proof: dict | None = None, components: list | None = None) -> dict:
    """Freeze the realization in `d` into a record: compute the root, write the
    manifest. Deterministic — commits like a lockfile."""
    recipe = load_recipe(d)
    # The manifest is pure identity: name + root (+ proof, + component links).
    # It carries no free-output hashes, so editing the implementation (free)
    # never churns it — a self-hosted record stays byte-stable and git-clean.
    manifest = {"name": recipe["record"]["name"], "root": claim(recipe, d)}
    if proof:
        manifest["proof"] = proof
    if components:
        manifest["components"] = components
    os.makedirs(os.path.join(d, STORE), exist_ok=True)
    _write(os.path.join(d, STORE, "manifest.json"), manifest)
    return manifest


def read_manifest(d: str) -> dict:
    return _read(os.path.join(d, STORE, "manifest.json"))


def verify(d: str) -> dict:
    """Recompute the root from the bytes on disk; it must equal the sealed root.
    Needs no ledger — a git-cloned record verifies from its committed identity.
    """
    if phase(d) == "vapor":
        raise ReticuliError(f"no record in {d} (seal first)")
    recipe = load_recipe(d)
    manifest = _read(os.path.join(d, STORE, "manifest.json"))
    got = claim(recipe, d)
    return {"name": manifest["name"], "root": manifest["root"],
            "recomputed": got, "ok": got == manifest["root"],
            "phase": phase(d)}


# -- realize: an independent redo (M3) --------------------------------------


def realize(d: str, producer: str, into: str, seed_from: dict | None = None,
            exist_ok: bool = False) -> dict:
    """Seed a clean room from the record's dry inputs, run each produce step
    with a fresh producer and each gate cold, then seal. A faithful redo lands
    on the same root.

    seed_from maps a seed path to a *freshly rehydrated* source (from a
    recursively-rehydrated component) instead of the carried bytes — this is how
    DAG-aware rehydrate threads a dependency's output up to its dependent.
    exist_ok tolerates a target already holding rehydrated deps (under
    .reticuli/deps) but no record of its own.
    """
    seed_from = seed_from or {}
    recipe = load_recipe(d)
    if os.path.exists(os.path.join(into, RECIPE)) or (os.path.exists(into) and not exist_ok):
        raise ReticuliError(f"target exists: {into}")
    os.makedirs(into, exist_ok=True)
    shutil.copyfile(os.path.join(d, RECIPE), os.path.join(into, RECIPE))
    for seed in _seeds(recipe):
        _copy(seed_from.get(seed) or os.path.join(d, seed), os.path.join(into, seed))
    for step in recipe.get("step", []):
        cmd = step["run"] if step["kind"] == "gate" else producer
        env = {**os.environ, "RETICULI_REQUEST": step.get("request", ""),
               "RETICULI_OUTPUT": _out(step), "RETICULI": "1"}
        r = subprocess.run(cmd, shell=True, cwd=into, env=env,
                           capture_output=True, text=True, check=False)
        made = os.path.isfile(os.path.join(into, _out(step)))
        if r.returncode != 0 or not made:
            raise ReticuliError(
                f"redo failed at {_out(step)}: {(r.stderr or r.stdout).strip()[:200]}")
    return {**seal(into), "into": into}


# -- three_machine: THE INVARIANT -------------------------------------------


def three_machine(m1: str, m2: str, m3: str) -> dict:
    """M1 a claim, M2 a byte-reuse, M3 an independent redo. Valid iff all three
    share a root: the redo reproduced the claim, the reuse proves the record is
    self-contained."""
    roots = {name: verify(m)["root"] for name, m in (("M1", m1), ("M2", m2), ("M3", m3))}
    integrity = all(verify(m)["ok"] for m in (m1, m2, m3))
    reuse = _outputs(m2) == _outputs(m1)          # M2 is a byte-copy of M1
    equivalence = roots["M3"] == roots["M1"]       # M3 redid it to the same claim
    return {"roots": roots, "integrity": integrity, "reuse": reuse,
            "equivalence": equivalence,
            "satisfied": integrity and reuse and equivalence}


def freeze_dry(m1: str, m2: str, m3: str) -> dict:
    """Prove, then promote: on a passing three-machine test, stamp M1 solid."""
    result = three_machine(m1, m2, m3)
    result["minted"] = False
    if result["satisfied"]:
        seal(m1, proof={"kind": "three-machine",
                        "m2": result["roots"]["M2"], "m3": result["roots"]["M3"]})
        result["minted"] = True
    return result


def _outputs(d: str) -> dict:
    recipe = load_recipe(d)
    return {_out(s): _hf(os.path.join(d, _out(s))) for s in recipe.get("step", [])}


# -- small io helpers -------------------------------------------------------


def _read(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def _copy(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    shutil.copyfile(src, dst)
