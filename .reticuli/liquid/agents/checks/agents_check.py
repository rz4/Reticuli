"""Agents conformance gate — the seed of the `agents` layer.

The agent handshake: hook payloads (Claude Code's shape) become trace events,
guarded — no session means no-op, files outside the session are ignored — and
the wiring installs idempotently without touching the rest of the agent's
settings. The claim that matters: a hook-traced session condenses into a
record that verifies and carries its C1. Layers on authoring. Writes AGENTS_OK
iff the handshake conforms. Stdlib only, so it runs in any clean room.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, ".")
from reticuli import feedback, hooks, kernel
from reticuli.condense import condense


def battery() -> None:
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        os.makedirs(os.path.join(ws, ".reticuli"))

        # payloads map to events; non-events map to nothing
        gate = "grep -qx 42 answer.txt && printf ok > OK"
        assert hooks.event({"hook_event_name": "UserPromptSubmit",
                            "prompt": "write the answer", "cwd": ws})["event"] == "prompt"
        assert hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Write",
                            "tool_input": {"file_path": os.path.join(ws, "answer.txt")},
                            "cwd": ws})["path"] == "answer.txt"
        assert hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Read",
                            "tool_input": {"file_path": os.path.join(ws, "notes.md")},
                            "cwd": ws})["event"] == "read"
        assert hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                            "tool_input": {"command": gate}, "cwd": ws})["event"] == "bash"
        outside = {"hook_event_name": "PostToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": os.path.join(d, "elsewhere.txt")}, "cwd": ws}
        assert hooks.event(outside) is None, "outside the session is ignored"
        assert hooks.event({"hook_event_name": "SessionStart", "cwd": ws}) is None
        nowhere = os.path.join(d, "not-a-session")
        os.makedirs(nowhere)
        assert hooks.event({"hook_event_name": "UserPromptSubmit", "prompt": "hi",
                            "cwd": nowhere}) is None, "no session, no-op"

        # a hook-traced session condenses: the handshake feeds the whole chain
        with open(os.path.join(ws, "answer.txt"), "w") as f:
            f.write("42\n")
        subprocess.run(gate, shell=True, cwd=ws, check=True)
        assert feedback.pilot(ws)["condensable"], "traced session is condensable"
        rec = os.path.join(ws, ".reticuli", "liquid", "answer")
        assert condense(ws, ["OK"], rec, name="answer")["ok"], "condense"
        assert kernel.verify(rec)["ok"], "the record verifies"
        assert kernel.cost(rec)["calls"] == 1, "the prompt is the C1"

        # wiring: idempotent, and everything else in settings survives
        proj = os.path.join(d, "proj")
        os.makedirs(os.path.join(proj, ".claude"))
        with open(os.path.join(proj, ".claude", "settings.json"), "w") as f:
            json.dump({"model": "opus"}, f)
        first = hooks.install(proj)
        assert set(first["wired"]) == {"UserPromptSubmit", "PostToolUse"}, "wired"
        with open(os.path.join(proj, ".claude", "settings.json")) as f:
            before = f.read()
        assert hooks.install(proj)["status"] == "already wired", "idempotent"
        with open(os.path.join(proj, ".claude", "settings.json")) as f:
            after = f.read()
        assert before == after and json.loads(after)["model"] == "opus", "preserving"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("AGENTS_OK", "w") as f:
        f.write("agents-ok\n")
    print("agents-ok")
