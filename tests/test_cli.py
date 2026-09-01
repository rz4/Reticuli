"""The CLI: git-native init, and prove printing a TOML verdict."""
import os
import shutil
import subprocess

from reticuli import cli, kernel

RECIPE = ('[record]\nname = "g"\n\n[[step]]\nkind = "produce"\noutput = "g.txt"\n'
          'request = "hi"\nclass = "free"\n\n[[step]]\nkind = "gate"\noutput = "V"\n'
          'run = "grep -qi hi g.txt && printf v > V"\nclass = "validated"\n')


def _rec(d: str, greeting: str) -> str:
    os.makedirs(d)
    open(os.path.join(d, "reticuli.toml"), "w").write(RECIPE)
    open(os.path.join(d, "g.txt"), "w").write(greeting)
    subprocess.run("grep -qi hi g.txt && printf v > V", shell=True, cwd=d)
    kernel.seal(d)
    return d


def test_init_is_git_native(tmp_path):
    assert cli.main(["init", str(tmp_path)]) == 0
    assert ".reticuli/**/ledger.jsonl" in (tmp_path / ".gitignore").read_text()
    assert ".reticuli/** -text" in (tmp_path / ".gitattributes").read_text()
    assert (tmp_path / ".reticuli" / "vapor.jsonl").exists()


def test_prove_cli_reports_same_root(tmp_path, capsys):
    m1 = _rec(str(tmp_path / "m1"), "hi there\n")
    m2 = str(tmp_path / "m2"); shutil.copytree(m1, m2)
    m3 = str(tmp_path / "m3")
    kernel.realize(m1, "printf 'oh hi\\n' > g.txt", m3)
    code = cli.main(["prove", m1, m2, m3])
    out = capsys.readouterr().out
    assert code == 0 and "satisfied = true" in out


def test_verify_cli(tmp_path, capsys):
    rec = _rec(str(tmp_path / "m1"), "hi\n")
    assert cli.main(["verify", rec]) == 0
    assert "fresh" in capsys.readouterr().out
