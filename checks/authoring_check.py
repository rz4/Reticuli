"""Authoring conformance gate — the seed of the `authoring` layer.

The machinery that turns sessions into records: condense (draft from a trace,
certify cold, account the session's C1), feedback (sense what's condensable),
pack (a project as a self-record: implementation free, check claimed), and
render's recipe writer. Layers on exchange; knows nothing of the CLI. Writes
AUTHORING_OK iff the layer conforms. Stdlib only, so it runs in any clean room.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.path.insert(0, ".")
from reticuli import condense as condense_mod
from reticuli import feedback, kernel, pack, render
from reticuli.condense import condense


def _calls_jailed_directly(path: str) -> bool:
    """True if the module reaches for kernel._jailed itself (a Call to a
    `_jailed` attribute or name) — an authoring module must run gates only
    through kernel.run_gate, which owns the scrub, the bound, and the jail."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "_jailed":
                return True
            if isinstance(fn, ast.Name) and fn.id == "_jailed":
                return True
    return False


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

        # cold-certification: the trace has no authority. condense must rebuild
        # in a clean room and re-run every gate COLD; a pinned verdict that does
        # not reproduce from the bytes (a nondeterministic gate) must refuse to
        # seal — no record forms from a claim the room cannot re-earn.
        ws2 = os.path.join(d, "ws2")
        os.makedirs(os.path.join(ws2, ".reticuli"))
        nd_gate = ("python3 -c \"import time; open('STAMP','w')"
                   ".write(str(time.time_ns()))\"")
        events2 = [{"event": "prompt", "text": "stamp the moment", "ts": 1.0},
                   {"event": "bash", "cmd": nd_gate, "ts": 2.0}]
        with open(os.path.join(ws2, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in events2) + "\n")
        subprocess.run(nd_gate, shell=True, cwd=ws2, check=True)   # warm STAMP
        rec2 = os.path.join(ws2, ".reticuli", "liquid", "stamp")
        try:
            condense(ws2, ["STAMP"], rec2, name="stamp")
            raise AssertionError("condense must refuse a verdict it cannot re-earn cold")
        except kernel.ReticuliError:
            pass

        # the AUTHORING GATE CONTRACT: condense and pack run gates only through
        # kernel.run_gate (scrubbed env, bounded wall-clock, quarantine), never
        # kernel._jailed directly — reaching for _jailed bypasses the scrub and
        # the bound. Enforced structurally, so a refactor cannot quietly reopen
        # the hole the reviewer found (pack sealing an inherited secret).
        for mod in (condense_mod, pack):
            assert not _calls_jailed_directly(mod.__file__), \
                f"{os.path.basename(mod.__file__)} must run gates via kernel.run_gate, not _jailed"

        # finding 1, behaviorally: pack runs the gate SCRUBBED, so an inherited
        # env secret cannot be sealed into the verdict.
        secret = "s3cr3t-" + "not-real"
        os.environ["AUTHORING_LEAK_PROBE"] = secret
        try:
            lp = os.path.join(d, "leakproj")
            os.makedirs(lp)
            with open(os.path.join(lp, "chk.py"), "w") as f:
                f.write("import os\n"
                        "open('OK','w').write(os.environ.get('AUTHORING_LEAK_PROBE','clean'))\n")
            with open(os.path.join(lp, "src.py"), "w") as f:
                f.write("# free\n")
            pack.pack(lp, "leak", ["src.py"], ["chk.py"], "python3 chk.py", "OK")
            with open(os.path.join(lp, "OK")) as f:
                assert secret not in f.read(), "pack must run the gate scrubbed (secret reached the verdict)"
        finally:
            os.environ.pop("AUTHORING_LEAK_PROBE", None)

        # finding 2: condense confines trace-derived paths BEFORE copying them. A
        # traced read of ../secret is a seed that escapes the session; condense
        # must refuse it at the confinement boundary, not copy it out of the
        # .building room on the way to the seal that refuses it.
        cs = os.path.join(d, "confine-sess")
        os.makedirs(os.path.join(cs, ".reticuli"))
        with open(os.path.join(cs, "solver.py"), "w") as f:
            f.write("print('ok')\n")
        with open(os.path.join(d, "cs-secret.txt"), "w") as f:     # at the session's PARENT
            f.write("TOP SECRET\n")
        cs_events = [{"event": "prompt", "text": "solve", "ts": 1.0},
                     {"event": "write", "path": "solver.py", "ts": 2.0},
                     {"event": "read", "path": "../cs-secret.txt", "ts": 3.0},
                     {"event": "bash", "cmd": "python3 solver.py && printf ok > OK", "ts": 4.0}]
        with open(os.path.join(cs, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in cs_events) + "\n")
        subprocess.run("python3 solver.py && printf ok > OK", shell=True, cwd=cs, check=True)
        cs_rec = os.path.join(d, "confine-rec")
        try:
            condense(cs, ["OK"], cs_rec, name="confine")
            raise AssertionError("condense must refuse a trace-derived seed that escapes the session")
        except kernel.ReticuliError:
            pass
        stray = [os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs
                 if f == "cs-secret.txt" and os.path.join(r, f) != os.path.join(d, "cs-secret.txt")]
        assert not stray, f"condense copied the escaping seed out of the room before refusing: {stray}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("AUTHORING_OK", "w") as f:
        f.write("authoring-ok\n")
    print("authoring-ok")
