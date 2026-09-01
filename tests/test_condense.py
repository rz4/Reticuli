"""Condense drafts a record from a trace and certifies it cold. A read-only
command (ls/cat/rm) is never mistaken for a gate."""
import json
import os
import subprocess

import pytest

from reticuli import condense as C
from reticuli import kernel


def _session(tmp_path, trace: list[dict]) -> str:
    ws = str(tmp_path / "s")
    os.makedirs(os.path.join(ws, ".reticuli"))
    open(os.path.join(ws, "answer.txt"), "w").write("42\n")
    with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(e) for e in trace) + "\n")
    return ws


def test_read_only_command_is_not_a_gate():
    assert not C._writes("ls -l VERIFIED", "VERIFIED")
    assert not C._writes("cat answer.txt", "answer.txt")
    assert not C._writes("rm VERIFIED && python t.py", "VERIFIED")
    assert C._writes("echo ok > VERIFIED", "VERIFIED")
    assert C._writes("python gen.py out.json", "out.json")


def test_no_check_no_record(tmp_path):
    ws = _session(tmp_path, [{"event": "write", "path": "answer.txt"}])
    with pytest.raises(kernel.ReticuliError, match="no check, no record"):
        C.condense(ws, ["answer.txt"], str(tmp_path / "rec"))


def test_condense_seals_and_the_record_verifies(tmp_path):
    ws = _session(tmp_path, [
        {"event": "write", "path": "answer.txt"},
        {"event": "bash", "cmd": "grep -qx 42 answer.txt && printf ok > VERIFIED"}])
    subprocess.run("grep -qx 42 answer.txt && printf ok > VERIFIED", shell=True, cwd=ws)
    r = C.condense(ws, ["VERIFIED"], str(tmp_path / "rec"), name="answer")
    assert r["ok"]
    rec = str(tmp_path / "rec")
    assert kernel.verify(rec)["ok"]
    # a redo with different work still certifies (answer.txt is free)
    m3 = kernel.realize(rec, "printf '42\\n' > answer.txt", str(tmp_path / "m3"))
    assert kernel.verify(str(tmp_path / "m3"))["root"] == kernel.verify(rec)["root"]
