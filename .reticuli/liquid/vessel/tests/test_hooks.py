"""The agent handshake: hook payloads become trace events, guarded; the wiring
installs idempotently and preserves the rest of the agent's settings."""
import json
import os

from reticuli import hooks


def _ws(tmp_path) -> str:
    ws = str(tmp_path / "ws")
    os.makedirs(os.path.join(ws, ".reticuli"))
    return ws


def _trace(ws: str) -> list[dict]:
    with open(os.path.join(ws, ".reticuli", "vapor.jsonl")) as f:
        return [json.loads(line) for line in f]


def test_payloads_become_trace_events(tmp_path):
    ws = _ws(tmp_path)
    hooks.event({"hook_event_name": "UserPromptSubmit", "prompt": "do it", "cwd": ws})
    hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Edit",
                 "tool_input": {"file_path": os.path.join(ws, "a.py")}, "cwd": ws})
    hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Read",
                 "tool_input": {"file_path": os.path.join(ws, "b.md")}, "cwd": ws})
    hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "pytest -q"}, "cwd": ws})
    ev = _trace(ws)
    assert [e["event"] for e in ev] == ["prompt", "write", "read", "bash"]
    assert ev[1]["path"] == "a.py" and all("ts" in e for e in ev)


def test_guards_hold(tmp_path):
    ws = _ws(tmp_path)
    outside = str(tmp_path / "elsewhere.txt")
    assert hooks.event({"hook_event_name": "PostToolUse", "tool_name": "Write",
                        "tool_input": {"file_path": outside}, "cwd": ws}) is None
    assert hooks.event({"hook_event_name": "SessionStart", "cwd": ws}) is None
    not_a_session = str(tmp_path / "plain")
    os.makedirs(not_a_session)
    assert hooks.event({"hook_event_name": "UserPromptSubmit", "prompt": "hi",
                        "cwd": not_a_session}) is None
    assert not os.path.exists(os.path.join(not_a_session, ".reticuli"))


def test_install_is_idempotent_and_preserving(tmp_path):
    proj = str(tmp_path / "proj")
    os.makedirs(os.path.join(proj, ".claude"))
    settings = os.path.join(proj, ".claude", "settings.json")
    with open(settings, "w") as f:
        json.dump({"permissions": {"allow": ["Bash(ls:*)"]}}, f)
    assert set(hooks.install(proj)["wired"]) == {"UserPromptSubmit", "PostToolUse"}
    with open(settings) as f:
        once = f.read()
    assert hooks.install(proj)["status"] == "already wired"
    with open(settings) as f:
        twice = f.read()
    assert once == twice
    merged = json.loads(twice)
    assert merged["permissions"] == {"allow": ["Bash(ls:*)"]}
    assert any(h["command"] == "ret hook"
               for e in merged["hooks"]["PostToolUse"] for h in e["hooks"])
