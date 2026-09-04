"""Soundness: verdicts must be earned, not carried. These are the exact attacks
from the first external review — a fabricated M3 (copied record, scribbled free
output) and a post-realization tamper both share the root, and both must fail
audit, prove, and mint."""
import os
import shutil
import subprocess

from reticuli import kernel

RECIPE = ('[record]\nname = "g"\n\n[[step]]\nkind = "produce"\noutput = "answer.txt"\n'
          'request = "the answer"\nclass = "free"\n\n[[step]]\nkind = "gate"\noutput = "V"\n'
          'run = "grep -qx 42 answer.txt && printf ok > V"\nclass = "validated"\n')


def _chain(tmp_path):
    m1 = str(tmp_path / "m1")
    os.makedirs(m1)
    with open(os.path.join(m1, "reticuli.toml"), "w") as f:
        f.write(RECIPE)
    with open(os.path.join(m1, "answer.txt"), "w") as f:
        f.write("42\n")
    subprocess.run("grep -qx 42 answer.txt && printf ok > V", shell=True, cwd=m1, check=True)
    kernel.seal(m1)
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf '42\\n' > answer.txt", m3)
    return m1, m2, m3


def test_audit_accepts_earned_verdicts(tmp_path):
    m1, m2, m3 = _chain(tmp_path)
    for m in (m1, m2, m3):
        a = kernel.audit(m)
        assert a["ok"] and all(g["ok"] for g in a["gates"])
    assert kernel.three_machine(m1, m2, m3)["satisfied"]


def test_a_fabricated_m3_shares_the_root_but_does_not_prove(tmp_path):
    m1, m2, _ = _chain(tmp_path)
    fake = str(tmp_path / "m3_fake")
    shutil.copytree(m1, fake)
    with open(os.path.join(fake, "answer.txt"), "w") as f:
        f.write("fabricated, does not satisfy gate\n")
    assert kernel.verify(fake)["ok"], "identity alone cannot see it"
    assert not kernel.audit(fake)["ok"], "audit can"
    r = kernel.three_machine(m1, m2, fake)
    assert r["equivalence"] and not r["audited"]["M3"] and not r["satisfied"]
    assert not kernel.freeze_dry(m1, m2, fake)["proven"]
    assert kernel.phase(m1) == "liquid"


def test_post_realization_tamper_fails_audit(tmp_path):
    m1, m2, m3 = _chain(tmp_path)
    with open(os.path.join(m3, "answer.txt"), "w") as f:
        f.write("NOT THE ANSWER\n")
    assert kernel.verify(m3)["ok"]
    assert not kernel.three_machine(m1, m2, m3)["satisfied"]


def test_a_tampered_pin_fails_audit_too(tmp_path):
    m1, _, _ = _chain(tmp_path)
    with open(os.path.join(m1, "V"), "w") as f:
        f.write("forged")
    a = kernel.audit(m1)
    assert not a["fresh"] and not a["ok"]