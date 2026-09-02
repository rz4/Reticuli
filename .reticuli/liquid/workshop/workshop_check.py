"""Workshop conformance gate — the seed of the `workshop` rung.

The bench: the scripts that build, probe, and sweep the repo, and the pytest
suite. All of it is free water under a claim about PROPERTIES, not bytes:

- the suite must pass against the package it ships with;
- the suite must have TEETH — a kernel whose `seal` is deliberately killed must
  make it fail, so an empty or toothless suite cannot land in this basin (the
  mutation is an append-shadow redefinition, so it works on any realization of
  the kernel, however written);
- the tools must be present, syntactically sound, and the sweep must plan.

Knowledge discovered on the bench is ratified by promotion into the rung
checks; this gate keeps the bench alive and honest in between. One ambient
dependency is admitted: pytest on the host python. Writes WORKSHOP_OK iff the
bench conforms. Runs wherever the verdict runs (inside a jail included).
"""
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = ["scripts/selfrecord.py", "scripts/probe.py", "scripts/sweep.py",
           "scripts/envelope.py", "scripts/producer_claude.py",
           "scripts/producer_claude_agentic.py", "scripts/producer_openai.py",
           "scripts/lagrange.py"]


def _pytest(cwd: str) -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"],
                       cwd=cwd, capture_output=True, text=True, check=False,
                       env={**os.environ, "RETICULI": "1"})
    return r.returncode


def battery() -> None:
    # the suite passes against the package as it stands
    assert _pytest(".") == 0, "the suite must pass"

    # TEETH: shadow kernel.seal with a corpse; the suite must notice. An
    # append-redefinition breaks any realization without assuming its internals.
    tmp = tempfile.mkdtemp()
    try:
        shutil.copytree("reticuli", os.path.join(tmp, "reticuli"))
        shutil.copytree("tests", os.path.join(tmp, "tests"))
        with open(os.path.join(tmp, "reticuli", "kernel.py"), "a") as f:
            f.write("\n\ndef seal(*a, **k):  # workshop tooth\n"
                    "    raise RuntimeError('mutant kernel')\n")
        assert _pytest(tmp) != 0, "the suite has no teeth — a dead seal went unnoticed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # the tools: present, sound, and the sweep plans
    for s in SCRIPTS:
        assert os.path.isfile(s), f"missing tool: {s}"
        py_compile.compile(s, doraise=True)
    r = subprocess.run([sys.executable, "scripts/sweep.py"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0 and "sweep plan" in r.stdout, "the sweep must plan"


if __name__ == "__main__":
    battery()
    with open("WORKSHOP_OK", "w") as f:
        f.write("workshop-ok\n")
    print("workshop-ok")
