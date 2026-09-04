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
import sys
import tempfile
import time
import tomllib

STORE = ".reticuli"
RECIPE = "reticuli.toml"
LEDGER = os.path.join(STORE, "ledger.jsonl")
TOLERANCE = 2.0                 # comparable cost: 1/2 <= C3/C1 <= 2, unless the claim declares


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
            produce_from: dict | None = None, exist_ok: bool = False) -> dict:
    """Seed a clean room from the record's dry inputs, run each produce step
    with a fresh producer and each gate cold, then seal. A faithful redo lands
    on the same root.

    seed_from maps a seed path to a *freshly rehydrated* source (from a
    recursively-rehydrated component) instead of the carried bytes — this is how
    DAG-aware rehydrate threads a dependency's output up to its dependent.
    produce_from does the same for a *free* produce step whose `from` is a
    component: the bytes are supplied by the rehydrated component instead of the
    producer, so the output stays free (never pinned) yet layered. exist_ok
    tolerates a target already holding rehydrated deps (under .reticuli/deps).

    Every oracle call and gate is accounted to the target's ledger — cost is
    residue of the event, never part of the claim.
    """
    seed_from = seed_from or {}
    produce_from = produce_from or {}
    recipe = load_recipe(d)
    if os.path.exists(os.path.join(into, RECIPE)) or (os.path.exists(into) and not exist_ok):
        raise ReticuliError(f"target exists: {into}")
    os.makedirs(into, exist_ok=True)
    shutil.copyfile(os.path.join(d, RECIPE), os.path.join(into, RECIPE))
    for seed in _seeds(recipe):
        _copy(seed_from.get(seed) or os.path.join(d, seed), os.path.join(into, seed))
    # component-supplied free code goes in first, so a producer can build on it
    for step in recipe.get("step", []):
        if step["kind"] == "produce" and _out(step) in produce_from:
            _copy(produce_from[_out(step)], os.path.join(into, _out(step)))
    usage_path = os.path.join(into, STORE, "usage.json")
    os.makedirs(os.path.join(into, STORE), exist_ok=True)
    for step in recipe.get("step", []):
        out = _out(step)
        if step["kind"] == "produce" and out in produce_from:
            _ledger_add(into, {"event": "reuse", "output": out})
            continue
        env = {**os.environ, "RETICULI_REQUEST": step.get("request", ""),
               "RETICULI_OUTPUT": out, "RETICULI": "1"}
        t0 = time.monotonic()
        if step["kind"] == "gate":
            r, jailed_as = _jailed(step["run"], into, env)
        else:
            env["RETICULI_USAGE"] = usage_path
            r = subprocess.run(producer, shell=True, cwd=into, env=env,
                               capture_output=True, text=True, check=False)
        if r.returncode != 0 or not os.path.isfile(os.path.join(into, out)):
            raise ReticuliError(
                f"redo failed at {out}: {(r.stderr or r.stdout).strip()[:200]}")
        entry = {"event": "gate" if step["kind"] == "gate" else "oracle",
                 "output": out, "seconds": round(time.monotonic() - t0, 3)}
        if step["kind"] == "gate":
            entry["quarantine"] = jailed_as
        else:
            entry.update({"calls": 1, **_usage(usage_path)})
        _ledger_add(into, entry)
    return {**seal(into), "into": into, "cost": cost(into)}


# -- quarantine: a record's gates are not your shell -------------------------

_PROFILE = """(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "{room}") (subpath "/dev"))
"""

_BWRAP: bool | None = None


def _bwrap_ok() -> bool:
    global _BWRAP                      # probed once — a present-but-broken bwrap is "none"
    if _BWRAP is None:
        _BWRAP = bool(shutil.which("bwrap")) and subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--unshare-net", "true"],
            capture_output=True, check=False).returncode == 0
    return _BWRAP


def jail(cmd: str, room: str) -> tuple[list[str] | str, str]:
    """Wrap a gate command in the platform's jail: writes confined to the room,
    network denied. Producers are never jailed — you chose that command; a
    pulled record's gates you did not. RETICULI_QUARANTINE: auto (default) uses
    a jail when the platform has one, require refuses to run without one, off
    opts out. Whichever happened, the ledger records it."""
    mode = os.environ.get("RETICULI_QUARANTINE", "auto")
    if mode == "off":
        return cmd, "off"
    if os.environ.get("RETICULI_JAILED"):    # jails don't nest; the outer one holds
        return cmd, "inherited"
    room = os.path.realpath(room)
    if sys.platform == "darwin":
        profile = _PROFILE.format(room=room.replace('"', '\\"'))
        return ["sandbox-exec", "-p", profile, "/bin/sh", "-c", cmd], "seatbelt"
    if _bwrap_ok():
        return ["bwrap", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev",
                "--proc", "/proc", "--bind", room, room, "--unshare-net",
                "--die-with-parent", "/bin/sh", "-c", cmd], "bubblewrap"
    if mode == "require":
        raise ReticuliError("quarantine required, but no jail here (sandbox-exec or bwrap)")
    return cmd, "none"


def _jailed(cmd: str, room: str, env: dict) -> tuple[subprocess.CompletedProcess, str]:
    """Run a gate in the jail. TMPDIR moves inside the room so well-behaved
    temp use stays confined; the jail refuses the rest."""
    wrapped, status = jail(cmd, room)
    if isinstance(wrapped, list):
        tmp = os.path.join(os.path.realpath(room), STORE, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env = {**env, "TMPDIR": tmp, "RETICULI_JAILED": status}
    return subprocess.run(wrapped, shell=isinstance(wrapped, str), cwd=room, env=env,
                          capture_output=True, text=True, check=False), status


# -- the cost ledger: residue of the event, never part of the claim ----------


def _ledger_add(d: str, entry: dict) -> None:
    os.makedirs(os.path.join(d, STORE), exist_ok=True)
    with open(os.path.join(d, LEDGER), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def _usage(path: str) -> dict:
    """Optional oracle-reported usage ({tokens, usd}), consumed once per call."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            u = json.load(f)
    except (json.JSONDecodeError, OSError):
        u = {}
    os.remove(path)
    u = u if isinstance(u, dict) else {}
    return {k: u[k] for k in ("tokens", "usd") if isinstance(u.get(k), (int, float))}


def cost(d: str) -> dict | None:
    """Total the machine's ledger — the paid cost of its realization event:
    oracle calls, wall seconds, and tokens/usd where a producer reported them.
    None if nothing was measured. The root never sees any of this."""
    path = os.path.join(d, LEDGER)
    if not os.path.isfile(path):
        return None
    totals = {"calls": 0, "seconds": 0.0, "tokens": 0, "usd": 0.0}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            for k in totals:
                if isinstance(e.get(k), (int, float)):
                    totals[k] += e[k]
    totals["seconds"] = round(totals["seconds"], 3)
    totals["usd"] = round(totals["usd"], 6)
    return {k: v for k, v in totals.items() if v} or {"calls": 0}


def _comparable(c1: dict | None, c3: dict | None, tol: float) -> dict:
    """C3/C1 in the strongest unit both machines measured (usd > tokens > calls
    > seconds), within [1/tol, tol]. An unmeasured machine is reported, not
    failed: comparable is None and does not gate the test."""
    if not c1 or not c3:
        missing = " and ".join(m for m, c in (("M1", c1), ("M3", c3)) if not c)
        return {"tolerance": tol, "comparable": None,
                "note": f"unmeasured: no ledger on {missing}"}
    unit = next((u for u in ("usd", "tokens", "calls", "seconds")
                 if c1.get(u) and c3.get(u)), None)
    if unit is None:
        return {"tolerance": tol, "comparable": None, "note": "no shared measured unit"}
    ratio = round(c3[unit] / c1[unit], 3)
    return {"unit": unit, "c1": c1[unit], "c3": c3[unit], "ratio": ratio,
            "tolerance": tol, "comparable": (1.0 / tol) <= ratio <= tol}


# -- audit: the verdicts must reproduce, not merely be carried ---------------


def audit(d: str) -> dict:
    """The deep check. verify() proves *identity* — the root holds over the
    bytes present. audit() proves the verdicts are *earned by* those bytes: it
    rebuilds a scratch room from the record's recipe, seeds, and produce
    outputs (no verdicts carried in), re-runs every gate jailed, and requires
    each pinned output to reproduce the record's bytes exactly. A verdict that
    was copied rather than produced does not survive it."""
    v = verify(d)
    recipe = load_recipe(d)
    steps = recipe.get("step", [])
    room = tempfile.mkdtemp(prefix="reticuli-audit-")
    gates, ok = [], v["ok"]
    try:
        shutil.copyfile(os.path.join(d, RECIPE), os.path.join(room, RECIPE))
        for seed in _seeds(recipe):
            _copy(os.path.join(d, seed), os.path.join(room, seed))
        for step in steps:
            if step["kind"] == "produce" and os.path.isfile(os.path.join(d, _out(step))):
                _copy(os.path.join(d, _out(step)), os.path.join(room, _out(step)))
        for step in steps:
            if step["kind"] != "gate":
                continue
            out = _out(step)
            r, jailed_as = _jailed(step["run"], room, {**os.environ, "RETICULI": "1"})
            produced = os.path.join(room, out)
            reproduced = (r.returncode == 0 and os.path.isfile(produced)
                          and os.path.isfile(os.path.join(d, out))
                          and _hf(produced) == _hf(os.path.join(d, out)))
            gates.append({"output": out, "ok": reproduced, "quarantine": jailed_as})
            ok = ok and reproduced
    finally:
        shutil.rmtree(room, ignore_errors=True)
    return {"name": v["name"], "root": v["root"], "fresh": v["ok"],
            "gates": gates, "ok": ok}


# -- three_machine: THE INVARIANT -------------------------------------------


def three_machine(m1: str, m2: str, m3: str) -> dict:
    """M1 a claim, M2 a byte-reuse, M3 an independent redo. Valid iff all three
    share a root — the redo reproduced the claim, the reuse proves the record is
    self-contained — AND every machine's gates re-run clean against its own
    bytes (audit: a carried verdict does not survive), and, where both machines
    kept a ledger, the redo's cost is comparable within the claim's declared
    tolerance. Root equality alone is identity; audit makes it evidence."""
    roots = {name: verify(m)["root"] for name, m in (("M1", m1), ("M2", m2), ("M3", m3))}
    audited = {name: audit(m)["ok"] for name, m in (("M1", m1), ("M2", m2), ("M3", m3))}
    integrity = all(verify(m)["ok"] for m in (m1, m2, m3))
    reuse = _outputs(m2) == _outputs(m1)          # M2 carries M1's outputs, byte-for-byte
    equivalence = roots["M3"] == roots["M1"]       # M3 redid it to the same claim
    tol = float(load_recipe(m1).get("record", {}).get("tolerance", TOLERANCE))
    cost_ = _comparable(cost(m1), cost(m3), tol)
    return {"roots": roots, "integrity": integrity, "reuse": reuse,
            "equivalence": equivalence, "audited": audited, "cost": cost_,
            "satisfied": integrity and reuse and equivalence
            and all(audited.values()) and cost_["comparable"] is not False}


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


# -- the mint: solid identity, bottom-anchored -------------------------------


def realization_digest(d: str) -> str:
    """The chosen crystal: a hash of this record's OWN free bytes — every free
    produce output not supplied by a component (`from`). The root ignores these
    (that freedom is the basin); the mint freezes them. `from` outputs belong to
    the component and are covered by folding the component's mint, so they are
    excluded here to avoid double-counting."""
    recipe = load_recipe(d)
    own = [[_out(s), _hf(os.path.join(d, _out(s)))]
           for s in recipe.get("step", [])
           if s["kind"] == "produce" and "from" not in s and s.get("class") == "free"
           and os.path.isfile(os.path.join(d, _out(s)))]
    return _h(json.dumps(sorted(own), sort_keys=True).encode())


def mint_node(root: str, digest: str, component_mints: list[str]) -> str:
    """THE FOLD. A rung's mint binds its claim root, its realization digest (the
    frozen bytes the root ignores), and the mints of everything beneath it. The
    kernel's mint is the genesis — the most significant digit — and a disturbance
    at any height moves that rung's mint and every mint above it, never one below:
    the lowest mint that moved names the floor the change entered on. Liquid
    records leave this uncomputed; minting is where bytes freeze."""
    return _h(json.dumps([root, digest, sorted(component_mints)], sort_keys=True).encode())


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
