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
RETICULI_AGENT_BUDGET (usd, default 3) to size the loop.

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

MODEL = os.environ.get("RETICULI_MODEL", "claude-sonnet-5")
OUT = os.environ["RETICULI_OUTPUT"]
BUDGET = os.environ.get("RETICULI_AGENT_BUDGET", "3")   # usd cap for the whole layer

# The agent produces ALL free files in one session; realize then calls the
# producer once per remaining file, each of which already exists -> skip. So the
# whole layer costs exactly one agentic session, accounted on the first call.
if os.path.isfile(OUT) and os.path.getsize(OUT) > 0:
    sys.exit(0)

with open("reticuli.toml", "rb") as f:
    recipe = tomllib.load(f)
produce = [s["output"] for s in recipe["step"] if s["kind"] == "produce"]
gate = next((s for s in recipe["step"] if s["kind"] == "gate"), None)
seeds = recipe["record"].get("inputs", [])
# the free own-stratum files: produce outputs not already supplied on disk
free = [p for p in produce if not (os.path.isfile(p) and os.path.getsize(p) > 0)]

task = f"""You are working inside a clean room that is a Reticuli record. Your job is to \
make its check pass by writing the required source files. There is NO reference \
implementation here — infer the required API and semantics from the check ALONE.

Create these files, standard library only, correct over clever:
{free}

The check(s) are the dry-seed files already in this directory: {seeds}. Read them first.
The gate command is:  {gate['run'] if gate else ''}
It must create the file:  {gate['output'] if gate else ''}

You MAY run the gate to test yourself and iterate until it passes — that is the point. \
When {gate['output'] if gate else 'the gate output'} exists and the gate exits 0, you are \
done; stop. Do NOT modify the check/seed files ({seeds}); only write the files listed above. \
Do not touch anything outside this directory."""

cmd = ["claude", "-p", task, "--model", MODEL, "--output-format", "json",
       "--max-budget-usd", str(BUDGET)]
if os.environ.get("RETICULI_AGENT_BYPASS"):
    cmd += ["--permission-mode", "bypassPermissions"]
else:                                   # scoped: edit/write files, run the python gate, nothing else
    cmd += ["--permission-mode", "acceptEdits",
            "--allowedTools", "Read", "Edit", "Write", "Bash(python3 *)", "Bash(python *)"]

if os.environ.get("RETICULI_AGENT_DRYRUN"):   # validate wiring without spending
    print("DRYRUN cmd:", " ".join(c if c != task else "<task…>" for c in cmd))
    print("free files:", free, "| gate:", gate["run"] if gate else None, "| budget $", BUDGET)
    sys.exit(1)                         # produced nothing — a dry run is not a realization

_LIMIT = re.compile(r"(session|usage|rate)\s+limit|you'?ve hit your|limit\s*·"
                    r"|reset[s]?\s|please try again|overloaded", re.IGNORECASE)


def _fail(msg: str) -> None:
    print(f"producer_agentic: {msg}", file=sys.stderr)
    sys.exit(1)


env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}   # subscription auth
r = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
if r.returncode != 0:
    _fail(f"claude exited {r.returncode}: {(r.stderr or r.stdout).strip()[:160]}")

generated = False
try:                                   # final json envelope carries the whole session's usage
    envelope = json.loads(r.stdout)
    if isinstance(envelope, dict):
        if envelope.get("is_error") or envelope.get("subtype") == "error":
            _fail(f"error envelope: {str(envelope.get('result'))[:160]}")
        u = envelope.get("usage") or {}
        out_tok = int(u.get("output_tokens", 0))
        generated = out_tok > 0
        usage = {"tokens": int(u.get("input_tokens", 0)) + out_tok}
        if isinstance(envelope.get("total_cost_usd"), (int, float)):
            usage["usd"] = envelope["total_cost_usd"]
        upath = os.environ.get("RETICULI_USAGE")
        if upath and usage["tokens"]:
            with open(upath, "w", encoding="utf-8") as f:
                json.dump(usage, f)
except (json.JSONDecodeError, TypeError, ValueError, OSError):
    pass

if _LIMIT.search(r.stdout) and not generated:
    _fail(f"limit/refusal, not a realization: {r.stdout.strip()[:160]}")

# the agent's own output text is discarded — the realization is the files it left
# in the room. Success is simply: the gate's target exists (realize re-checks it,
# jailed, as the authoritative gate).
if not (os.path.isfile(OUT) and os.path.getsize(OUT) > 0):
    _fail(f"agent finished but {OUT} was not produced (budget hit, or gate never passed)")
sys.exit(0)
