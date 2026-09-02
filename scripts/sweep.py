"""The reproducible sweep runner — one honest command for the whole grid.

Runs series sequentially (never concurrently — a lock prevents the double-run
that once corrupted the data), each series probing all six layers via probe.py,
every row stamped with the claim root it was measured against and every landed
specimen archived. Prints the plan and cost estimate by default; runs only what
you name, so spend is always explicit.

    python3 scripts/sweep.py                      # show the plan, run nothing
    python3 scripts/sweep.py --go free            # controls only (byte-copy, stub) — $0
    python3 scripts/sweep.py --go haiku           # haiku oneshot + agentic
    python3 scripts/sweep.py --go haiku-oneshot sonnet-oneshot
    python3 scripts/sweep.py --go all             # the whole grid (costs real money)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "scripts", "probe.py")
PROFILE = os.path.join(ROOT, "docs", "reflection_profile.jsonl")
SPECIMENS = os.path.join(ROOT, "docs", "experiments", "specimens")
LOCK = os.path.join(ROOT, "runs", ".sweep.lock")
PY = sys.executable

_CP = f'mkdir -p reticuli && cp "{ROOT}/$RETICULI_OUTPUT" "$RETICULI_OUTPUT"'
_STUB = 'mkdir -p "$(dirname "$RETICULI_OUTPUT")" 2>/dev/null; printf "stub = None\\n" > "$RETICULI_OUTPUT"'
_ONESHOT = f'{PY} {ROOT}/scripts/producer_claude.py'
_AGENTIC = f'{PY} {ROOT}/scripts/producer_claude_agentic.py'

# label, model, producer, per-layer budget (agentic only), rough total $, note
PLAN = [
    ("byte-copy", None, _CP, None, 0.0, "positive control — must land 6/6"),
    ("negative-stub", None, _STUB, None, 0.0, "negative control — must land 0/6"),
    ("haiku-oneshot", "claude-haiku-4-5-20251001", _ONESHOT, None, 1.2, "budget, blind"),
    ("haiku-agentic", "claude-haiku-4-5-20251001", _AGENTIC, "3", 1.5, "budget, iterating"),
    ("sonnet-oneshot", "claude-sonnet-5", _ONESHOT, None, 8.7, "pro, blind"),
    ("sonnet-agentic", "claude-sonnet-5", _AGENTIC, "4", 6.0, "pro, iterating"),
    ("opus-oneshot", "claude-opus-4-8", _ONESHOT, None, 12.0, "top, blind"),
    ("opus-agentic", "claude-opus-4-8", _AGENTIC, "5", 10.0, "top, iterating"),
]
GROUPS = {"free": ["byte-copy", "negative-stub"],
          "controls": ["byte-copy", "negative-stub"],
          "haiku": ["haiku-oneshot", "haiku-agentic"],
          "sonnet": ["sonnet-oneshot", "sonnet-agentic"],
          "opus": ["opus-oneshot", "opus-agentic"],
          "oneshot": [p[0] for p in PLAN if p[0].endswith("oneshot")],
          "agentic": [p[0] for p in PLAN if p[0].endswith("agentic")],
          "all": [p[0] for p in PLAN]}


def _select(names):
    want, seen = [], set()
    for n in names:
        for label in GROUPS.get(n, [n]):
            if label not in seen:
                seen.add(label)
                want.append(label)
    return [p for p in PLAN if p[0] in want]


def _lock():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    if os.path.exists(LOCK):
        try:
            with open(LOCK) as f:
                os.kill(int(f.read().strip()), 0)
            sys.exit(f"a sweep is already running (lock {LOCK}); refusing to run concurrently")
        except (ValueError, ProcessLookupError, PermissionError):
            pass                                          # stale lock
    with open(LOCK, "w") as f:
        f.write(str(os.getpid()))


def show_plan():
    print(f"# sweep plan  (profile -> {os.path.relpath(PROFILE, ROOT)}, "
          f"specimens -> {os.path.relpath(SPECIMENS, ROOT)})\n")
    print(f"  {'series':<16}{'model':<28}{'~$':>7}   note")
    for label, model, _, _b, est, note in PLAN:
        print(f"  {label:<16}{(model or '—'):<28}{est:>7.1f}   {note}")
    print("\n# groups: free · controls · haiku · sonnet · opus · oneshot · agentic · all")
    print("# run with:  python3 scripts/sweep.py --go <group|series> …")


def run(selected):
    _lock()
    try:
        print(f"# running {len(selected)} series, sequentially · profile {PROFILE}")
        for label, model, producer, budget, _est, _note in selected:
            print(f"\n########## {label} ##########", flush=True)
            env = {**os.environ, "RETICULI_PROFILE": PROFILE, "RETICULI_ARCHIVE": SPECIMENS}
            if model:
                env["RETICULI_MODEL"] = model
            if budget:
                env["RETICULI_AGENT_BUDGET"] = budget
            subprocess.run([PY, PROBE, producer, label], env=env, cwd=ROOT, check=False)
    finally:
        os.remove(LOCK)
    print("\n# sweep complete")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--go" in args:
        names = args[args.index("--go") + 1:] or ["free"]
        sel = _select(names)
        if not sel:
            sys.exit(f"nothing selected from {names}")
        run(sel)
    else:
        show_plan()
