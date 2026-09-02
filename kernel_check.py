"""Kernel conformance gate — the fixed check that defines "a correct kernel".

This is the seed of the `kernel-core` component record. It imports the
(re)generated kernel and confirms it implements the invariant: seal + verify
hold, an independent redo lands on the *same root* (root = claim), the
three-machine test is satisfied — and is SOUND: verdicts must be earned, not
carried, so a fabricated machine that shares the root but whose gates cannot
reproduce its verdicts from its own bytes neither proves nor mints (audit).
Cost is accounted: a redo leaves a ledger (residue, outside the root), an
unmeasured machine is reported rather than failed, an incomparable redo fails
the test. And gates run in quarantine: where the platform has a jail, an
escaping gate refuses, and the ledger tells the truth about the jail either
way. Writes KERNEL_OK iff it conforms. Stdlib only, so it runs in any clean
room.

Any kernel that passes this check hashes to the same kernel-core root — the
basin of kernels is what the component *is*. The whole toolchain layers on top:
its own gate ([`whole_check.py`](whole_check.py)) certifies the CLI, condense,
registry, and render built over a conformant kernel.
"""
import json
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

        # soundness: the verdicts must be EARNED, not carried. Root equality is
        # identity; audit re-runs the gates against the bytes present, so a
        # fabricated M3 — M1 copied, free output scribbled over, gate failing —
        # shares the root yet must not prove, and must never mint solid.
        m3f = os.path.join(d, "m3f")
        shutil.copytree(m1, m3f)
        with open(os.path.join(m3f, "g.txt"), "w") as f:
            f.write("fabricated, does not satisfy the gate\n")
        rf = kernel.three_machine(m1, m2, m3f)
        assert rf["equivalence"] and not rf["audited"]["M3"], "audit sees through the root"
        assert not rf["satisfied"], "a carried verdict does not prove"
        assert not kernel.freeze_dry(m1, m2, m3f)["minted"], "and does not mint"
        assert kernel.audit(m3)["ok"] and not kernel.audit(m3f)["ok"], "audit is the deep check"

        # cost: the redo's ledger accounts the oracle call — residue, outside
        # the root (m1 has no ledger, m3 does, and they share a root above)
        assert os.path.isfile(os.path.join(m3, kernel.LEDGER)), "ledger written"
        assert kernel.cost(m3)["calls"] == 1, "cost totals the ledger"
        assert kernel.cost(m1) is None, "no event, no cost"
        assert r["cost"]["comparable"] is None, "unmeasured is reported, not failed"
        with open(os.path.join(m1, kernel.LEDGER), "w") as f:
            f.write('{"event": "oracle", "calls": 4}\n')       # a 4-call original
        rr = kernel.three_machine(m1, m2, m3)                  # vs the 1-call redo
        assert rr["cost"]["comparable"] is False and not rr["satisfied"], "cost gates the test"

        # quarantine: a record's gates are not your shell. The ledger tells the
        # truth about the jail; where one exists, an escaping gate refuses.
        backend = kernel.jail("true", m3)[1]
        with open(os.path.join(m3, kernel.LEDGER)) as f:
            gate_line = [json.loads(x) for x in f if '"gate"' in x][-1]
        assert gate_line["quarantine"] == backend, "the ledger records the jail"
        m1e = os.path.join(d, "m1e")
        os.makedirs(m1e)
        with open(os.path.join(m1e, "reticuli.toml"), "w") as f:
            f.write(FIXTURE.replace("grep -qi hello g.txt && printf v > V",
                                    "printf pwn > ../escape.txt && printf v > V"))
        if backend in ("seatbelt", "bubblewrap"):
            try:
                kernel.realize(m1e, "printf 'hello jail\\n' > g.txt", os.path.join(d, "m4"))
                raise AssertionError("an escaping gate must refuse")
            except kernel.ReticuliError:
                pass
            assert not os.path.exists(os.path.join(d, "escape.txt")), "nothing escaped"
        else:                                                  # no jail here: recorded, not hidden
            kernel.realize(m1e, "printf 'hello jail\\n' > g.txt", os.path.join(d, "m4"))
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    battery()
    with open("KERNEL_OK", "w") as f:
        f.write("kernel-ok\n")
    print("kernel-ok")
