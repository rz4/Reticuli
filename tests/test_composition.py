"""Records become components: a dry seed matching a registry record's output
links them; pull brings a component in; deps draws the DAG."""
import json
import os
import subprocess

from reticuli import kernel, registry
from reticuli.condense import condense


def _component_a(tmp_path) -> tuple[str, dict]:
    """A record 'A' whose gate output lib.txt = 'LIBDATA'."""
    d = str(tmp_path / "ws")
    os.makedirs(os.path.join(d, ".reticuli"))
    with open(os.path.join(d, ".reticuli", "vapor.jsonl"), "w") as f:
        f.write(json.dumps({"event": "bash", "cmd": "printf LIBDATA > lib.txt"}) + "\n")
    subprocess.run("printf LIBDATA > lib.txt", shell=True, cwd=d, check=True)
    r = condense(d, ["lib.txt"], os.path.join(d, ".reticuli", "liquid", "A"), name="A")
    return d, r


def test_condense_links_a_component_and_deps_shows_it(tmp_path):
    d, _ = _component_a(tmp_path)
    # a downstream session in the same registry: dep.txt == A's lib.txt output
    with open(os.path.join(d, "dep.txt"), "w") as f:
        f.write("LIBDATA")
    with open(os.path.join(d, "out.txt"), "w") as f:
        f.write("built\n")
    with open(os.path.join(d, ".reticuli", "vapor.jsonl"), "w") as f:
        for e in ({"event": "read", "path": "dep.txt"},
                  {"event": "write", "path": "out.txt"},
                  {"event": "bash", "cmd": "cat out.txt dep.txt > result.txt"}):
            f.write(json.dumps(e) + "\n")
    subprocess.run("cat out.txt dep.txt > result.txt", shell=True, cwd=d, check=True)
    r = condense(d, ["out.txt", "result.txt"], os.path.join(d, ".reticuli", "liquid", "B"), name="B")
    assert r["ok"]
    assert any(c["component"] == "A" and c["input"] == "dep.txt" for c in r["components"])

    b = next(n for n in registry.deps(d)["records"] if n["name"] == "B")
    assert any(e["component"] == "A" and e["status"] == "ok" for e in b["depends_on"])


def test_pull_registers_and_materializes(tmp_path):
    d, ra = _component_a(tmp_path)
    dst = str(tmp_path / "consumer")
    os.makedirs(os.path.join(dst, ".reticuli"))
    r = registry.pull(ra["into"], dst)
    assert r["component"] == "A" and "lib.txt" in r["materialized"]
    assert os.path.isfile(os.path.join(dst, "lib.txt"))
    assert any(x["name"] == "A" for x in registry.records(dst))
