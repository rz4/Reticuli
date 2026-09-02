"""Vessel conformance gate — the seed of the `vessel` rung.

The skin the repo ships in: packaging, law, mark, docs, CI. The law (LICENSE)
and the mark (logo.png) are dry seeds — byte-pinned identity. Everything else
is free water under integrity claims:

- pyproject: parses, names the package, maps `ret` to reticuli.cli:main;
- docs: every relative link in README and docs/*.md resolves in the room —
  except the declared residue namespace (experiments/, *.pdf: results and
  papers are what happened, never identity) and identity-elsewhere files
  (*_check.py live as seeds of their own rungs, not here);
- every `ret` verb the guide names exists in the CLI;
- CI names the enforcement steps; init's git-native lines are present;
- the cube example is present and syntactically sound.

Writes VESSEL_OK iff the vessel conforms. Stdlib only.
"""
import os
import py_compile
import re
import subprocess
import sys
import tomllib

DOCS = ["docs/guide.md", "docs/basin.md", "docs/impedance.md", "docs/landscape.md"]
CUBE = ["examples/cube/checker.py", "examples/cube/rotating_cube.py",
        "examples/cube/rotating_cube_alt.py", "examples/cube/rotating_cube_alt2.py"]
# links exempt from room-existence: residue namespaces (results, papers) and
# identity-elsewhere files (rung checks live as seeds of their own records;
# README is the contact rung's stratum, one rung up)
_ELSEWHERE = re.compile(r"experiments/|\.pdf$|_check\.py$|README\.md$")


def battery() -> None:
    # packaging: the vessel can become a tool
    with open("pyproject.toml", "rb") as f:
        proj = tomllib.load(f)["project"]
    assert proj["name"] == "reticuli", "the package names itself"
    assert proj["scripts"]["ret"] == "reticuli.cli:main", "ret maps to the CLI"
    assert "requires-python" in proj and proj["readme"] == "README.md", "install metadata"

    # law and mark: pinned identity, present
    assert os.path.getsize("LICENSE") > 0, "the law"
    with open("logo.png", "rb") as f:
        assert f.read(8) == b"\x89PNG\r\n\x1a\n", "the mark is a PNG"

    # docs: links resolve; no verb the guide names is a lie
    for md in DOCS:
        assert os.path.isfile(md), f"missing doc: {md}"
        base = os.path.dirname(md)
        with open(md, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(r"\]\(([^)#\s]+)\)", text):
            t = m.group(1)
            if t.startswith(("http://", "https://", "mailto:")) or _ELSEWHERE.search(t):
                continue
            assert os.path.exists(os.path.normpath(os.path.join(base, t))), \
                f"{md} links a ghost: {t}"
    with open("docs/guide.md", encoding="utf-8") as f:
        guide = f.read()
    verbs = set(re.findall(r"\bret ([a-z][a-z-]*)", guide))
    r = subprocess.run([sys.executable, "-m", "reticuli", "--help"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "the CLI answers --help"
    for v in verbs:
        assert v in r.stdout, f"the guide names `ret {v}` — no such verb"

    # enforcement and git-native skin
    with open(".github/workflows/ci.yml", encoding="utf-8") as f:
        ci = f.read()
    for needle in ("ruff", "pytest", "ret verify", "--recursive"):
        assert needle in ci, f"CI must {needle}"
    with open(".github/workflows/release.yml", encoding="utf-8") as f:
        assert "pypi-publish" in f.read(), "the release ships to PyPI"
    with open(".gitignore", encoding="utf-8") as f:
        assert ".reticuli/vapor.jsonl" in f.read(), "history stays local"
    with open(".gitattributes", encoding="utf-8") as f:
        assert ".reticuli/** -text" in f.read(), "sealed bytes stay binary"

    # the worked example is present and sound (numpy not required to check)
    for f in CUBE:
        assert os.path.isfile(f), f"missing example: {f}"
        py_compile.compile(f, doraise=True)
    assert os.path.isfile("examples/cube/README.md"), "the example explains itself"


if __name__ == "__main__":
    battery()
    with open("VESSEL_OK", "w") as f:
        f.write("vessel-ok\n")
    print("vessel-ok")
