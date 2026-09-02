"""A record exports to a deterministic tar and imports back, verifying."""
import os
import subprocess

from reticuli import kernel, transfer

RECIPE = ('[record]\nname = "g"\n\n[[step]]\nkind = "gate"\noutput = "V"\n'
          'run = "printf ok > V"\nclass = "validated"\n')


def _rec(d: str) -> str:
    os.makedirs(d)
    with open(os.path.join(d, "reticuli.toml"), "w") as f:
        f.write(RECIPE)
    subprocess.run("printf ok > V", shell=True, cwd=d, check=True)
    kernel.seal(d)
    return d


def test_export_is_byte_deterministic(tmp_path):
    a = _rec(str(tmp_path / "a"))
    t1, t2 = str(tmp_path / "a1.tar"), str(tmp_path / "a2.tar")
    transfer.export(a, t1)
    transfer.export(a, t2)
    with open(t1, "rb") as f1, open(t2, "rb") as f2:
        assert f1.read() == f2.read()          # same record -> same bytes


def test_import_round_trip_verifies(tmp_path):
    a = _rec(str(tmp_path / "a"))
    tar = str(tmp_path / "a.tar")
    transfer.export(a, tar)
    r = transfer.import_(tar, str(tmp_path / "b"))
    assert r["ok"] and r["root"] == kernel.verify(a)["root"]
