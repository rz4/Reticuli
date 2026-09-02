"""The cost ledger: realization cost is residue (a local ledger), never
identity, and prove carries the comparable-cost check — C3/C1 within the
claim's declared tolerance, gating the test only when both machines were
measured."""
import json
import os
import shutil
import subprocess
import tarfile

from reticuli import kernel, transfer
from reticuli.condense import condense

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


def _mk(d: str, greeting: str = "hello world\n", recipe: str = RECIPE) -> str:
    os.makedirs(d)
    with open(os.path.join(d, "reticuli.toml"), "w") as f:
        f.write(recipe)
    with open(os.path.join(d, "greeting.txt"), "w") as f:
        f.write(greeting)
    subprocess.run(GATE, shell=True, cwd=d, check=True)
    kernel.seal(d)
    return d


def test_realize_accounts_every_oracle_call(tmp_path):
    m1 = _mk(str(tmp_path / "m1"))
    m3 = str(tmp_path / "m3")
    r = kernel.realize(m1, "printf 'oh hello\\n' > greeting.txt", m3)
    assert os.path.isfile(os.path.join(m3, kernel.LEDGER))
    c = kernel.cost(m3)
    assert c["calls"] == 1 and c["seconds"] >= 0    # one produce step, timed
    assert r["cost"] == c                           # realize reports what it paid


def test_producer_reported_usage_lands_in_the_ledger(tmp_path):
    m1 = _mk(str(tmp_path / "m1"))
    producer = ("printf 'hello again\\n' > greeting.txt && "
                "printf '{\"tokens\": 7, \"usd\": 0.01}' > \"$RETICULI_USAGE\"")
    kernel.realize(m1, producer, str(tmp_path / "m3"))
    c = kernel.cost(str(tmp_path / "m3"))
    assert c["tokens"] == 7 and c["usd"] == 0.01


def test_prove_compares_cost_when_both_machines_measured(tmp_path):
    base = _mk(str(tmp_path / "base"))
    m1 = str(tmp_path / "m1")
    kernel.realize(base, "printf 'hello one\\n' > greeting.txt", m1)
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(base, "printf 'hello two\\n' > greeting.txt", m3)
    r = kernel.three_machine(m1, m2, m3)
    assert r["satisfied"] and r["cost"]["comparable"]
    assert r["cost"]["unit"] == "calls" and r["cost"]["ratio"] == 1.0


def test_cost_out_of_tolerance_fails_the_test(tmp_path):
    m1 = _mk(str(tmp_path / "m1"))
    for _ in range(5):
        kernel._ledger_add(m1, {"event": "oracle", "calls": 1})   # a 5-call original
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'hello cheap\\n' > greeting.txt", m3)   # a 1-call redo
    r = kernel.three_machine(m1, m2, m3)
    assert r["equivalence"] and r["cost"]["comparable"] is False   # same root, incomparable cost
    assert not r["satisfied"]
    assert not kernel.freeze_dry(m1, m2, m3)["minted"]


def test_the_claim_declares_its_own_tolerance(tmp_path):
    recipe = RECIPE.replace('name = "greet"', 'name = "greet"\ntolerance = 10.0')
    m1 = _mk(str(tmp_path / "m1"), recipe=recipe)
    for _ in range(5):
        kernel._ledger_add(m1, {"event": "oracle", "calls": 1})
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'hello wide\\n' > greeting.txt", m3)
    r = kernel.three_machine(m1, m2, m3)
    assert r["cost"] == {"unit": "calls", "c1": 5, "c3": 1, "ratio": 0.2,
                         "tolerance": 10.0, "comparable": True}
    assert r["satisfied"]


def test_unmeasured_cost_reports_but_does_not_gate(tmp_path):
    m1 = _mk(str(tmp_path / "m1"))                  # hand-sealed: no ledger
    m2 = str(tmp_path / "m2")
    shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'hello free\\n' > greeting.txt", m3)
    r = kernel.three_machine(m1, m2, m3)
    assert r["satisfied"] and r["cost"]["comparable"] is None
    assert "M1" in r["cost"]["note"]


def test_condense_accounts_the_traced_session(tmp_path):
    ws = str(tmp_path / "s")
    os.makedirs(os.path.join(ws, ".reticuli"))
    with open(os.path.join(ws, "answer.txt"), "w") as f:
        f.write("42\n")
    gate = "grep -qx 42 answer.txt && printf ok > OK"
    events = [{"event": "prompt", "text": "write the answer", "ts": 10.0},
              {"event": "write", "path": "answer.txt", "ts": 11.0},
              {"event": "prompt", "text": "check it", "ts": 12.0},
              {"event": "bash", "cmd": gate, "ts": 13.5}]
    with open(os.path.join(ws, ".reticuli", "vapor.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(e) for e in events) + "\n")
    subprocess.run(gate, shell=True, cwd=ws, check=True)
    rec = str(tmp_path / "rec")
    condense(ws, ["OK"], rec, name="answer")
    assert kernel.cost(rec) == {"calls": 2, "seconds": 3.5}   # two prompts, the trace span


def test_export_excludes_the_volatile_ledger(tmp_path):
    m1 = _mk(str(tmp_path / "m1"))
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'hello tar\\n' > greeting.txt", m3)
    tar = str(tmp_path / "m3.tar")
    transfer.export(m3, tar)
    with tarfile.open(tar) as t:
        names = t.getnames()
    assert ".reticuli/ledger.jsonl" not in names
    assert ".reticuli/manifest.json" in names
