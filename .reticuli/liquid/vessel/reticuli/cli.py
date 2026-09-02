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

from . import attest as attest_mod
from . import condense as condense_mod
from . import feedback as feedback_mod
from . import hooks as hooks_mod
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
             ".reticuli/vapor.jsonl", ".reticuli/**/ledger.jsonl",
             ".reticuli/**/tmp/"], made, ".gitignore")
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


def _r_attest(r: dict) -> None:
    toml(("attest", {"name": r["name"], "root": short(r["root"]),
                     "identity": r["identity"], "statement": r["statement"],
                     "signature": r["signature"]}))
    print("# commit the pair — the attestation travels with the record")


def _r_attest_check(r: dict) -> None:
    toml(("attest", {"name": r["name"], "root": short(r["root"]),
                     "fresh": r["fresh"], "attested": r["ok"]}))
    print()
    table([{"identity": a["identity"], "verdict": a["verdict"],
            "root_match": a["root_match"], "when": a["when"]}
           for a in r["attestations"]] or
          [{"identity": "(none)", "verdict": "", "root_match": None, "when": ""}],
          ("identity", "identity"), ("verdict", "verdict"),
          ("root_match", "root_match"), ("when", "when"))


def _r_hooks(r: dict) -> None:
    toml(("hooks", {"settings": r["settings"], "status": r["status"],
                    "wired": r["wired"] or None}))
    print("# needs `ret` on PATH; events flow once a session exists (`ret init`)")


def _r_verify(r: dict) -> None:
    toml(("verify", {"name": r["name"], "phase": r["phase"],
                     "verdict": "fresh" if r["ok"] else "broken",
                     "root": r["root"], "recomputed": r["recomputed"]}))


def _r_audit(r: dict) -> None:
    toml(("audit", {"name": r["name"], "root": short(r["root"]), "fresh": r["fresh"],
                    "verdict": "earned" if r["ok"] else "carried or broken"}))
    print()
    table([{"gate": g["output"], "reproduced": g["ok"], "quarantine": g["quarantine"]}
           for g in r["gates"]] or [{"gate": "(none)", "reproduced": None, "quarantine": ""}],
          ("gate", "gate"), ("reproduced", "reproduced"), ("quarantine", "quarantine"))


def _r_realize(r: dict) -> None:
    c = r.get("cost") or {}
    toml(("rehydrate", {"name": r["name"], "root": short(r["root"]), "into": r["into"],
                        "calls": c.get("calls"), "seconds": c.get("seconds"),
                        "tokens": c.get("tokens"), "usd": c.get("usd")}))


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
    c = r.get("cost") or {}
    toml(("prove", {"satisfied": r["satisfied"], "integrity": r["integrity"],
                    "reuse": r["reuse"], "equivalence": r["equivalence"],
                    "audited": all(r.get("audited", {}).values()) or False,
                    "cost": c.get("comparable"), "minted_solid": r.get("minted")}),
         ("cost", {k: c.get(k) for k in ("unit", "c1", "c3", "ratio", "tolerance", "note")}))
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


def _r_anatomy(r: dict) -> None:
    def nodeify(n):
        kids = [{"label": f"seed  {s}   (the claim)"} for s in n["seeds"]]
        kids += [{"label": f"free  {f}"} for f in n["free"]]
        for c in n["components"]:
            kids.append({"label": f"{len(c['files'])} file(s)  ⇐  "
                                  f"{c['component']}@{short(c['root'])}"})
        kids += [{"label": f"pin   {p}   (the verdict)"} for p in n["pins"]]
        for c in n["components"]:
            if c["rung"]:
                kids.append({"label": f"rung  {c['rung']['name']}  "
                                      f"{short(c['rung']['root'])}  · {c['rung']['phase']}",
                             "children": nodeify(c["rung"])})
            else:
                kids.append({"label": f"rung  {c['component']}@{short(c['root'])}"
                                      "  (missing from the registry)"})
        return kids

    def count(n):
        return 1 + sum(count(c["rung"]) for c in n["components"] if c["rung"])

    rec = r["record"]
    tree(f"record {rec['name']}  {short(rec['root'])}  · {rec['phase']}"
         f" · {count(rec)} rung(s), contact to leaf", {"children": nodeify(rec)})


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
    q = add("hook", help="consume one agent hook payload from stdin (silent; wired by `ret hooks`)")
    q.add_argument("-C", "--workspace", default=None)
    add("hooks", help="wire the project's agent to the trace (.claude/settings.json)") \
        .add_argument("project", nargs="?", default=".")
    q = add("run", help="run a command and record it in the trace")
    q.add_argument("command")
    q.add_argument("-C", "--workspace", default=".")
    q = add("condense", help="draft a record from the session and certify it cold")
    q.add_argument("session", nargs="?", default=".")
    q.add_argument("--accept", action="append", default=[], metavar="PATH", required=True)
    q.add_argument("--into", required=True)
    q.add_argument("--name", default=None)
    add("verify", help="does the record hold (recompute the root — identity only)").add_argument("record")
    add("audit", help="re-run the gates against the bytes present — verdicts must reproduce") \
        .add_argument("record")
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
    q = add("attest", help="sign a realization with ssh-keygen -Y (or --check its attestations)")
    q.add_argument("record")
    q.add_argument("--key", default=None, metavar="SSH_KEY")
    q.add_argument("--as", dest="identity", default=None, metavar="IDENTITY")
    q.add_argument("--check", action="store_true")
    q.add_argument("--signers", default=None, metavar="ALLOWED_SIGNERS")
    q = add("export", help="pack a record into a deterministic tar")
    q.add_argument("record")
    q.add_argument("tar")
    q = add("import", help="unpack a record from a tar and verify it")
    q.add_argument("tar")
    q.add_argument("into")
    add("status", help="where you are: phase and freshness (or a session's progress)").add_argument("workspace", nargs="?", default=".")
    add("tree", help="the workspace through Reticuli's lens: a session's dry/wet, "
                     "or a sealed record's rungs (seeds, strata, verdicts)") \
        .add_argument("workspace", nargs="?", default=".")
    for name in ("verify", "audit", "realize", "prove", "condense", "pack", "records",
                 "deps", "pull", "export", "import", "status", "tree", "hooks", "attest"):
        sub.choices[name].add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    j = getattr(args, "json", False)
    try:
        if args.cmd == "init":
            return emit(init(args.project), False, _r_init)
        if args.cmd == "hook":
            hooks_mod.consume(args.workspace)   # silent: hook stdout can leak into the agent
            return 0
        if args.cmd == "hooks":
            return emit(hooks_mod.install(args.project), j, _r_hooks)
        if args.cmd == "run":
            return run(args.command, args.workspace)
        if args.cmd == "condense":
            r = condense_mod.condense(args.session, args.accept, args.into, args.name)
            return emit(r, j, _r_condense)
        if args.cmd == "verify":
            r = kernel.verify(args.record)
            emit(r, j, _r_verify)
            return 0 if r["ok"] else 1
        if args.cmd == "audit":
            r = kernel.audit(args.record)
            emit(r, j, _r_audit)
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
        if args.cmd == "attest":
            if args.check:
                r = attest_mod.check(args.record, args.signers)
                emit(r, j, _r_attest_check)
                return 0 if r["ok"] else 1
            if not args.key or not args.identity:
                print("ret: attest needs --key and --as (or --check)", file=sys.stderr)
                return 2
            return emit(attest_mod.attest(args.record, args.key, args.identity), j, _r_attest)
        if args.cmd == "export":
            return emit(transfer_mod.export(args.record, args.tar), j, _r_export)
        if args.cmd == "import":
            r = transfer_mod.import_(args.tar, args.into)
            emit(r, j, _r_import)
            return 0 if r["ok"] else 1
        if args.cmd == "status":
            return emit(status(args.workspace), j, _r_status)
        if args.cmd == "tree":
            ws = os.path.abspath(args.workspace)
            if kernel.phase(ws) == "vapor":
                return emit(feedback_mod.pilot(ws), j, _r_tree)
            return emit(registry_mod.anatomy(ws), j, _r_anatomy)
    except kernel.ReticuliError as e:
        print(f"ret: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
