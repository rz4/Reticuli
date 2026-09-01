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
from . import feedback as feedback_mod
from . import kernel
from . import pack as pack_mod
from . import registry as registry_mod
from . import transfer as transfer_mod
from .render import emit, short, table, toml, tree

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
                       "root": short(r["root"]), "into": r["into"]}),
         *[("[[depends_on]]", {"component": c["component"], "root": short(c["root"]),
                               "via": c["input"]}) for c in r.get("components", [])])
    print("# git add this record to share it — identity is deterministic")


def _r_records(r: dict) -> None:
    print(f"# records in {os.path.basename(r['workspace']) or r['workspace']}")
    table([{"name": x["name"], "phase": x["phase"], "drawer": x["drawer"],
            "root": short(x["root"]), "path": x["path"]} for x in r["records"]],
          ("name", "name"), ("phase", "phase"), ("drawer", "drawer"),
          ("root", "root"), ("path", "path"))


def _r_deps(r: dict) -> None:
    total = sum(len(n["depends_on"]) for n in r["records"])
    node = {"children": [
        {"label": f"{n['phase']:<7} {n['name']}  {short(n['root'])}",
         "children": [{"label": f"{e['input']}  ⇐  {e['component']}@{short(e['root'])}"
                       + ("" if e["status"] == "ok" else "  (missing)")}
                      for e in n["depends_on"]]}
        for n in r["records"]]}
    ws = os.path.basename(r["workspace"].rstrip(os.sep)) or r["workspace"]
    tree(f"deps  {ws}  ·  {len(r['records'])} record(s), {total} link(s)", node)


def _r_pull(r: dict) -> None:
    toml(("pull", {"component": r["component"], "root": short(r["root"]),
                   "drawer": r["drawer"], "registered": r["registered"],
                   "materialized": r["materialized"]}))


def _r_export(r: dict) -> None:
    toml(("export", {"tar": r["tar"], "members": r["members"]}))


def _r_import(r: dict) -> None:
    toml(("import", {"into": r["into"], "verdict": r["verdict"], "root": short(r["root"])}))


def _r_prove(r: dict) -> None:
    toml(("prove", {"satisfied": r["satisfied"], "integrity": r["integrity"],
                    "reuse": r["reuse"], "equivalence": r["equivalence"],
                    "minted_solid": r.get("minted")}))
    print()
    table([{"machine": m, "root": short(h)} for m, h in r["roots"].items()],
          ("machine", "machine"), ("root", "root"))


def _r_pack(r: dict) -> None:
    toml(("pack", {"name": r["name"], "root": short(r["root"]),
                   "produce": r["produce"], "seeds": r["seeds"]}))
    print("# sealed as a record — `ret verify .` holds; `ret realize .` regrows it")


def _r_status(r: dict) -> None:
    if r["phase"] != "vapor":
        toml(("record", {"name": r["name"], "phase": r["phase"],
                         "freshness": "fresh" if r["ok"] else "broken",
                         "root": short(r["root"])}))
        return
    print(f"# session {os.path.basename(r['session']) or r['session']}"
          f"  ~ vapor · {r['trace_events']} trace events")
    table([{"role": f["role"], "kind": f["kind"], "covered": f["covered"], "path": f["path"]}
           for f in r["files"]],
          ("role", "role"), ("kind", "kind"), ("covered", "covered"), ("path", "path"))
    print(f"# {r['nudge']}")


def _r_tree(r: dict) -> None:
    def gloss(f):
        tag = f"{f['role']}/{f['kind']}"
        return f"{f['path']}   {tag}" + ("" if f["covered"] else "  ✗ uncovered")
    node = {"children": [{"label": gloss(f)} for f in r["files"]]}
    ws = os.path.basename(r["session"].rstrip(os.sep)) or r["session"]
    tree(f"session {ws}  ~ vapor · {r['trace_events']} events", node)
    print(f"  {r['nudge']}")


def status(workspace: str) -> dict:
    ws = os.path.abspath(workspace)
    if kernel.phase(ws) == "vapor":
        return feedback_mod.pilot(ws)
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
    q.add_argument("--recursive", action="store_true",
                   help="DAG-aware: also rehydrate component dependencies, bottom-up")
    q = add("prove", help="the three-machine test: root equality across M1, M2, M3")
    q.add_argument("m1"); q.add_argument("m2"); q.add_argument("m3")
    q.add_argument("--freeze-dry", action="store_true", help="promote M1 to solid on success")
    add("show", help="print the record's recipe (TOML)").add_argument("record")
    q = add("pack", help="declare a project as a self-record (code free, check gated)")
    q.add_argument("name")
    q.add_argument("--produce", nargs="+", required=True, metavar="GLOB")
    q.add_argument("--seed", nargs="*", default=[], metavar="GLOB")
    q.add_argument("--gate", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("-C", "--root", default=".")
    add("records", help="the session's record drawer").add_argument("workspace", nargs="?", default=".")
    add("deps", help="the component DAG: which records depend on which").add_argument("workspace", nargs="?", default=".")
    q = add("pull", help="bring a record in as a dependency (dry seeds)")
    q.add_argument("component")
    q.add_argument("-C", "--into", default=".")
    q = add("export", help="pack a record into a deterministic tar")
    q.add_argument("record")
    q.add_argument("tar")
    q = add("import", help="unpack a record from a tar and verify it")
    q.add_argument("tar")
    q.add_argument("into")
    add("status", help="where you are: phase and freshness (or a session's progress)").add_argument("workspace", nargs="?", default=".")
    add("tree", help="the session through Reticuli's lens: dry/wet, covered/uncovered").add_argument("workspace", nargs="?", default=".")
    for name in ("verify", "realize", "prove", "condense", "pack", "records",
                 "deps", "pull", "export", "import", "status", "tree"):
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
            fn = registry_mod.rehydrate if args.recursive else kernel.realize
            return emit(fn(args.record, args.producer, args.into), j, _r_realize)
        if args.cmd == "prove":
            r = (kernel.freeze_dry if args.freeze_dry else kernel.three_machine)(args.m1, args.m2, args.m3)
            r.setdefault("minted", None)
            emit(r, j, _r_prove)
            return 0 if r["satisfied"] else 1
        if args.cmd == "show":
            from .render import dump_recipe
            print(dump_recipe(kernel.load_recipe(args.record)))
            return 0
        if args.cmd == "pack":
            r = pack_mod.pack(args.root, args.name, args.produce, args.seed, args.gate, args.output)
            return emit(r, j, _r_pack)
        if args.cmd == "records":
            ws = os.path.abspath(args.workspace)
            return emit({"workspace": ws, "records": registry_mod.records(ws)}, j, _r_records)
        if args.cmd == "deps":
            return emit(registry_mod.deps(args.workspace), j, _r_deps)
        if args.cmd == "pull":
            return emit(registry_mod.pull(args.component, args.into), j, _r_pull)
        if args.cmd == "export":
            return emit(transfer_mod.export(args.record, args.tar), j, _r_export)
        if args.cmd == "import":
            r = transfer_mod.import_(args.tar, args.into)
            emit(r, j, _r_import)
            return 0 if r["ok"] else 1
        if args.cmd == "status":
            return emit(status(args.workspace), j, _r_status)
        if args.cmd == "tree":
            return emit(feedback_mod.pilot(os.path.abspath(args.workspace)), j, _r_tree)
    except kernel.ReticuliError as e:
        print(f"ret: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
