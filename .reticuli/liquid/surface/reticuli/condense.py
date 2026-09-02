"""Condense: draft a record from a session's trace, then certify it cold.

The trace has zero authority. Condense drafts a recipe from what the session did,
rebuilds it in a clean room, re-runs the gates cold, and seals only if the pinned
verdicts reproduce. A wrong draft simply fails to certify; no record forms.
"""
from __future__ import annotations

import json
import os
import re
import shutil

from . import kernel, render

TRACE = os.path.join(kernel.STORE, "vapor.jsonl")

# A read/inspect tool consumes its arguments; it never *produces* them. So a gate
# is a command that WRITES its output (a redirect target, or a non-read-only
# program) — never `ls VERIFIED` merely naming it.
_READ_ONLY = frozenset({"ls", "cat", "rm", "head", "tail", "grep", "wc", "stat",
                        "echo", "printf", "find", "diff", "cmp", "file"})
_REDIRECT = re.compile(r'\d*>>?\s*["\']?([^\s"\';|&<>()]+)')


def _writes(cmd: str, out: str) -> bool:
    base = os.path.basename(out)
    if any(os.path.basename(m.group(1)) == base for m in _REDIRECT.finditer(cmd)):
        return True
    prog = next((os.path.basename(t) for t in cmd.split() if "=" not in t or not t.split("=")[0].isidentifier()), "")
    return base in cmd and prog not in _READ_ONLY


def _events(session: str) -> list[dict]:
    path = os.path.join(session, TRACE)
    out: list[dict] = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return out


def draft(session: str, accepted: list[str], name: str) -> dict:
    """Draft a recipe in trace order: produce steps for model-written files
    (free), a gate for each accepted output some command writes, the read files
    as dry seeds. Order matters — a gate's inputs are produced before it runs."""
    ev = _events(session)
    prompts = [e["text"] for e in ev if e.get("event") == "prompt" and e.get("text")]

    write_at: dict[str, int] = {}
    for i, e in enumerate(ev):
        if e.get("event") == "write" and e.get("path"):
            write_at.setdefault(e["path"], i)
    gate_at: dict[str, tuple[int, str]] = {}
    for i, e in enumerate(ev):
        if e.get("event") == "bash" and e.get("cmd"):
            for out in accepted:
                if out not in gate_at and _writes(e["cmd"], out):
                    gate_at[out] = (i, e["cmd"])

    ordered: list[tuple[int, dict]] = []
    for path, i in write_at.items():
        if path not in gate_at:
            ordered.append((i, {"kind": "produce", "output": path,
                                "request": prompts[-1] if prompts else "produced interactively",
                                "class": "free"}))
    for out, (i, cmd) in gate_at.items():
        ordered.append((i, {"kind": "gate", "output": out, "run": cmd, "class": "validated"}))
    steps = [s for _, s in sorted(ordered, key=lambda x: x[0])]

    produced = [s["output"] for s in steps if s["kind"] == "produce"]
    gates = [s["run"] for s in steps if s["kind"] == "gate"]
    for a in accepted:
        if a in produced and not any(a in g for g in gates):
            raise kernel.ReticuliError(
                f"'{a}' is declared as an input to no gate (no check, no record)")

    bashes = [e["cmd"] for e in ev if e.get("event") == "bash" and e.get("cmd")]
    reads = [e["path"] for e in ev if e.get("event") == "read" and e.get("path")]
    named = {t.strip(";,()|&<>'\"") for c in bashes for t in c.replace('"', " ").replace("'", " ").split()}
    seeds = [f for f in dict.fromkeys(reads + sorted(named))
             if f and f not in write_at and f not in accepted
             and os.path.isfile(os.path.join(session, f))]
    return {"record": {"name": name, "inputs": seeds}, "step": steps}


def condense(session: str, accepted: list[str], into: str, name: str | None = None) -> dict:
    name = name or os.path.basename(os.path.abspath(session).rstrip(os.sep)) or "record"
    recipe = draft(session, accepted, name)
    warm = {a: kernel._hf(os.path.join(session, a)) for a in accepted
            if os.path.isfile(os.path.join(session, a))}

    build = into + ".building"
    if os.path.exists(build):
        shutil.rmtree(build)
    os.makedirs(build)
    with open(os.path.join(build, kernel.RECIPE), "w", encoding="utf-8") as f:
        f.write(render.dump_recipe(recipe))
    for seed in kernel._seeds(recipe):
        kernel._copy(os.path.join(session, seed), os.path.join(build, seed))
    for step in recipe["step"]:
        if step["kind"] == "produce":
            kernel._copy(os.path.join(session, step["output"]), os.path.join(build, step["output"]))

    for step in recipe["step"]:
        if step["kind"] == "gate":
            r, _ = kernel._jailed(step["run"], build, {**os.environ, "RETICULI": "1"})
            if r.returncode != 0:
                shutil.rmtree(build)
                raise kernel.ReticuliError(
                    f"cold gate failed: {(r.stderr or r.stdout).strip()[:150]}")

    for a, warm_h in warm.items():
        cold = os.path.join(build, a)
        cls = next((s.get("class", "exact") for s in recipe["step"] if s["output"] == a), "free")
        if cls != "free" and os.path.isfile(cold) and kernel._hf(cold) != warm_h:
            shutil.rmtree(build)
            raise kernel.ReticuliError(f"cold result does not match accepted (nondeterministic '{a}')")

    # the session's cost, as the trace shows it: one oracle call per prompt,
    # the trace's wall-clock span — the record's C1, kept as local residue
    ev = _events(session)
    prompts = sum(1 for e in ev if e.get("event") == "prompt")
    ts = [e["ts"] for e in ev if isinstance(e.get("ts"), (int, float))]
    if prompts:
        for _ in range(prompts):
            kernel._ledger_add(build, {"event": "oracle", "calls": 1})
        if len(ts) >= 2:
            kernel._ledger_add(build, {"event": "trace", "seconds": round(max(ts) - min(ts), 3)})

    from . import registry
    links = registry.detect_components(session, kernel._seeds(recipe))
    manifest = kernel.seal(build, components=links or None)
    if os.path.exists(into):
        shutil.rmtree(into)
    os.rename(build, into)
    return {"ok": True, "name": name, "root": manifest["root"], "into": into,
            "steps": recipe["step"], "inputs": kernel._seeds(recipe),
            "components": links}
