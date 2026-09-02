"""Surface conformance gate — the seed of the `surface` rung.

The human handshake: drives the CLI end-to-end through the layers beneath it
(init -> run -> condense -> verify -> realize -> prove) and claims the volatile
surface itself — argv grammar, exit codes, the shape of what a user sees (TOML
verdicts, the cost block, --json underneath). The functional depth is claimed
by the inner gates (kernel_check, exchange_check, authoring_check,
agents_check); above sits only contact — the README, claimed by
readme_check.py. Writes SURFACE_OK iff the toolchain a *user* touches is
conformant. Stdlib only, so it runs in any clean room.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, ".")
import reticuli.__main__   # the CLI entrypoint
from reticuli import cli


def _run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(argv)
    return code, buf.getvalue()


def battery() -> None:
    assert reticuli.__main__.main is cli.main, "entrypoint"
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        code, _ = _run(["init", ws])
        assert code == 0, "init exits 0"
        with open(os.path.join(ws, ".gitignore")) as f:
            assert "ledger.jsonl" in f.read(), "init is git-native"

        with open(os.path.join(ws, "answer.txt"), "w") as f:
            f.write("42\n")
        gate = "grep -qx 42 answer.txt && printf ok > OK"
        code, _ = _run(["run", gate, "-C", ws])
        assert code == 0 and os.path.isfile(os.path.join(ws, "OK")), "run authors a gate"
        events = [{"event": "prompt", "text": "write the answer", "ts": 5.0},
                  {"event": "write", "path": "answer.txt", "ts": 6.0},
                  {"event": "bash", "cmd": gate, "ts": 7.0}]
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\n")

        rec = os.path.join(ws, ".reticuli", "liquid", "answer")
        code, _ = _run(["condense", ws, "--accept", "OK", "--into", rec, "--name", "answer"])
        assert code == 0, "condense exits 0"
        code, out = _run(["verify", rec])
        assert code == 0 and "fresh" in out, "verify says fresh"
        code, out = _run(["verify", rec, "--json"])
        assert code == 0 and json.loads(out)["ok"], "--json underneath"

        m3 = os.path.join(d, "m3")
        code, out = _run(["realize", rec, "--producer", "printf '42\\n' > answer.txt",
                          "--into", m3])
        assert code == 0 and "calls" in out, "realize reports what it paid"
        m2 = os.path.join(d, "m2")
        shutil.copytree(rec, m2)
        code, out = _run(["prove", rec, m2, m3])
        assert code == 0, "prove exits 0"
        assert "satisfied = true" in out and "[cost]" in out, "the verdict and the bill"

        code, out = _run(["records", ws])
        assert code == 0 and "answer" in out, "the drawer renders"

        # two lenses, one verb: a session's tree is dry/wet; a record's tree is
        # its anatomy — seeds (the claim), free strata, pinned verdicts
        code, out = _run(["tree", ws])
        assert code == 0 and "vapor" in out, "the session lens"
        code, out = _run(["tree", rec])
        assert code == 0 and "free  answer.txt" in out and "pin   OK" in out \
            and "rung(s)" in out, "the record lens"

        # the agent handshake at the surface: `ret hook` is silent, `ret hooks` wires
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "again", "cwd": ws}
        stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps(payload))
        try:
            code, out = _run(["hook", "-C", ws])
        finally:
            sys.stdin = stdin
        assert code == 0 and out == "", "hook exits 0 and prints nothing"
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl")) as f:
            assert '"prompt"' in f.readlines()[-1], "the payload became a trace event"
        code, _ = _run(["hooks", ws])
        assert code == 0 and os.path.isfile(
            os.path.join(ws, ".claude", "settings.json")), "hooks wires the agent"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("SURFACE_OK", "w") as f:
        f.write("surface-ok\n")
    print("surface-ok")
