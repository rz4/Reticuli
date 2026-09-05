"""A live-model producer for `ret realize`, OpenAI edition.

Same contract as producer_claude.py: one blind text call per produce file — no
tools, no reference implementation, no iteration. The model gets the recipe and
the check inline and must land in the basin. Real usage (tokens; usd if a price
is declared) is reported back through $RETICULI_USAGE for the cost ledger.

All work is inside `main()`: importing this module has no side effects, so the
workshop gate can assert it.

Usage:
    ret realize <record> --producer "python3 scripts/producer_openai.py" --into M3
    RETICULI_MODEL=gpt-5.1 ret realize ...                # pick the model
    RETICULI_PRICE="1.25,10" ...                          # usd per Mtok in,out
"""
import json
import os
import re
import sys
import tomllib
import urllib.request


def main() -> int:
    model = os.environ.get("RETICULI_MODEL", "gpt-5.1")
    out = os.environ["RETICULI_OUTPUT"]

    # an earlier step's call already produced this, or a component supplied it
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return 0

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
              "`from <pkg> import <module>` to succeed." if out.endswith("__init__.py") else ""

    present = []
    for f in produce:
        if f != out and os.path.isfile(f):
            with open(f, encoding="utf-8") as fh:
                present.append(f"--- {f} ---\n{fh.read()}")
    present_text = ("\n\n# files already in this record — import from them and match their API, "
                    "do NOT rewrite them:\n" + "\n\n".join(present)) if present else ""

    prompt = f"""Reconstruct ONE file of a content-addressed record from its check ALONE. There is \
no reference implementation — infer the required API and semantics from the check.

Output ONLY the complete contents of `{out}`. No prose, no explanation. You may wrap it in a \
single ```python code fence or emit it bare; nothing else.{minimal}

# reticuli.toml (the recipe)
{recipe_text}

# the check(s) that must pass (dry seeds)
{seed_text}

The gate runs `{gate['run'] if gate else ''}` and must create `{gate['output'] if gate else ''}`.
The record's files are {produce} (each reconstructed the same way).
Standard library only. Correct over clever. Write `{out}` now.{present_text}"""

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps({"model": model,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        envelope = json.load(resp)

    text = envelope["choices"][0]["message"]["content"] or ""
    u = envelope.get("usage") or {}
    usage = {"tokens": int(u.get("prompt_tokens", 0)) + int(u.get("completion_tokens", 0))}
    price = os.environ.get("RETICULI_PRICE", "")
    if "," in price:
        p_in, p_out = (float(x) for x in price.split(",", 1))
        usage["usd"] = (u.get("prompt_tokens", 0) * p_in
                        + u.get("completion_tokens", 0) * p_out) / 1_000_000
    upath = os.environ.get("RETICULI_USAGE")
    if upath and usage["tokens"]:
        with open(upath, "w", encoding="utf-8") as f:
            json.dump(usage, f)

    fence = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", text, re.DOTALL)
    body = (fence.group(1) if fence else text).strip("\n")
    if body:
        if os.path.dirname(out):
            os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(body + "\n")

    return 0 if os.path.isfile(out) and os.path.getsize(out) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
