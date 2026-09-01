"""Kernel conformance gate — the fixed check that defines "a correct kernel".

This is the seed of the `kernel-core` component record. It imports the
(re)generated kernel and confirms it implements the invariant: seal + verify
hold, an independent redo lands on the *same root* (root = claim), and the
three-machine test is satisfied. Writes KERNEL_OK iff it conforms. Stdlib only,
so it runs in any clean room.

Any kernel that passes this check hashes to the same kernel-core root — the
basin of kernels is what the component *is*. The whole toolchain layers on top:
its own gate ([`whole_check.py`](whole_check.py)) certifies the CLI, condense,
registry, and render built over a conformant kernel.
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, ".")
from reticuli import kernel   # the kernel under test

FIXTURE = '''[record]
name = "fixture"

[[step]]
kind = "produce"
output = "g.txt"
request = "a greeting containing the word hello"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -qi hello g.txt && printf v > V"
class = "validated"
'''


def battery() -> None:
    d = tempfile.mkdtemp()
    try:
        m1 = os.path.join(d, "m1")
        os.makedirs(m1)
        with open(os.path.join(m1, "reticuli.toml"), "w") as f:
            f.write(FIXTURE)
        with open(os.path.join(m1, "g.txt"), "w") as f:
            f.write("hello, world\n")
        subprocess.run("grep -qi hello g.txt && printf v > V", shell=True, cwd=m1, check=True)
        kernel.seal(m1)
        assert kernel.verify(m1)["ok"], "seal/verify"

        m2 = os.path.join(d, "m2")
        shutil.copytree(m1, m2)                                  # byte-reuse
        m3 = os.path.join(d, "m3")
        kernel.realize(m1, "printf 'why, hello!\\n' > g.txt", m3)  # a different redo
        assert kernel.verify(m1)["root"] == kernel.verify(m3)["root"], "root is the claim"

        r = kernel.three_machine(m1, m2, m3)
        assert r["satisfied"] and len(set(r["roots"].values())) == 1, "three-machine"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("KERNEL_OK", "w") as f:
        f.write("kernel-ok\n")
    print("kernel-ok")
