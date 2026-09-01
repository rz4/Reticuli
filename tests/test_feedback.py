"""The pilot: an uncovered output nudges toward a gate; a checked session is
condensable."""
import json
import os
import subprocess

from reticuli import feedback


def _session(tmp_path, trace: list[dict], files: dict) -> str:
    ws = str(tmp_path / "s")
    os.makedirs(os.path.join(ws, ".reticuli"))
    for name, content in files.items():
        with open(os.path.join(ws, name), "w") as f:
            f.write(content)
    with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(e) for e in trace) + "\n")
    return ws


def test_uncovered_output_nudges_for_a_gate(tmp_path):
    ws = _session(tmp_path, [{"event": "write", "path": "answer.txt"}], {"answer.txt": "42\n"})
    p = feedback.pilot(ws)
    assert "answer.txt" in p["uncovered"] and not p["condensable"]
    assert "add a gate" in p["nudge"]


def test_checked_session_is_condensable(tmp_path):
    ws = _session(tmp_path, [
        {"event": "write", "path": "answer.txt"},
        {"event": "bash", "cmd": "grep -qx 42 answer.txt && printf ok > VERIFIED"}],
        {"answer.txt": "42\n"})
    subprocess.run("grep -qx 42 answer.txt && printf ok > VERIFIED", shell=True, cwd=ws, check=True)
    p = feedback.pilot(ws)
    assert p["condensable"] and not p["uncovered"]
    assert "condensable" in p["nudge"]
