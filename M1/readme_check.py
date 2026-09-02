"""Contact conformance gate — the seed of the repo's whole self-record.

The last rung before contact: the README. Its *consumability* is the claim —
the prose is free water. A conformant README is one a human reads in about a
minute and an agent can act on without being lied to: a hard word budget, the
real install line, the one idea stated, the mark, a pointer to depth, and no
verb named that the CLI does not actually have. Editing the README keeps the
root; editing this check moves it. Writes VERIFIED iff contact is conformant.
Stdlib only, so it runs in any clean room.
"""
import re
import subprocess
import sys

BUDGET = 350                     # words; ~60 comfortable seconds of human reading


def battery() -> None:
    with open("README.md", encoding="utf-8") as f:
        text = f.read()

    words = len(text.split())
    assert words <= BUDGET, f"README is {words} words; contact allows {BUDGET}"

    assert 'pip install "git+https://github.com/rz4/reticuli"' in text, "the real install line"
    assert "root = hash(" in text, "the one idea, stated"
    assert "three-machine" in text, "the invariant, named"
    assert "logo.png" in text, "the mark"
    assert "docs/guide.md" in text, "a pointer to depth"

    # no hallucinated verbs: everything `ret <verb>` names must exist in the CLI
    verbs = set(re.findall(r"\bret ([a-z][a-z-]*)", text))
    assert verbs, "contact shows the tool in use"
    r = subprocess.run([sys.executable, "-m", "reticuli", "--help"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "the CLI answers --help"
    for verb in verbs:
        assert verb in r.stdout, f"README names `ret {verb}` — the CLI has no such verb"


if __name__ == "__main__":
    battery()
    with open("VERIFIED", "w") as f:
        f.write("conformant\n")
    print("conformant")
