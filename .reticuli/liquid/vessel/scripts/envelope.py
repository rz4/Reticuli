"""The provenance cost envelope: rehydrate the layered self-record with a live
producer and record what every rung paid. One JSONL row per layer per run,
appended to docs/envelope.jsonl — the paper's data.

    python3 scripts/envelope.py "python3 scripts/producer_claude.py" sonnet-5
    RETICULI_MODEL=claude-opus-4-8 python3 scripts/envelope.py \\
        "python3 scripts/producer_claude.py" opus-4.8
    RETICULI_MODEL=gpt-5.1 python3 scripts/envelope.py \\
        "python3 scripts/producer_openai.py" gpt-5.1

Rooms are built under runs/<label>-<n>/ (gitignored); the envelope rows are
committed. A row's `ok` is the three-machine equivalence in miniature: did this
rung land on the committed root?
"""
import datetime
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from reticuli import kernel, registry, render

DATA = os.path.join(ROOT, "docs", "envelope.jsonl")


def committed_roots() -> dict:
    roots = {kernel.read_manifest(ROOT)["name"]: kernel.read_manifest(ROOT)["root"]}
    for r in registry.records(ROOT):
        roots[r["name"]] = r["root"]
    return roots


def rungs(d: str) -> list[str]:
    """The realized chain, outermost first, by walking nested deps."""
    found = [d]
    deps = os.path.join(d, kernel.STORE, "deps")
    if os.path.isdir(deps):
        for name in sorted(os.listdir(deps)):
            found += rungs(os.path.join(deps, name))
    return found


def main(producer: str, label: str) -> int:
    n = 1
    while os.path.exists(os.path.join(ROOT, "runs", f"{label}-{n}")):
        n += 1
    into = os.path.join(ROOT, "runs", f"{label}-{n}")
    run = f"{label}-{n}"
    print(f"# envelope {run}: rehydrating the chain with `{producer}`")
    t0 = time.monotonic()
    registry.rehydrate(ROOT, producer, into, ws=ROOT)
    wall = round(time.monotonic() - t0, 1)

    truth = committed_roots()
    when = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    rows = []
    for d in rungs(into):
        m = kernel.read_manifest(d)
        cost = kernel.cost(d) or {}
        rows.append({"run": run, "when": when, "producer": label, "layer": m["name"],
                     "calls": cost.get("calls", 0), "tokens": cost.get("tokens"),
                     "usd": cost.get("usd"), "seconds": cost.get("seconds"),
                     "root": m["root"], "ok": truth.get(m["name"]) == m["root"]})
    with open(DATA, "a", encoding="utf-8") as f:
        f.writelines(json.dumps(row, sort_keys=True) + "\n" for row in rows)

    render.table([{**r, "root": render.short(r["root"])} for r in rows],
                 ("layer", "layer"), ("calls", "calls"), ("tokens", "tokens"),
                 ("usd", "usd"), ("seconds", "seconds"), ("ok", "ok"))
    total_usd = sum(r["usd"] or 0 for r in rows)
    total_tok = sum(r["tokens"] or 0 for r in rows)
    print(f"# {run}: {total_tok:,} tokens · ${total_usd:.2f} · {wall}s wall · -> {DATA}")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
