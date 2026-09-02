"""The per-layer reflection profile: a Smith-chart reading of each rung.

Where envelope.py rehydrates the whole chain (and hard-fails at the first
reflection), this isolates each rung: it supplies the *committed* lower layers
and asks one producer to regrow only that rung's own stratum. So every layer is
measured against a correct foundation — a clean per-layer reading of whether the
load lands at center (Γ=0, root exact) or reflects (the gate bounces), and what
it cost either way. The cost ledger is the tuning circuit; this is the meter.

    python3 scripts/probe.py "<producer>" <label>
    RETICULI_MODEL=claude-haiku-4-5-20251001 python3 scripts/probe.py \\
        "python3 $PWD/scripts/producer_claude.py" haiku-4.5
"""
import datetime
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, render

DATA = os.path.join(ROOT, "docs", "reflection_profile.jsonl")

# name -> committed record dir; inner to outer, contact last (repo root)
RUNGS = [
    ("kernel-core", os.path.join(ROOT, kernel.STORE, "liquid", "kernel-core")),
    ("exchange", os.path.join(ROOT, kernel.STORE, "liquid", "exchange")),
    ("authoring", os.path.join(ROOT, kernel.STORE, "liquid", "authoring")),
    ("agents", os.path.join(ROOT, kernel.STORE, "liquid", "agents")),
    ("surface", os.path.join(ROOT, kernel.STORE, "liquid", "surface")),
    ("reticuli", ROOT),
]


def probe(name: str, d: str, producer: str, label: str) -> dict:
    recipe = kernel.load_recipe(d)
    committed = kernel.read_manifest(d)["root"]
    # supply the committed lower layers; the producer regrows only this stratum
    produce_from, own = {}, []
    for step in recipe.get("step", []):
        if step["kind"] != "produce":
            continue
        if "from" in step:
            produce_from[step["output"]] = os.path.join(d, step["output"])
        else:
            own.append(step["output"])
    # per-process tag so two concurrent sweeps never share (and stomp) a room
    room = os.path.join(ROOT, "runs", f"probe-{label}-{os.getpid()}-{name}")
    if os.path.exists(room):
        shutil.rmtree(room)
    landed, reflection = False, None
    try:
        res = kernel.realize(d, producer, room, produce_from=produce_from)
        landed = res["root"] == committed
        if not landed:
            reflection = "root mismatch"          # gate passed but not to the claim
    except kernel.ReticuliError as e:
        reflection = str(e).split(": ", 1)[-1].strip()[:120]   # the bounce
    cost = kernel.cost(room) or {}
    return {"label": label, "layer": name, "own": own, "landed": landed,
            "reflection": reflection, "calls": cost.get("calls", 0),
            "tokens": cost.get("tokens"), "usd": cost.get("usd"),
            "seconds": cost.get("seconds")}


def main(producer: str, label: str) -> int:
    when = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    rows = []
    for name, d in RUNGS:
        print(f"# probing {name} …", flush=True)
        r = probe(name, d, producer, label)
        r["when"] = when
        rows.append(r)
        with open(DATA, "a", encoding="utf-8") as f:   # append per layer: an
            f.write(json.dumps(r, sort_keys=True) + "\n")   # interrupt keeps the rest

    render.table([{"layer": r["layer"], "regrew": len(r["own"]),
                   "match": r["landed"], "usd": r["usd"], "calls": r["calls"],
                   "reflection": r["reflection"] or "—"}
                  for r in rows],
                 ("layer", "layer"), ("regrew", "regrew"), ("match", "Γ=0"),
                 ("usd", "usd"), ("calls", "calls"), ("reflection", "reflection"))
    landed = [r for r in rows if r["landed"]]
    total = sum(r["usd"] or 0 for r in rows)
    print(f"# {label}: {len(landed)}/{len(rows)} layers at center · "
          f"${total:.3f} total · -> {DATA}")
    return 0 if len(landed) == len(rows) else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
