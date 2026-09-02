"""The per-layer reflection profile: a Smith-chart reading of each rung.

Where envelope.py rehydrates the whole chain (and hard-fails at the first
reflection), this isolates each rung: it supplies the *committed* lower layers
and asks one producer to regrow only that rung's own stratum. So every layer is
measured against a correct foundation — a clean per-layer reading of whether the
load lands at center (Γ=0, root exact) or reflects, and what it cost either way.

Honesty: every row records `claim_root`, the committed root of the layer *at
measurement time*, so data can never be silently mixed across a re-mint. A cell
counts as landed only when the redo hits that root AND `audit` passes (the
verdicts are re-earned from the produced bytes, not carried). Set
RETICULI_ARCHIVE=<dir> to export each landed specimen (the actual regrown code)
as a deterministic tar under <dir>/<label>/<layer>.tar; RETICULI_PROFILE
overrides the output jsonl.

    python3 scripts/probe.py "<producer>" <label> [layer]
"""
import datetime
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, render, transfer

DATA = os.environ.get("RETICULI_PROFILE", os.path.join(ROOT, "docs", "reflection_profile.jsonl"))
ARCHIVE = os.environ.get("RETICULI_ARCHIVE")

# signatures of a producer/API failure (the model never landed a real attempt) —
# distinct from a genuine gate bounce, and never counted as a measurement
_PRODUCER_FAIL = ("producer_claude:", "producer_agentic:", "producer_openai:",
                  "is_error", "claude exited", "session limit", "overloaded", "rate limit")

RUNGS = [
    ("kernel-core", os.path.join(ROOT, kernel.STORE, "liquid", "kernel-core")),
    ("exchange", os.path.join(ROOT, kernel.STORE, "liquid", "exchange")),
    ("authoring", os.path.join(ROOT, kernel.STORE, "liquid", "authoring")),
    ("agents", os.path.join(ROOT, kernel.STORE, "liquid", "agents")),
    ("surface", os.path.join(ROOT, kernel.STORE, "liquid", "surface")),
    ("workshop", os.path.join(ROOT, kernel.STORE, "liquid", "workshop")),
    ("vessel", os.path.join(ROOT, kernel.STORE, "liquid", "vessel")),
    ("reticuli", ROOT),
]


def probe(name: str, d: str, producer: str, label: str) -> dict:
    recipe = kernel.load_recipe(d)
    committed = kernel.read_manifest(d)["root"]           # the claim, at this instant
    produce_from, own = {}, []
    for step in recipe.get("step", []):
        if step["kind"] != "produce":
            continue
        if "from" in step:                                # supplied committed lower layer
            produce_from[step["output"]] = os.path.join(d, step["output"])
        else:
            own.append(step["output"])                    # this rung's stratum, to regrow
    room = os.path.join(ROOT, "runs", f"probe-{label}-{os.getpid()}-{name}")
    if os.path.exists(room):
        shutil.rmtree(room)
    landed, reflection, audited, producer_error = False, None, None, False
    try:
        res = kernel.realize(d, producer, room, produce_from=produce_from)
        root_match = res["root"] == committed
        audited = kernel.audit(room)["ok"]                # verdicts re-earned, jailed
        landed = root_match and audited
        if root_match and not audited:
            reflection = "root matched but verdicts not re-earned (audit)"
        elif not root_match:
            reflection = "root mismatch (gate passed, wrong claim)"
    except kernel.ReticuliError as e:
        msg = str(e)
        # keep the head AND the tail of a traceback — the tail names the assert
        lines = [x for x in msg.splitlines() if x.strip()]
        reflection = (lines[0][:100] + " … " + lines[-1][:160]) if len(lines) > 1 else msg[:200]
        # a producer/API failure is NOT a reflection — the model never got to
        # try. Flag it so it can't count as a landing OR a measurement, and so a
        # resuming sweep re-runs it rather than trusting the failure.
        producer_error = any(s in msg for s in _PRODUCER_FAIL)
    cost = kernel.cost(room) or {}
    if ARCHIVE and os.path.isdir(room):                   # keep the evidence either way:
        dst = os.path.join(ARCHIVE, label)                # a landed specimen, or a
        os.makedirs(dst, exist_ok=True)                   # failed room for diagnosis
        tag = name if landed else f"failed-{name}"
        try:
            transfer.export(room, os.path.join(dst, f"{tag}.tar"))
        except kernel.ReticuliError:
            shutil.make_archive(os.path.join(dst, tag), "tar", room)   # unsealed room
    shutil.rmtree(room, ignore_errors=True)               # room is transient; tar is the evidence
    return {"label": label, "layer": name, "own": own, "claim_root": committed,
            "landed": landed, "audited": audited, "producer_error": producer_error,
            "reflection": reflection, "calls": cost.get("calls", 0),
            "tokens": cost.get("tokens"), "usd": cost.get("usd"), "seconds": cost.get("seconds")}


def main(producer: str, label: str, only: str | None = None) -> int:
    when = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    rungs = [(n, d) for n, d in RUNGS if only in (None, n)]
    if not rungs:
        print(f"no such layer: {only} (choose from {[n for n, _ in RUNGS]})")
        return 2
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    rows = []
    for name, d in rungs:
        print(f"# probing {name} …", flush=True)
        r = probe(name, d, producer, label)
        r["when"] = when
        rows.append(r)
        with open(DATA, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    render.table([{"layer": r["layer"], "regrew": len(r["own"]), "match": r["landed"],
                   "usd": r["usd"], "calls": r["calls"], "reflection": r["reflection"] or "—"}
                  for r in rows],
                 ("layer", "layer"), ("regrew", "regrew"), ("match", "Γ=0"),
                 ("usd", "usd"), ("calls", "calls"), ("reflection", "reflection"))
    landed = [r for r in rows if r["landed"]]
    total = sum(r["usd"] or 0 for r in rows)
    print(f"# {label}: {len(landed)}/{len(rows)} at center · ${total:.3f} · -> {DATA}")
    return 0 if len(landed) == len(rows) else 1


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None))
