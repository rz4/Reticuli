"""ret — the command line. The invariant is the three-machine test; every stdout
is a TOML fact sheet, a pandas-style table, or a tree.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

from . import condense as condense_mod
from . import kernel
from .render import emit, short, table, toml

# -- session setup (git-native) ---------------------------------------------


def _ensure(path: str, lines: list[str], made: list, label: str) -> None:
    content = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            content = f.read()
    missing = [ln for ln in lines if ln not in content]
    if missing:
        with open(path, "a", encoding="utf-8") as f:
            if content and not content.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing) + "\n")
        made.append({"path": label, "status": "updated" if content else "created"})


def init(project: str) -> dict:
    root = os.path.abspath(project)
    made: list = []
    os.makedirs(os.path.join(root, kernel.STORE), exist_ok=True)
    vapor = os.path.join(root, condense_mod.TRACE)
    if not os.path.exists(vapor):
        open(vapor, "w").close()
        made.append({"path": ".reticuli/vapor.jsonl", "status": "created"})
    _ensure(os.path.join(root, ".gitignore"),
            ["# Reticuli: history is local — never committed",
             ".reticuli/vapor.jsonl", ".reticuli/**/ledger.jsonl"], made, ".gitignore")
    _ensure(os.path.join(root, ".gitattributes"),
            ["# Reticuli: sealed bytes are binary — no text/CRLF conversion",
             ".reticuli/** -text"], made, ".gitattributes")
    return {"project": root, "files": made}


def run(cmd: str, workspace: str) -> int:
    root = os.path.abspath(workspace)
    trace = os.path.join(root, condense_mod.TRACE)
    os.makedirs(os.path.dirname(trace), exist_ok=True)
    print(f"ret run: {cmd}  (tracked -> {condense_mod.TRACE})", file=sys.stderr)
    proc = subprocess.run(cmd, shell=True, cwd=root, check=False,
                          env={**os.environ, "RETICULI": "1"})
    with open(trace, "a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "bash", "cmd": cmd, "ts": round(time.time(), 3)}) + "\n")
    return proc.returncode


# -- renderers (TOML | table) ------------------------------------------------


def _r_init(r: dict) -> None:
    print(f"# init {r['project']}")
    table(r["files"] or [{"path": "already set up", "status": ""}],
          ("status", "status"), ("path", "path"))
    print("# ready: work, `ret run` your checks, `ret condense` when it holds")


def _r_verify(r: dict) -> None:
    toml(("verify", {"name": r["name"], "phase": r["phase"],
                     "verdict": "fresh" if r["ok"] else "broken",
                     "root": r["root"], "recomputed": r["recomputed"]}))


def _r_realize(r: dict) -> None:
    toml(("rehydrate", {"name": r["name"], "root": short(r["root"]), "into": r["into"]}))


def _r_condense(r: dict) -> None:
    toml(("condense", {"verdict": "condensed", "name": r["name"],
                       "root": short(r["root"]), "into": r["into"]}))
    print("# git add this record to share it — identity is deterministic")


def _r_prove(r: dict) -> None:
    toml(("prove", {"satisfied": r["satisfied"], "integrity": r["integrity"],
                    "reuse": r["reuse"], "equivalence": r["equivalence"],
                    "minted_solid": r.get("minted")}))
    print()
    table([{"machine": m, "root": short(h)} for m, h in r["roots"].items()],
          ("machine", "machine"), ("root", "root"))


def _r_status(r: dict) -> None:
    if r["phase"] == "vapor":
        toml(("session", {"phase": "vapor", "workspace": r["workspace"],
                          "trace_events": r["trace_events"]}))
    else:
        toml(("record", {"name": r["name"], "phase": r["phase"],
                         "freshness": "fresh" if r["ok"] else "broken",
                         "root": short(r["root"])}))


def status(workspace: str) -> dict:
    ws = os.path.abspath(workspace)
    if kernel.phase(ws) == "vapor":
        trace = os.path.join(ws, condense_mod.TRACE)
        n = 0
        if os.path.isfile(trace):
            with open(trace, encoding="utf-8") as f:
                n = sum(1 for _ in f)
        return {"phase": "vapor", "workspace": ws, "trace_events": n}
    return kernel.verify(ws)


# -- dispatch ----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="ret",
        description="Sealed, reproducible records of model-assisted work. "
                    "The invariant is the three-machine test.")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<verb>")

    def add(name, **kw):
        return sub.add_parser(name, **kw)

    add("init", help="set up a git-native session").add_argument("project", nargs="?", default=".")
    q = add("run", help="run a command and record it in the trace")
    q.add_argument("command")
    q.add_argument("-C", "--workspace", default=".")
    q = add("condense", help="draft a record from the session and certify it cold")
    q.add_argument("session", nargs="?", default=".")
    q.add_argument("--accept", action="append", default=[], metavar="PATH", required=True)
    q.add_argument("--into", required=True)
    q.add_argument("--name", default=None)
    add("verify", help="does the record hold (recompute the root)").add_argument("record")
    q = add("realize", help="rehydrate: an independent redo in a clean room (M3)")
    q.add_argument("record")
    q.add_argument("--producer", required=True)
    q.add_argument("--into", required=True)
    q = add("prove", help="the three-machine test: root equality across M1, M2, M3")
    q.add_argument("m1"); q.add_argument("m2"); q.add_argument("m3")
    q.add_argument("--freeze-dry", action="store_true", help="promote M1 to solid on success")
    add("show", help="print the record's recipe (TOML)").add_argument("record")
    add("status", help="where you are: phase and freshness").add_argument("workspace", nargs="?", default=".")
    for name in ("verify", "realize", "prove", "condense", "status"):
        sub.choices[name].add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    j = getattr(args, "json", False)
    try:
        if args.cmd == "init":
            return emit(init(args.project), False, _r_init)
        if args.cmd == "run":
            return run(args.command, args.workspace)
        if args.cmd == "condense":
            r = condense_mod.condense(args.session, args.accept, args.into, args.name)
            return emit(r, j, _r_condense)
        if args.cmd == "verify":
            r = kernel.verify(args.record)
            emit(r, j, _r_verify)
            return 0 if r["ok"] else 1
        if args.cmd == "realize":
            return emit(kernel.realize(args.record, args.producer, args.into), j, _r_realize)
        if args.cmd == "prove":
            r = (kernel.freeze_dry if args.freeze_dry else kernel.three_machine)(args.m1, args.m2, args.m3)
            r.setdefault("minted", None)
            emit(r, j, _r_prove)
            return 0 if r["satisfied"] else 1
        if args.cmd == "show":
            from .render import dump_recipe
            print(dump_recipe(kernel.load_recipe(args.record)))
            return 0
        if args.cmd == "status":
            return emit(status(args.workspace), j, _r_status)
    except kernel.ReticuliError as e:
        print(f"ret: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
