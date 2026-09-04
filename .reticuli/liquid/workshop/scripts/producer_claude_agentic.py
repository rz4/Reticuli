"""An *agentic* producer for `ret realize` — the iterate-until-it-passes sibling
of producer_claude.py.

Where the oneshot producer writes each file blind in a single call, this runs one
autonomous `claude` session in the clean room, with tools, that may READ the
check, WRITE the free files, RUN the gate, see it fail, and fix — until the gate
passes or a dollar budget is spent. It is a *different experiment*: not "can the
model land blind" but "can an agent land it given the ability to test, and at
what cost." (Gate E, the cost envelope, is the whole point — a bounded loop, so
the number means something.)

Integrity holds: the room contains only the check and the already-free lower
layers — no reference implementation — so running the gate and iterating is
honest "make the tests pass," not copying. realize's final jailed gate stays the
authoritative verdict.

Privilege: producers are unjailed by design, so this *is* an autonomous agent on
your machine, scoped to the room (cwd) and to a tool allowlist. It can write
files and run the python gate; nothing else is pre-approved. Set
RETICULI_AGENT_BYPASS=1 to loosen permissions if a run stalls, and
RETICULI_AGENT_BUDGET (usd, default 3) to size the loop. All work is inside
`main()`: importing this module has no side effects, so the workshop gate can
assert it.

Usage:
    ret realize <rec> --producer "python3 scripts/producer_claude_agentic.py" --into M3
    RETICULI_MODEL=claude-haiku-4-5-20251001 RETICULI_AGENT_BUDGET=1 ret realize ...
"""
import json
import os
import re
import subprocess
import sys
import tomllib

_LIMIT = re.compile(r"(session|usage|rate)\s+limit|you'?ve hit your|limit\s*·"
                    r"|reset[s]?\s|please try again|overloaded", re.IGNORECASE)


def _fail(msg: str) -> None:
    print(f"producer_agentic: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    model = os.environ.get("RETICULI_MODEL", "claude-sonnet-5")
    out = os.environ["RETICULI_OUTPUT"]
    budget = os.environ.get("RETICULI_AGENT_BUDGET", "3")   # usd cap for the whole layer

    # The agent produces ALL free files in one session; realize then calls the
    # producer once per remaining file, each of which already exists -> skip. So the
    # whole layer costs exactly one agentic session, accounted on the first call.
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return 0

    with open("reticuli.toml", "rb") as f:
        recipe = tomllib.load(f)
    gate = next((s for s in recipe["step"] if s["kind"] == "gate"), None)
    seeds = recipe["record"].get("inputs", [])
    # own stratum = produce steps NOT supplied by a component (the recipe knows,
    # via `from`) — presence on disk does not decide ownership, so an interrupted
    # attempt's partial files stay the agent's to finish or repair
    supplied = [s["output"] for s in recipe["step"]
                if s["kind"] == "produce" and "from" in s]
    own = [s["output"] for s in recipe["step"]
           if s["kind"] == "produce" and "from" not in s]
    missing = [p for p in own if not (os.path.isfile(p) and os.path.getsize(p) > 0)]
    partial = [p for p in own if p not in missing]

    partial_note = (f"\nThese of your files already exist from an interrupted earlier "
                    f"attempt — read them; repair or rewrite any that are wrong:\n{partial}\n"
                    if partial else "")
    task = f"""You are working inside a clean room that is a Reticuli record. Your job is to \
make its check pass by writing the required source files. There is NO reference \
implementation here — infer the required API and semantics from the check ALONE.

YOUR files (create the missing, standard library only, correct over clever):
{missing}
{partial_note}
The check(s) are the dry-seed files already in this directory: {seeds}. Read them first.
Files supplied by lower layers — read and import from them, do NOT modify: {supplied}
The gate command is:  {gate['run'] if gate else ''}
It must create the file:  {gate['output'] if gate else ''}

You MAY run the gate to test yourself and iterate until it passes — that is the point. \
When {gate['output'] if gate else 'the gate output'} exists and the gate exits 0, you are \
done; stop. Never modify the check/seed files ({seeds}) or the supplied files; write only \
your own files listed above. Do not touch anything outside this directory."""

    cmd = ["claude", "-p", task, "--model", model, "--output-format", "json",
           "--max-budget-usd", str(budget)]
    if os.environ.get("RETICULI_AGENT_BYPASS"):
        cmd += ["--permission-mode", "bypassPermissions"]
    else:                               # scoped: edit/write files, run the python gate, nothing else
        cmd += ["--permission-mode", "acceptEdits",
                "--allowedTools", "Read", "Edit", "Write", "Bash(python3 *)", "Bash(python *)"]

    if os.environ.get("RETICULI_AGENT_DRYRUN"):   # validate wiring without spending
        print("DRYRUN cmd:", " ".join(c if c != task else "<task…>" for c in cmd))
        print("missing:", missing, "| partial:", partial,
              "| gate:", gate["run"] if gate else None, "| budget $", budget)
        return 1                        # produced nothing — a dry run is not a realization

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}   # subscription auth

    # long agentic sessions occasionally die to a transient mid-session error; one
    # retry is honest (each session's files persist in the room, and the retry's
    # task recomputes missing/partial) — a limit/refusal is never retried
    last, generated = "", False
    total = {"tokens": 0, "usd": 0.0}      # retries sum into one usage report
    r = None
    for attempt in (1, 2):
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
        transient = False
        if r.returncode != 0:
            last = f"claude exited {r.returncode}: {(r.stderr or r.stdout).strip()[:160]}"
            transient = not _LIMIT.search(r.stdout or "")
        try:                           # final json envelope carries the session's usage
            envelope = json.loads(r.stdout)
            if isinstance(envelope, dict):
                u = envelope.get("usage") or {}
                out_tok = int(u.get("output_tokens", 0))
                generated = generated or out_tok > 0
                total["tokens"] += int(u.get("input_tokens", 0)) + out_tok
                if isinstance(envelope.get("total_cost_usd"), (int, float)):
                    total["usd"] += envelope["total_cost_usd"]
                if envelope.get("is_error") or envelope.get("subtype") == "error":
                    last = f"error envelope: {str(envelope.get('result'))[:160]}"
                    transient = not _LIMIT.search(r.stdout)
                else:
                    last = ""
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            pass
        if not last:
            break                       # clean session
        if attempt == 1 and transient:
            print(f"producer_agentic: transient session failure, retrying once: {last[:100]}",
                  file=sys.stderr)
            continue

    upath = os.environ.get("RETICULI_USAGE")
    if upath and total["tokens"]:
        with open(upath, "w", encoding="utf-8") as f:
            json.dump({"tokens": total["tokens"], "usd": round(total["usd"], 6)}, f)
    if last:
        _fail(last)
    if _LIMIT.search(r.stdout or "") and not generated:
        _fail(f"limit/refusal, not a realization: {r.stdout.strip()[:160]}")

    # the agent's own output text is discarded — the realization is the files it left
    # in the room. Success is simply: the gate's target exists (realize re-checks it,
    # jailed, as the authoritative gate).
    if not (os.path.isfile(out) and os.path.getsize(out) > 0):
        _fail(f"agent finished but {out} was not produced (budget hit, or gate never passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
