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

THE EXECUTION CONTRACT: gates are judged *inside* a platform jail when the host
has one (sandbox-exec on darwin, bwrap on linux), and jails do not nest. The
environment variable RETICULI_JAILED means "you are already inside one" — a
conformant kernel must then inherit (run the gate unwrapped, record its
quarantine as inherited) rather than re-apply a sandbox, which would refuse.
To make a producer's test environment equal the verdict environment, this check
re-execs itself under the host jail when run bare — so a kernel that re-applies
fails here, visibly, not only at the final gate.

Any kernel that passes this check hashes to the same kernel-core root — the
basin of kernels is what the component *is*. The whole toolchain layers on top:
its own gate ([`surface_check.py`](surface_check.py)) certifies the CLI built
over a conformant kernel, rung by rung.
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

# A record WITH a dry seed — the acceptance criteria are part of the claim.
# Used to pin the deepest property of the invariant: the root is a function of
# the seed bytes. A kernel that hashes only its validated outputs passes the
# seedless FIXTURE yet fails here — which is exactly the hole a live redo fell
# into (a regrown kernel whose `verify` blesses a record whose check was edited).
SEEDED = '''[record]
name = "seeded"
inputs = ["spec.txt"]

[[step]]
kind = "produce"
output = "impl.txt"
request = "any implementation that satisfies the spec"
class = "free"

[[step]]
kind = "gate"
output = "V"
run = "grep -q PASS impl.txt && printf v > V"
class = "validated"
'''


def _rejail() -> None:
    """Judge in the verdict's environment: if the host has a jail and we are
    not already inside one, re-exec this check under it, RETICULI_JAILED set.
    Jails do not nest — a conformant kernel inherits, never re-applies."""
    if os.environ.get("RETICULI_JAILED"):
        return                                       # already judged inside a jail
    cwd = os.path.realpath(os.getcwd())
    tmp = os.path.join(cwd, ".kc-tmp")
    os.makedirs(tmp, exist_ok=True)
    env = {**os.environ, "TMPDIR": tmp}
    argv = None
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        profile = ('(version 1)(allow default)(deny network*)(deny file-write*)'
                   f'(allow file-write* (subpath "{cwd}") (subpath "/dev"))')
        argv, env["RETICULI_JAILED"] = ["sandbox-exec", "-p", profile], "seatbelt"
    elif shutil.which("bwrap") and subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--unshare-net", "true"],
            capture_output=True, check=False).returncode == 0:
        argv = ["bwrap", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev",
                "--proc", "/proc", "--bind", cwd, cwd, "--unshare-net",
                "--die-with-parent"]
        env["RETICULI_JAILED"] = "bubblewrap"
    if argv:
        os.execvpe(argv[0], argv + [sys.executable, os.path.abspath(__file__)], env)


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

        # the root is the CLAIM: it is a function of the dry seeds (the check),
        # and independent of the free outputs (the implementation). Editing a
        # free output must keep the root; editing a seed must move it AND break
        # identity. A kernel that omits the seeds from the root passes the
        # seedless fixture above but fails right here.
        s = os.path.join(d, "seeded")
        os.makedirs(s)
        with open(os.path.join(s, "reticuli.toml"), "w") as f:
            f.write(SEEDED)
        with open(os.path.join(s, "spec.txt"), "w") as f:
            f.write("acceptance criteria: v1\n")
        with open(os.path.join(s, "impl.txt"), "w") as f:
            f.write("PASS — implementation one\n")
        subprocess.run("grep -q PASS impl.txt && printf v > V", shell=True, cwd=s, check=True)
        kernel.seal(s)
        assert kernel.verify(s)["ok"], "seeded record seals"
        r_seed = kernel.verify(s)["root"]
        with open(os.path.join(s, "impl.txt"), "w") as f:      # a different free redo
            f.write("PASS — implementation two, wholly rewritten\n")
        vs = kernel.verify(s)
        assert vs["ok"] and vs["root"] == r_seed, "editing a free output keeps the root"
        with open(os.path.join(s, "spec.txt"), "w") as f:      # edit the claim itself
            f.write("acceptance criteria: v2 (stricter)\n")
        vs = kernel.verify(s)
        assert not vs["ok"] and vs["recomputed"] != r_seed, "editing a dry seed moves the claim"

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

        # comparability is a BAND ([1/tol, tol]), not equality: a redo that cost
        # 1.5x the original is comparable at the default tolerance. A kernel that
        # demands exact-equal cost passes the 4:1 case above yet fails here.
        # (last — it clobbers the ledgers it writes.)
        with open(os.path.join(m1, kernel.LEDGER), "w") as f:
            f.write('{"event": "oracle", "calls": 2}\n')       # a 2-call original
        with open(os.path.join(m3, kernel.LEDGER), "w") as f:
            f.write('{"event": "oracle", "calls": 3}\n')       # a 3-call redo -> 1.5x
        rb = kernel.three_machine(m1, m2, m3)
        assert rb["cost"]["comparable"] is True, "a 1.5x redo is comparable (a band, not equality)"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    _rejail()
    battery()
    with open("KERNEL_OK", "w") as f:
        f.write("kernel-ok\n")
    print("kernel-ok")
