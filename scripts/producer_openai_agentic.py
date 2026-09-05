"""An *agentic* producer for `ret realize`, OpenAI edition — the cross-vendor
sibling of producer_claude_agentic.py.

Where producer_openai.py writes each file blind in one call, this drives a
bounded tool-use loop on the OpenAI SDK: the model may write files and run the
gate, see it fail, and fix — until the gate passes or a turn/budget cap is hit.
It respects OPENAI_BASE_URL (a LiteLLM/gateway endpoint), unlike the oneshot
producer, and uses the SDK's HTTP stack (raw urllib is Cloudflare-blocked on the
science-cloud gateway). All work is inside main() — import is side-effect free.

Usage:
    ret realize <rec> --producer "python3 producer_openai_agentic.py" --into M3
    RETICULI_MODEL=gpt-5 RETICULI_AGENT_BUDGET=15 ret realize ...
"""
import json
import os
import subprocess
import sys
import tomllib


def _fail(msg: str) -> None:
    print(f"producer_openai_agentic: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    from openai import OpenAI  # lazy: import-safe even where the SDK is absent

    model = os.environ.get("RETICULI_MODEL", "gpt-5")
    out = os.environ["RETICULI_OUTPUT"]
    max_turns = int(os.environ.get("RETICULI_AGENT_TURNS", "40"))

    with open("reticuli.toml", "rb") as f:
        recipe = tomllib.load(f)
    gate = next((s for s in recipe["step"] if s["kind"] == "gate"), None)
    seeds = recipe["record"].get("inputs", [])
    supplied = [s["output"] for s in recipe["step"]
                if s["kind"] == "produce" and "from" in s]
    own = [s["output"] for s in recipe["step"]
           if s["kind"] == "produce" and "from" not in s]
    gate_cmd = gate["run"] if gate else ""
    gate_out = gate["output"] if gate else ""

    # Presence is EXISTENCE, not size: a free output may be legitimately empty (a
    # bare __init__.py). Completion is the GATE passing — realize re-runs it
    # jailed — with "all own files written" standing in when there is no gate.
    def present(p):
        return bool(p) and os.path.isfile(p)

    def record_done():
        return present(gate_out) if gate_out else bool(own) and all(present(p) for p in own)

    # the whole record is produced in one session; later per-file calls skip once
    # that session has driven the gate green
    if present(out) and record_done():
        return 0

    task = f"""You are reconstructing the source files of a content-addressed record so its \
check passes. There is NO reference implementation — infer the required API and semantics \
from the check files ALONE.

Your files to create (standard library only, correct over clever): {own}
The check/seed files (already present — read them first): {seeds}
Files supplied by lower layers (read, import from, do NOT modify): {supplied}
The gate command is:  {gate_cmd}
It must succeed and create:  {gate_out}

Use the tools: read_file to inspect the checks, write_file to create your files, run_gate to \
test. Iterate until run_gate reports success, then stop. Never modify the check/seed files."""

    tools = [
        {"type": "function", "function": {"name": "read_file",
            "description": "Read a file in the record directory.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "write_file",
            "description": "Write (create/overwrite) one of your source files.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"]}}},
        {"type": "function", "function": {"name": "run_gate",
            "description": "Run the gate command; returns exit code and output.",
            "parameters": {"type": "object", "properties": {}}}},
    ]

    def _safe(path):
        full = os.path.realpath(path)
        if full != os.path.realpath(".") and not full.startswith(os.path.realpath(".") + os.sep):
            raise ValueError(f"path escapes the record: {path}")
        return path

    def _do(name, args):
        if name == "read_file":
            try:
                with open(_safe(args["path"]), encoding="utf-8") as f:
                    return f.read()[:20000]
            except OSError as e:
                return f"error: {e}"
        if name == "write_file":
            p = _safe(args["path"])
            if p in seeds:
                return "refused: cannot modify a check/seed file"
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return f"wrote {p} ({len(args['content'])} bytes)"
        if name == "run_gate":
            r = subprocess.run(gate_cmd, shell=True, capture_output=True, text=True, check=False)
            tail = (r.stdout + r.stderr)[-4000:]
            return f"exit={r.returncode}\n{tail}"
        return "unknown tool"

    client = OpenAI()
    messages = [{"role": "user", "content": task}]
    usage_tok = 0
    for _ in range(max_turns):
        resp = client.chat.completions.create(model=model, messages=messages, tools=tools)
        if resp.usage:
            usage_tok += resp.usage.total_tokens
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            # model spoke without acting; nudge once toward the tools
            messages.append({"role": "user",
                             "content": "Use write_file then run_gate; stop when it passes."})
            continue
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = _do(tc.function.name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            if tc.function.name == "run_gate" and result.startswith("exit=0"):
                _report(usage_tok)
                if present(out):        # gate green; an empty free file still counts
                    return 0
    _report(usage_tok)
    if not record_done():
        why = f"the gate never produced {gate_out}" if gate_out else "the record is incomplete"
        _fail(f"agent finished but {why} (turn cap or gate never passed)")
    if not present(out):
        _fail(f"agent finished but did not write {out} (turn cap or gate never passed)")
    return 0


def _report(tokens: int) -> None:
    upath = os.environ.get("RETICULI_USAGE")
    if upath and tokens:
        rec = {"tokens": tokens}
        price = os.environ.get("RETICULI_PRICE")     # "in,out" usd/Mtok, optional
        try:
            if price:
                i, o = (float(x) for x in price.split(","))
                rec["usd"] = round(tokens / 1e6 * (i + o) / 2, 6)
        except ValueError:
            pass
        with open(upath, "w", encoding="utf-8") as f:
            json.dump(rec, f)


if __name__ == "__main__":
    sys.exit(main())
