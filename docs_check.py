"""Documentation conformance gate — the seed of the repo's whole self-record.

The contact rung is the documentation rung: what a stranger — developer or
agent, but always technical — needs to take the hand-off. Its stratum is the
README (a minute, no lies) and the guide (the depth). Both are free water; the
claim is what they must carry:

README — a hard word budget (350; ~60 comfortable human seconds), the real
install line, the one idea stated, the mark, a pointer to the guide, and no
verb named that the CLI does not have.

guide — deep enough for rigorous engineers and scientists (a word floor, not a
ceiling); EVERY verb the CLI exposes is documented (parsed live from --help,
so an undocumented verb fails here before it ships); the load-bearing concepts
are named; the public environment contract (the RETICULI_* variables a driver
or agent needs) is documented; every relative link resolves — residue
namespaces (experiments/, notes/, *.pdf) and identity-elsewhere files
(*_check.py) exempt; and the machine audience is served (--json is shown).

Editing the docs keeps the root; editing this check moves it. Writes VERIFIED
iff the hand-off is conformant. Stdlib only, so it runs in any clean room.
"""
import os
import re
import subprocess
import sys

BUDGET = 350                     # README words; ~60 comfortable seconds
GUIDE_FLOOR = 1500               # guide words; depth is the point
CONCEPTS = ["root = hash(", "three-machine", "audit", "quarantine", "attest",
            "basin", "ledger", "freeze-dr", "condense", "realize"]
ENV_CONTRACT = ["RETICULI_QUARANTINE", "RETICULI_JAILED", "RETICULI_USAGE",
                "RETICULI_MODEL", "RETICULI_AGENT_BUDGET"]
_ELSEWHERE = re.compile(r"experiments/|notes/|\.pdf$|_check\.py$")


def _help() -> str:
    r = subprocess.run([sys.executable, "-m", "reticuli", "--help"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "the CLI answers --help"
    return r.stdout


def _links_resolve(md: str) -> None:
    base = os.path.dirname(md)
    with open(md, encoding="utf-8") as f:
        text = f.read()
    for m in re.finditer(r"\]\(([^)#\s]+)\)", text):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:")) or _ELSEWHERE.search(t):
            continue
        assert os.path.exists(os.path.normpath(os.path.join(base, t))), \
            f"{md} links a ghost: {t}"


def battery() -> None:
    help_out = _help()

    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    words = len(readme.split())
    assert words <= BUDGET, f"README is {words} words; contact allows {BUDGET}"
    assert 'pip install "git+https://github.com/rz4/reticuli"' in readme, "the real install line"
    assert "root = hash(" in readme, "the one idea, stated"
    assert "three-machine" in readme, "the invariant, named"
    assert "logo.png" in readme, "the mark"
    assert "docs/guide.md" in readme, "a pointer to depth"
    for verb in set(re.findall(r"\bret ([a-z][a-z-]*)", readme)):
        assert verb in help_out, f"README names `ret {verb}` — no such verb"

    with open("docs/guide.md", encoding="utf-8") as f:
        guide = f.read()
    gwords = len(guide.split())
    assert gwords >= GUIDE_FLOOR, f"the guide is {gwords} words; the hand-off needs {GUIDE_FLOOR}+"
    # every verb the CLI exposes must be documented — parsed live, so a new
    # verb cannot ship undocumented
    exposed = set(re.findall(r"^\s{4}([a-z][a-z-]+)\s{2,}", help_out, re.MULTILINE))
    assert exposed, "could not parse the CLI's verb list"
    for verb in exposed:
        assert f"ret {verb}" in guide or f"`{verb}`" in guide, \
            f"the CLI exposes `{verb}` — the guide does not document it"
    for verb in set(re.findall(r"\bret ([a-z][a-z-]*)", guide)):
        assert verb in help_out, f"the guide names `ret {verb}` — no such verb"
    for c in CONCEPTS:
        assert c in guide, f"the guide must name the concept: {c!r}"
    for var in ENV_CONTRACT:
        assert var in guide, f"the public env contract must be documented: {var}"
    assert "--json" in guide, "the machine audience: --json is shown"

    for md in ("README.md", "docs/guide.md"):
        _links_resolve(md)


if __name__ == "__main__":
    battery()
    with open("VERIFIED", "w") as f:
        f.write("conformant\n")
    print("conformant")
