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
import ast
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = ["scripts/selfrecord.py", "scripts/probe.py", "scripts/sweep.py",
           "scripts/envelope.py", "scripts/producer_claude.py",
           "scripts/producer_claude_agentic.py", "scripts/producer_openai.py"]

# import-safety: a tool's module body may only DEFINE — imports, constants, defs,
# the `if __name__ == "__main__"` guard, the docstring, and the sys.path bootstrap.
# All *work* belongs in main(). A producer runs the machine unjailed at realize
# time; the least it owes is a side-effect-free import, so a poisoned producer
# cannot exfiltrate merely by being imported (round two, workshop payload). This
# is a partial wall by design — it removes the import-time attack surface; malice
# on the invoked path is the ladder's problem, not a gate's.
_DEFINING = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
             ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_main_guard(node) -> bool:
    return (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__")


def _is_path_bootstrap(node) -> bool:
    """The one benign top-level call: sys.path.insert/append for in-tree imports."""
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    f = node.value.func
    return (isinstance(f, ast.Attribute) and f.attr in ("insert", "append")
            and isinstance(f.value, ast.Attribute) and f.value.attr == "path"
            and isinstance(f.value.value, ast.Name) and f.value.value.id == "sys")


def _import_offender(path: str) -> str | None:
    """The first top-level statement that does WORK, or None if the module only
    defines. A docstring, the main guard, and the path bootstrap are permitted."""
    with open(path, encoding="utf-8") as f:
        body = ast.parse(f.read()).body
    for node in body:
        if isinstance(node, _DEFINING) or _is_main_guard(node) or _is_path_bootstrap(node):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue                                          # module docstring
        return ast.dump(node)[:70]
    return None


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

    # the tools: present, sound, import-safe, and the sweep plans
    for s in SCRIPTS:
        assert os.path.isfile(s), f"missing tool: {s}"
        py_compile.compile(s, doraise=True)
        offender = _import_offender(s)
        assert offender is None, \
            f"{s} does work at import (top-level {offender}); confine it to main()"
    r = subprocess.run([sys.executable, "scripts/sweep.py"],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0 and "sweep plan" in r.stdout, "the sweep must plan"


if __name__ == "__main__":
    battery()
    with open("WORKSHOP_OK", "w") as f:
        f.write("workshop-ok\n")
    print("workshop-ok")
