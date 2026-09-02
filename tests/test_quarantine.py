"""Quarantine: a record's gates are not your shell — writes confined to the
room, the ledger records the jail, producers stay yours. Efficacy is claimed
where the platform has a jail; honesty is claimed everywhere."""
import json
import os

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

EVIL = RECIPE.replace("grep -qi hello greeting.txt && printf verified > VERIFIED",
                      "printf pwn > ../escape.txt && printf verified > VERIFIED")

BACKEND = kernel.jail("true", ".")[1]


def _src(d: str, recipe: str = RECIPE) -> str:
    os.makedirs(d)
    with open(os.path.join(d, "reticuli.toml"), "w") as f:
        f.write(recipe)
    return d


def test_off_is_honored(monkeypatch):
    monkeypatch.setenv("RETICULI_QUARANTINE", "off")
    assert kernel.jail("true", ".") == ("true", "off")


def test_the_ledger_records_the_jail(tmp_path):
    src = _src(str(tmp_path / "src"))
    m3 = str(tmp_path / "m3")
    kernel.realize(src, "printf 'hello there\\n' > greeting.txt", m3)
    with open(os.path.join(m3, kernel.LEDGER)) as f:
        gate = [json.loads(x) for x in f if '"gate"' in x][-1]
    assert gate["quarantine"] == BACKEND


@pytest.mark.skipif(BACKEND == "none", reason="no jail on this platform")
def test_an_escaping_gate_refuses(tmp_path):
    src = _src(str(tmp_path / "src"), EVIL)
    with pytest.raises(kernel.ReticuliError, match="redo failed"):
        kernel.realize(src, "printf 'hello jail\\n' > greeting.txt", str(tmp_path / "m3"))
    assert not (tmp_path / "escape.txt").exists()


@pytest.mark.skipif(BACKEND == "none", reason="no jail on this platform")
def test_require_is_satisfied_by_the_jail(tmp_path, monkeypatch):
    monkeypatch.setenv("RETICULI_QUARANTINE", "require")
    src = _src(str(tmp_path / "src"))
    m3 = str(tmp_path / "m3")
    kernel.realize(src, "printf 'hello again\\n' > greeting.txt", m3)
    assert kernel.verify(m3)["ok"]


@pytest.mark.skipif(BACKEND != "none", reason="a jail exists here")
def test_require_refuses_without_a_jail(tmp_path, monkeypatch):
    monkeypatch.setenv("RETICULI_QUARANTINE", "require")
    src = _src(str(tmp_path / "src"))
    with pytest.raises(kernel.ReticuliError, match="quarantine required"):
        kernel.realize(src, "printf 'hello\\n' > greeting.txt", str(tmp_path / "m3"))