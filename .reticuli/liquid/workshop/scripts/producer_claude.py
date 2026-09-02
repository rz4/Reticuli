"""A live-model producer for `ret realize`.

A real model reconstructs the record's *free* code from its check ALONE — there
is no reference implementation in the clean room. The record's identity excludes
free outputs, so the model need not match anyone's bytes; it only has to make the
check pass. If it does, the redo lands on the same root: a live-model M3.

Default mode is **oneshot** (lowest privilege): one `claude -p` text call per
produce file, NO tools, NO autonomous loop. The model gets the recipe and the
check inline and must return the file blind (it cannot run the gate to iterate).
The script writes the returned text; realize then certifies the record cold.
Real oracle usage (tokens, usd) is reported back through $RETICULI_USAGE, so the
redo's ledger accounts what the model actually cost.

Usage:
    ret realize <record> --producer "python3 scripts/producer_claude.py" --into M3
    RETICULI_MODEL=claude-opus-4-8 ret realize ...        # pick the model
"""
import json
import os
import re
import subprocess
import sys
import tomllib

MODEL = os.environ.get("RETICULI_MODEL", "claude-sonnet-5")
OUT = os.environ["RETICULI_OUTPUT"]

# an earlier step's call already produced this, or a component supplied it
if os.path.isfile(OUT) and os.path.getsize(OUT) > 0:
    sys.exit(0)

with open("reticuli.toml", "rb") as f:
    recipe = tomllib.load(f)
produce = [s["output"] for s in recipe["step"] if s["kind"] == "produce"]
gate = next((s for s in recipe["step"] if s["kind"] == "gate"), None)
seeds = {}
for s in recipe["record"].get("inputs", []):
    if os.path.isfile(s):
        with open(s, encoding="utf-8") as f:
            seeds[s] = f.read()

with open("reticuli.toml", encoding="utf-8") as f:
    recipe_text = f.read()
seed_text = "\n\n".join(f"--- {name} ---\n{body}" for name, body in seeds.items())
minimal = " This is a package __init__; keep it minimal — the check only needs " \
          "`from <pkg> import <module>` to succeed." if OUT.endswith("__init__.py") else ""

# already-present record files (a dependency's supplied code, and siblings written
# by earlier steps) — the reconstruction must cohere with these
present = []
for f in produce:
    if f != OUT and os.path.isfile(f):
        with open(f, encoding="utf-8") as fh:
            present.append(f"--- {f} ---\n{fh.read()}")
present_text = ("\n\n# files already in this record — import from them and match their API, "
                "do NOT rewrite them:\n" + "\n\n".join(present)) if present else ""

prompt = f"""Reconstruct ONE file of a content-addressed record from its check ALONE. There is \
no reference implementation — infer the required API and semantics from the check.

Output ONLY the complete contents of `{OUT}`. No prose, no explanation. You may wrap it in a \
single ```python code fence or emit it bare; nothing else.{minimal}

# reticuli.toml (the recipe)
{recipe_text}

# the check(s) that must pass (dry seeds)
{seed_text}

The gate runs `{gate['run'] if gate else ''}` and must create `{gate['output'] if gate else ''}`.
The record's files are {produce} (each reconstructed the same way).
Standard library only. Correct over clever. Write `{OUT}` now.{present_text}"""

# a hosted-CLI status line masquerading as content — the reason a session-limited
# run once wrote "You've hit your session limit …" into every file as if it were code
_LIMIT = re.compile(r"(session|usage|rate)\s+limit|you'?ve hit your|limit\s*·"
                    r"|reset[s]?\s|please try again|overloaded", re.IGNORECASE)


def _fail(msg: str) -> None:
    print(f"producer_claude: {msg}", file=sys.stderr)
    sys.exit(1)                         # write nothing — realize treats this as a bounce


env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}   # subscription auth
r = subprocess.run(["claude", "-p", prompt, "--model", MODEL, "--output-format", "json"],
                   env=env, capture_output=True, text=True, check=False)
if r.returncode != 0:
    _fail(f"claude exited {r.returncode}: {(r.stderr or r.stdout).strip()[:160]}")

text, generated = r.stdout, False
try:                                   # the json envelope: result text + real usage
    envelope = json.loads(text)
    if not isinstance(envelope, dict):
        raise TypeError("not an envelope")
    if envelope.get("is_error") or envelope.get("subtype") == "error":
        _fail(f"error envelope: {str(envelope.get('result'))[:160]}")
    text = envelope.get("result") or ""
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
    pass                               # plain text from an older CLI — use as-is

# a limit/refusal notice, not code: refuse when the model never actually generated,
# or when the whole reply is a single status line that trips the signature
if _LIMIT.search(r.stdout) and not generated:
    _fail(f"limit/refusal, not a realization: {r.stdout.strip()[:160]}")

fence = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", text, re.DOTALL)   # take a code fence if present
body = (fence.group(1) if fence else text).strip("\n")
if not body:
    _fail("empty response")
if body.count("\n") < 2 and _LIMIT.search(body):
    _fail(f"one-line limit/refusal in body: {body[:160]}")
if os.path.dirname(OUT):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(body + "\n")

sys.exit(0 if os.path.isfile(OUT) and os.path.getsize(OUT) > 0 else 1)
