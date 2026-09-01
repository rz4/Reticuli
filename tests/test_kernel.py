"""The invariant, tested with no dependencies: a greeting (free) checked by a
gate that emits a canonical verdict (pinned). Divergent greetings that pass the
same check share a root — the basin is the preimage of the root."""
import os
import shutil
import subprocess

import pytest

from reticuli import kernel

RECIPE = '''[record]
name = "greet"

[[step]]
kind = "produce"
output = "greeting.txt"
request = "write a greeting containing the word hello"
class = "free"

[[step]]
kind = "gate"
output = "VERIFIED"
run = "grep -qi hello greeting.txt && printf verified > VERIFIED"
class = "validated"
'''

GATE = "grep -qi hello greeting.txt && printf verified > VERIFIED"


def _mk(d: str, greeting: str) -> str:
    os.makedirs(d)
    with open(os.path.join(d, "reticuli.toml"), "w") as f:
        f.write(RECIPE)
    with open(os.path.join(d, "greeting.txt"), "w") as f:
        f.write(greeting)
    subprocess.run(GATE, shell=True, cwd=d, check=True)      # warm run -> VERIFIED
    return d


def test_seal_then_verify(tmp_path):
    d = _mk(str(tmp_path / "m1"), "hello world\n")
    kernel.seal(d)
    r = kernel.verify(d)
    assert r["ok"] and r["phase"] == "liquid"


def test_the_root_is_the_claim(tmp_path):
    m1 = _mk(str(tmp_path / "m1"), "hello world\n")
    kernel.seal(m1)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'why, hello!\\n' > greeting.txt", m3)
    # the free implementation diverges...
    assert kernel._hf(os.path.join(m1, "greeting.txt")) != kernel._hf(os.path.join(m3, "greeting.txt"))
    # ...but the claim (the root) is identical
    assert kernel.verify(m1)["root"] == kernel.verify(m3)["root"]


def test_three_machine_is_root_equality(tmp_path):
    m1 = _mk(str(tmp_path / "m1"), "hello there\n")
    kernel.seal(m1)
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)                        # byte-reuse
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'oh, hello\\n' > greeting.txt", m3)
    r = kernel.three_machine(m1, m2, m3)
    assert r["satisfied"] and r["reuse"] and r["equivalence"]
    assert len(set(r["roots"].values())) == 1     # all three share one root


def test_freeze_dry_promotes_to_solid(tmp_path):
    m1 = _mk(str(tmp_path / "m1"), "hello\n")
    kernel.seal(m1)
    m2 = str(tmp_path / "m2"); shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3"); kernel.realize(m1, "printf 'hello!\\n' > greeting.txt", m3)
    assert kernel.freeze_dry(m1, m2, m3)["minted"]
    assert kernel.phase(m1) == "solid"


def test_verify_detects_a_tampered_verdict(tmp_path):
    m1 = _mk(str(tmp_path / "m1"), "hello\n")
    kernel.seal(m1)
    with open(os.path.join(m1, "VERIFIED"), "w") as f:
        f.write("tampered")                                     # pinned output changed
    assert not kernel.verify(m1)["ok"]


def test_a_broken_gate_fails_the_redo(tmp_path):
    m1 = _mk(str(tmp_path / "m1"), "hello\n")
    kernel.seal(m1)
    with pytest.raises(kernel.ReticuliError, match="redo failed"):
        kernel.realize(m1, "printf 'goodbye\\n' > greeting.txt", str(tmp_path / "m3"))
