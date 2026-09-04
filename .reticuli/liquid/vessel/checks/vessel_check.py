"""Vessel conformance gate — the seed of the `vessel` rung.

The skin the repo ships in: packaging, law, mark, CI, the git-native surface.
The law (LICENSE) and the mark (logo.png) are dry seeds — byte-pinned
identity. Everything else is free water under integrity claims:

- pyproject: parses, names the package, maps `ret` to reticuli.cli:main;
- CI names the enforcement steps; the release ships to PyPI;
- init's git-native lines are present in the skin.

Documentation is the contact rung's claim (docs_check); examples are residue.
Writes VESSEL_OK iff the vessel conforms. Stdlib only.
"""
import os
import re
import tomllib


def battery() -> None:
    # packaging: the vessel can become a tool
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    proj = pyproject["project"]
    assert proj["name"] == "reticuli", "the package names itself"
    assert proj["scripts"]["ret"] == "reticuli.cli:main", "ret maps to the CLI"
    assert "requires-python" in proj and proj["readme"] == "README.md", "install metadata"

    # the vessel is a ZERO-BUILD package, and its build must run no code. The
    # install path is `pip install git+https://…`, so a build hook or a setup.py
    # is arbitrary code on the installer's machine — root-invisible (pyproject is
    # free), and vessel_check parses without building, so nothing else catches it.
    # This is round two's separable vessel payload, walled: every honest vessel is
    # a plain hatchling declaration with no hooks, so the clause costs no width.
    backend = pyproject.get("build-system", {}).get("build-backend")
    assert backend == "hatchling.build", f"build-backend must be hatchling.build, not {backend!r}"
    assert not pyproject.get("tool", {}).get("hatch", {}).get("build", {}).get("hooks"), \
        "no build hooks — the build must run no code (root-invisible install-time execution)"
    for f in ("setup.py", "setup.cfg"):
        assert not os.path.exists(f), f"no {f} — declarative packaging only, no build-time code"

    # law and mark: pinned identity, present
    assert os.path.getsize("LICENSE") > 0, "the law"
    with open("logo.png", "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n", "the mark is a PNG"

    # enforcement and git-native skin
    with open(".github/workflows/ci.yml", encoding="utf-8") as f:
        ci = f.read()
    for needle in ("ruff", "pytest", "ret verify"):
        assert needle in ci, f"CI must {needle}"
    # the recursive redo must be RUN, not merely named: a bare `--recursive`
    # substring is satisfiable by a comment (the census caught exactly that), so
    # require it on an actual `ret realize` invocation.
    assert re.search(r"ret realize\b[^\n]*--recursive", ci), \
        "CI must run `ret realize --recursive`, not name it in a comment"
    with open(".github/workflows/release.yml", encoding="utf-8") as f:
        assert "pypi-publish" in f.read(), "the release ships to PyPI"
    with open(".gitignore", encoding="utf-8") as f:
        assert ".reticuli/vapor.jsonl" in f.read(), "history stays local"
    with open(".gitattributes", encoding="utf-8") as f:
        assert ".reticuli/** -text" in f.read(), "sealed bytes stay binary"


if __name__ == "__main__":
    battery()
    with open("VESSEL_OK", "w") as f:
        f.write("vessel-ok\n")
    print("vessel-ok")
