"""A project packs into a self-record that rehydrates to its own claim. The
implementation is free (editing it keeps the root); the check is a seed (editing
it changes the claim) — the check IS the claim."""
import os

from reticuli import kernel, pack


def _project(tmp_path) -> str:
    d = str(tmp_path / "proj")
    os.makedirs(os.path.join(d, "pkg"))
    with open(os.path.join(d, "pkg", "__init__.py"), "w") as f:
        f.write("VALUE = 42\n")
    with open(os.path.join(d, "check.py"), "w") as f:
        f.write("import sys; sys.path.insert(0, '.')\n"
                "from pkg import VALUE\n"
                "assert VALUE == 42\n"
                "open('OK', 'w').write('ok\\n')\n")
    return d


def _pack(d: str) -> dict:
    return pack.pack(d, "proj", ["pkg/*.py"], ["check.py"], "python3 check.py", "OK")


def test_pack_and_exact_self_rehydration(tmp_path):
    d = _project(tmp_path)
    assert _pack(d)["ok"] and kernel.verify(d)["ok"]
    m3 = str(tmp_path / "m3")
    kernel.realize(d, f'mkdir -p pkg && cp {d}/"$RETICULI_OUTPUT" "$RETICULI_OUTPUT"', m3)
    assert kernel.verify(m3)["root"] == kernel.verify(d)["root"]   # the exact fixpoint


def test_implementation_is_free_the_check_is_the_claim(tmp_path):
    d = _project(tmp_path)
    r0 = _pack(d)["root"]
    with open(os.path.join(d, "pkg", "__init__.py"), "a") as f:
        f.write("# a comment (free)\n")
    assert _pack(d)["root"] == r0                    # editing the implementation keeps the root
    with open(os.path.join(d, "check.py"), "a") as f:
        f.write("# a stricter check (a seed)\n")
    assert _pack(d)["root"] != r0                    # editing the check changes the claim
