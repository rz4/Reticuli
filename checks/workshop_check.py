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
bench conforms.

THE EXECUTION CONTRACT: the authoritative workshop gate runs JAILED (realize
jails every gate), so the suite's quarantine tests see the inherited-jail
condition (RETICULI_JAILED set → kernel.jail returns "inherited", not a wrapping
backend). A producer iterating UNJAILED tests a different environment and could
ship a suite that passes unjailed but fails jailed — the jail-seam, caught live
in run 3, where a regrown test hard-asserted backend=="seatbelt" and died under
the verdict's jail. So this check re-execs itself under the host jail when run
bare, setting the single well-known RETICULI_JAILED signal: the producer's test
environment is made equal to the verdict's, and a jail-fragile suite fails here,
visibly, during iteration rather than only at the final gate.
"""
import ast
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

_JAILED = "RETICULI_JAILED"          # the inherited-jail signal (a single well-known name)


def _rejail() -> None:
    """Judge the bench in the verdict's environment: if the host has a jail and
    we are not already inside one, re-exec this check under it with RETICULI_JAILED
    set, so the suite runs jailed whether the producer or the verdict invokes it.
    A single well-known name, so an independently regenerated kernel reads the
    same handshake (see rehydration 4). Jails do not nest."""
    if os.environ.get(_JAILED):
        return                                       # already judged inside a jail
    cwd = os.path.realpath(os.getcwd())
    tmp = os.path.join(cwd, ".ws-tmp")
    os.makedirs(tmp, exist_ok=True)
    env = {**os.environ, "TMPDIR": tmp, "HOME": tmp}
    argv = None
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        profile = ('(version 1)(allow default)(deny network*)(deny file-write*)'
                   f'(allow file-write* (subpath "{cwd}") (subpath "/dev"))')
        argv, env[_JAILED] = ["sandbox-exec", "-p", profile], "seatbelt"
    elif shutil.which("bwrap") and subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--unshare-net", "true"],
            capture_output=True, check=False).returncode == 0:
        argv = ["bwrap", "--ro-bind", "/", "/", "--dev-bind", "/dev", "/dev",
                "--proc", "/proc", "--bind", cwd, cwd, "--unshare-net",
                "--die-with-parent"]
        env[_JAILED] = "bubblewrap"
    if argv:
        os.execvpe(argv[0], argv + [sys.executable, os.path.abspath(__file__)], env)

SCRIPTS = ["scripts/selfrecord.py", "scripts/probe.py", "scripts/sweep.py",
           "scripts/envelope.py", "scripts/producer_claude.py",
           "scripts/producer_claude_agentic.py", "scripts/producer_openai.py",
           "scripts/producer_openai_agentic.py"]

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
    _rejail()
    battery()
    with open("WORKSHOP_OK", "w") as f:
        f.write("workshop-ok\n")
    print("workshop-ok")
