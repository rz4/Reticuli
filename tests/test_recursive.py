"""DAG-aware rehydrate: a record and its component dependency both regenerate,
bottom-up, and the whole chain lands on the same root — the layered self-host."""
import json
import os
import subprocess

from reticuli import kernel, registry
from reticuli.condense import condense


def _trace(ws, events):
    with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(e) for e in events) + "\n")


def _chain(tmp_path):
    ws = str(tmp_path / "ws")
    os.makedirs(os.path.join(ws, ".reticuli"))
    # component 'lib': a gate output lib.txt = LIBDATA (pinned, deterministic)
    _trace(ws, [{"event": "bash", "cmd": "printf LIBDATA > lib.txt"}])
    subprocess.run("printf LIBDATA > lib.txt", shell=True, cwd=ws, check=True)
    condense(ws, ["lib.txt"], os.path.join(ws, ".reticuli", "liquid", "lib"), name="lib")
    # app: seed dep.txt (== lib.txt), produce app.py (free), a canonical gate that
    # covers app.py but whose verdict is invariant to app.py's content
    with open(os.path.join(ws, "dep.txt"), "w") as f:
        f.write("LIBDATA")
    with open(os.path.join(ws, "app.py"), "w") as f:
        f.write("print(1)\n")
    gate = "cat app.py >/dev/null && grep -q LIBDATA dep.txt && printf ok > VERIFIED"
    _trace(ws, [{"event": "read", "path": "dep.txt"},
                {"event": "write", "path": "app.py"},
                {"event": "bash", "cmd": gate}])
    subprocess.run(gate, shell=True, cwd=ws, check=True)
    r = condense(ws, ["app.py", "VERIFIED"], os.path.join(ws, ".reticuli", "liquid", "app"), name="app")
    return ws, r


def test_recursive_rehydrate_reproduces_the_whole_chain(tmp_path):
    _ws, r = _chain(tmp_path)
    assert any(c["component"] == "lib" for c in r["components"])   # app depends on lib
    app = r["into"]

    # DAG-aware: regrow lib AND app (a *different* app.py) — the chain reproduces
    out = registry.rehydrate(app, "printf 'print(2)\\n' > app.py", str(tmp_path / "M3"))
    assert any(c["component"] == "lib" for c in out["rehydrated_components"])
    assert kernel._hf(os.path.join(str(tmp_path / "M3"), "app.py")) != \
        kernel._hf(os.path.join(app, "app.py"))                    # different implementation
    assert out["root"] == kernel.verify(app)["root"]               # same claim
