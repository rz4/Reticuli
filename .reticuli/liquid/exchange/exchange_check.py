"""Exchange conformance gate — the seed of the `exchange` layer.

Records meeting records — and other parties: the registry (drawers,
content-addressed component links, DAG-aware rehydrate), transfer
(deterministic tar, verify-on-import, volatile history stays home), and
attestation (a keyholder's signed statement of a realization: signs only fresh
records, refuses tampered statements, anchors identity to allowed signers).
Layers on kernel-core; knows nothing of authoring or the CLI. Writes
EXCHANGE_OK iff the layer conforms. Stdlib only, so it runs in any clean room.
"""
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, ".")
from reticuli import attest, kernel, registry, transfer

LIB = '''[record]
name = "lib"

[[step]]
kind = "gate"
output = "lib.txt"
run = "printf LIBDATA > lib.txt"
class = "validated"
'''

APP = '''[record]
name = "app"
inputs = ["dep.txt"]

[[step]]
kind = "produce"
output = "app.txt"
request = "any note"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -q LIBDATA dep.txt && cat app.txt >/dev/null && printf ok > V"
class = "validated"
'''


def _write(d: str, files: dict) -> None:
    os.makedirs(d, exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(d, name), "w") as f:
            f.write(content)


def battery() -> None:
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        lib = os.path.join(ws, ".reticuli", "liquid", "lib")
        _write(lib, {"reticuli.toml": LIB, "lib.txt": "LIBDATA"})
        kernel.seal(lib)

        # a dry seed that content-matches a record's output is a dependency
        _write(ws, {"dep.txt": "LIBDATA"})
        links = registry.detect_components(ws, ["dep.txt"])
        assert any(x["component"] == "lib" for x in links), "content-addressed link"

        app = os.path.join(ws, ".reticuli", "liquid", "app")
        _write(app, {"reticuli.toml": APP, "dep.txt": "LIBDATA",
                     "app.txt": "one implementation\n", "V": "ok"})
        kernel.seal(app, components=links)
        names = {r["name"] for r in registry.records(ws)}
        assert names == {"app", "lib"}, "the drawer"
        edges = registry.deps(ws)["records"]
        assert any(e["status"] == "ok" for n in edges for e in n["depends_on"]), "the DAG"

        # DAG-aware rehydrate: the chain reproduces from the leaves
        m3 = os.path.join(d, "m3")
        out = registry.rehydrate(app, "printf 'another implementation' > app.txt", m3, ws=ws)
        assert out["root"] == kernel.verify(app)["root"], "chain reproduces"
        assert any(c["component"] == "lib" for c in out["rehydrated_components"]), "leaf first"

        # pull: a record becomes a dependency of a fresh session
        ws2 = os.path.join(d, "ws2")
        os.makedirs(ws2)
        pulled = registry.pull(app, ws2)
        assert pulled["materialized"] and os.path.isfile(os.path.join(ws2, "V")), "pull"

        # transfer: deterministic tar, verify-on-import, ledger stays home
        tar_path = os.path.join(d, "m3.tar")
        transfer.export(m3, tar_path)
        with tarfile.open(tar_path) as t:
            assert ".reticuli/ledger.jsonl" not in t.getnames(), "events don't travel"
        back = transfer.import_(tar_path, os.path.join(d, "back"))
        assert back["ok"] and back["root"] == out["root"], "identity travels"

        # attestation: a signed statement of this realization, for other parties
        key = os.path.join(d, "key")
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", key], check=True)
        a = attest.attest(m3, key, "checker@basin")
        assert os.path.isfile(os.path.join(m3, a["signature"])), "signed"
        assert attest.check(m3)["ok"], "intact and naming this root"
        signers = os.path.join(d, "allowed_signers")
        with open(key + ".pub") as f:
            keytype, blob = f.read().split()[:2]
        with open(signers, "w") as f:
            f.write(f"checker@basin {keytype} {blob}\n")
        checked = attest.check(m3, signers)
        assert checked["ok"] and checked["attestations"][0]["verdict"] == "signed", "identity anchored"
        st_path = os.path.join(m3, a["statement"])
        with open(st_path, "a") as f:
            f.write("\n")                                        # tamper the statement
        assert not attest.check(m3, signers)["ok"], "a tampered statement refuses"
        imported = os.path.join(d, "back")
        with open(os.path.join(imported, "V"), "w") as f:
            f.write("tampered")                                  # break the imported copy
        try:
            attest.attest(imported, key, "checker@basin")
            raise AssertionError("attest must refuse a broken record")
        except kernel.ReticuliError:
            pass
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("EXCHANGE_OK", "w") as f:
        f.write("exchange-ok\n")
    print("exchange-ok")
