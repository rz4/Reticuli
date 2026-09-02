"""Attestation: a keyholder's signed statement of a realization — signs only
fresh records, refuses tampered statements, anchors identity to allowed
signers, and never enters the root."""
import os
import subprocess

import pytest

from reticuli import attest, kernel

RECIPE = ('[record]\nname = "g"\n\n[[step]]\nkind = "produce"\noutput = "g.txt"\n'
          'request = "hi"\nclass = "free"\n\n[[step]]\nkind = "gate"\noutput = "V"\n'
          'run = "grep -qi hi g.txt && printf v > V"\nclass = "validated"\n')


def _realized(tmp_path) -> str:
    src = str(tmp_path / "src")
    os.makedirs(src)
    with open(os.path.join(src, "reticuli.toml"), "w") as f:
        f.write(RECIPE)
    m3 = str(tmp_path / "m3")
    kernel.realize(src, "printf 'hi there\\n' > g.txt", m3)
    return m3


def _key(tmp_path) -> str:
    key = str(tmp_path / "key")
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", key], check=True)
    return key


def test_attest_signs_and_check_verifies(tmp_path):
    m3, key = _realized(tmp_path), _key(tmp_path)
    a = attest.attest(m3, key, "tester@example")
    assert os.path.isfile(os.path.join(m3, a["statement"]))
    assert os.path.isfile(os.path.join(m3, a["signature"]))
    r = attest.check(m3)                       # no signers: intact, root named
    assert r["ok"] and r["attestations"][0]["verdict"] == "intact"
    assert kernel.verify(m3)["ok"], "the attestation never enters the root"


def test_identity_anchored_to_allowed_signers(tmp_path):
    m3, key = _realized(tmp_path), _key(tmp_path)
    attest.attest(m3, key, "tester@example")
    signers = str(tmp_path / "allowed_signers")
    with open(key + ".pub") as f:
        keytype, blob = f.read().split()[:2]
    with open(signers, "w") as f:
        f.write(f"tester@example {keytype} {blob}\n")
    r = attest.check(m3, signers)
    assert r["ok"] and r["attestations"][0]["verdict"] == "signed"
    with open(signers, "w") as f:                       # the wrong trust anchor
        f.write(f"someone-else {keytype} {blob}\n")
    assert not attest.check(m3, signers)["ok"]


def test_a_tampered_statement_refuses(tmp_path):
    m3, key = _realized(tmp_path), _key(tmp_path)
    a = attest.attest(m3, key, "tester@example")
    with open(os.path.join(m3, a["statement"]), "a") as f:
        f.write("\n")
    assert not attest.check(m3)["ok"]


def test_attest_refuses_a_broken_record(tmp_path):
    m3, key = _realized(tmp_path), _key(tmp_path)
    with open(os.path.join(m3, "V"), "w") as f:
        f.write("tampered")
    with pytest.raises(kernel.ReticuliError, match="refusing to sign"):
        attest.attest(m3, key, "tester@example")
