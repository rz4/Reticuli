"""Toolchain conformance gate — the seed of the repo's whole self-record.

Layers on `kernel-core`: imports the full CLI surface (so a broken module fails
the gate, not just a broken kernel) and runs a functional condense -> verify ->
rehydrate cycle through the higher layers (condense, registry, render, feedback).
Writes VERIFIED iff the toolchain built over a conformant kernel is itself
conformant. Stdlib only, so it runs in any clean room.

The kernel it exercises is supplied by the kernel-core component (a `from`
produce step, free): `ret realize . --recursive` rehydrates kernel-core first,
threads its kernel up, then regrows the toolchain and runs this gate.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, ".")
import reticuli.__main__   # the CLI entrypoint
import reticuli.cli        # pulls condense, feedback, pack, registry, render, transfer
from reticuli import feedback, kernel, registry, render
from reticuli.condense import condense


def battery() -> None:
    # the CLI entrypoint is wired over the toolchain (validates both modules import)
    assert reticuli.__main__.main is reticuli.cli.main, "entrypoint"
    d = tempfile.mkdtemp()
    try:
        ws = os.path.join(d, "ws")
        os.makedirs(os.path.join(ws, ".reticuli"))
        with open(os.path.join(ws, "answer.txt"), "w") as f:
            f.write("42\n")
        gate = "grep -qx 42 answer.txt && printf ok > OK"
        events = [{"event": "write", "path": "answer.txt"}, {"event": "bash", "cmd": gate}]
        with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
            f.write("\n".join(json.dumps(e) for e in events) + "\n")
        subprocess.run(gate, shell=True, cwd=ws, check=True)

        # the pilot senses a checked session as condensable
        assert feedback.pilot(ws)["condensable"], "feedback"

        # condense certifies it cold; the record verifies
        rec = os.path.join(ws, ".reticuli", "liquid", "answer")
        assert condense(ws, ["OK"], rec, name="answer")["ok"], "condense"
        assert kernel.verify(rec)["ok"], "verify"

        # an independent redo with different work lands on the same root (the basin)
        m3 = os.path.join(d, "m3")
        kernel.realize(rec, "printf '42\\n' > answer.txt", m3)
        assert kernel.verify(m3)["root"] == kernel.verify(rec)["root"], "basin"

        # the registry sees the record; render shapes the root without error
        assert any(x["name"] == "answer" for x in registry.records(ws)), "registry"
        assert render.short(kernel.verify(rec)["root"]), "render"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("VERIFIED", "w") as f:
        f.write("conformant\n")
    print("conformant")
