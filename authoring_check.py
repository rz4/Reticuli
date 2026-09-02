"""Authoring conformance gate — the seed of the `authoring` layer.

The machinery that turns sessions into records: condense (draft from a trace,
certify cold, account the session's C1), feedback (sense what's condensable),
pack (a project as a self-record: implementation free, check claimed), and
render's recipe writer. Layers on exchange; knows nothing of the CLI. Writes
AUTHORING_OK iff the layer conforms. Stdlib only, so it runs in any clean room.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.path.insert(0, ".")
from reticuli import feedback, kernel, pack, render
from reticuli.condense import condense


def battery() -> None:
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        os.makedirs(os.path.join(ws, ".reticuli"))
        with open(os.path.join(ws, "answer.txt"), "w") as f:
            f.write("42\n")
        gate = "grep -qx 42 answer.txt && printf ok > OK"
        events = [{"event": "prompt", "text": "write the answer", "ts": 5.0},
                  {"event": "write", "path": "answer.txt", "ts": 6.0},
                  {"event": "bash", "cmd": gate, "ts": 7.0}]
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\n")
        subprocess.run(gate, shell=True, cwd=ws, check=True)

        # the pilot senses a checked session as condensable
        assert feedback.pilot(ws)["condensable"], "feedback"

        # condense certifies cold; the record verifies and carries the session's
        # cost as its C1 — one oracle call per prompt, the trace's span
        rec = os.path.join(ws, ".reticuli", "liquid", "answer")
        assert condense(ws, ["OK"], rec, name="answer")["ok"], "condense"
        assert kernel.verify(rec)["ok"], "verify"
        c1 = kernel.cost(rec)
        assert c1["calls"] == 1 and c1["seconds"] == 2.0, "condense accounts C1"

        # a redo with different work lands on the same root (the basin), and the
        # drafted recipe round-trips through the renderer byte-faithfully
        m3 = os.path.join(d, "m3")
        kernel.realize(rec, "printf '42\\n' > answer.txt", m3)
        assert kernel.verify(m3)["root"] == kernel.verify(rec)["root"], "basin"
        recipe = kernel.load_recipe(rec)
        assert tomllib.loads(render.dump_recipe(recipe)) == recipe, "recipe round-trip"

        # pack: the implementation is free water, the check is the claim
        proj = os.path.join(d, "proj")
        os.makedirs(os.path.join(proj, "pkg"))
        with open(os.path.join(proj, "pkg", "__init__.py"), "w") as f:
            f.write("VALUE = 42\n")
        with open(os.path.join(proj, "check.py"), "w") as f:
            f.write("import sys; sys.path.insert(0, '.')\n"
                    "from pkg import VALUE\nassert VALUE == 42\n"
                    "open('OK', 'w').write('ok\\n')\n")

        def repack():
            return pack.pack(proj, "proj", ["pkg/*.py"], ["check.py"],
                             "python3 check.py", "OK")["root"]

        r0 = repack()
        with open(os.path.join(proj, "pkg", "__init__.py"), "a") as f:
            f.write("# free\n")
        assert repack() == r0, "editing the implementation keeps the root"
        with open(os.path.join(proj, "check.py"), "a") as f:
            f.write("# a stricter claim\n")
        assert repack() != r0, "editing the check moves the claim"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("AUTHORING_OK", "w") as f:
        f.write("authoring-ok\n")
    print("authoring-ok")
