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


def _r_review(r: dict) -> None:
    toml(("review", {"name": r["name"], "root": short(r["root"]), "mint": short(r["mint"]),
                     "realization": short(r["realization_digest"]),
                     "fresh": r["fresh"], "audit": r["audit"]["ok"],
                     "gates": len(r["gates"]), "components": len(r["components"])}))
    print("# review the packet, then authorize: ret mint <rec> --key <ssh_key> --as you@lab")


def _r_mint(r: dict) -> None:
    toml(("mint", {"name": r["name"], "root": short(r["root"]), "mint": short(r["mint"]),
                   "identity": r["identity"], "ceremony": r["ceremony"],
                   "statement": r["statement"], "signature": r["signature"]}))
    print("# accountable authorization recorded — commit the mint/ pair to travel with the record")


def _r_mint_check(r: dict) -> None:
    toml(("mint", {"name": r["name"], "mint": short(r["mint"]), "authorized": r["ok"]}))
    print()
    table([{"identity": a["identity"], "verdict": a["verdict"],
            "chain_holds": a["chain_holds"], "packet_holds": a.get("packet_holds"),
            "proven": a.get("proven"), "ceremony": a["ceremony"]}
           for a in r["authorizations"]] or
          [{"identity": "(none)", "verdict": "", "chain_holds": None,
            "packet_holds": None, "proven": None, "ceremony": ""}],
          ("identity", "identity"), ("verdict", "verdict"),
          ("chain_holds", "chain_holds"), ("packet_holds", "packet_holds"),
          ("proven", "proven"), ("ceremony", "ceremony"))


def _r_export(r: dict) -> None:
    toml(("export", {"tar": r["tar"], "members": r["members"]}))


def _r_import(r: dict) -> None:
    toml(("import", {"into": r["into"], "verdict": r["verdict"], "root": short(r["root"])}))


def _r_prove(r: dict) -> None:
    c = r.get("cost") or {}
    toml(("prove", {"satisfied": r["satisfied"], "integrity": r["integrity"],
                    "reuse": r["reuse"], "equivalence": r["equivalence"],
                    "audited": all(r.get("audited", {}).values()) or False,
                    "cost": c.get("comparable"), "proven": r.get("proven")}),
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
    if r.get("drawer"):
        print()
        _r_deps(r["drawer"])


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

_DESC = """\
Sealed, reproducible records of model-assisted computation. Validity is the
three-machine test: M1 claim, M2 byte-copy, M3 independent redo, one root.

session (vapor):
    init        initialize a session store (.reticuli/) and git skin
    hooks       install agent hooks into .claude/settings.json
    status      print phase and freshness

author (vapor -> liquid, M1):
    run         run a command; append it to the session trace
    condense    draft a record from the trace, re-run gates cold, seal
    verify      recompute the root; compare with the sealed manifest

transfer (liquid, M2):
    export      write the record's declared content to a deterministic tar
    import      extract a tar into a new directory; verify the root
    audit       re-run gates in a scratch room; pinned outputs must reproduce

redo (liquid -> solid, M3):
    realize     rebuild free outputs with --producer in a clean room; seal
    prove       three-machine test over M1 M2 M3 (--freeze-dry: mint on pass)
    attest      sign with ssh-keygen -Y (--check: verify signatures)
    mint        review the chain and packet (no key), or authorize it (--key --as)

compose:
    pack        seal a project directory as a record (code free, checks claimed)
    pull        copy a sealed record into this session as a dependency
    tree        print session files and drawer graph, or a record's anatomy
    records     list sealed records"""

_EPILOG = ("`ret <verb> -h` for verb options. `ret hook` is internal, invoked by "
           "installed\nagent hooks. Documentation: docs/guide.md")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ret", description=_DESC, epilog=_EPILOG,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # verbs carry no parser-level help= — the sectioned map in _DESC is the one
    # listing (argparse only auto-lists verbs that set help=). Section order and
    # membership are structure, ratified by surface_check; the wording is free.
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<verb>")

    def add(name):
        return sub.add_parser(name)

    # -- session (vapor)
    add("init").add_argument("project", nargs="?", default=".")
    add("hooks").add_argument("project", nargs="?", default=".")
    add("status").add_argument("workspace", nargs="?", default=".")
    # -- author (M1)
    q = add("run")
    q.add_argument("command")
    q.add_argument("-C", "--workspace", default=".")
    q = add("condense")
    q.add_argument("session", nargs="?", default=".")
    q.add_argument("--accept", action="append", default=[], metavar="PATH", required=True)
    q.add_argument("--into", required=True)
    q.add_argument("--name", default=None)
    add("verify").add_argument("record")
    # -- transfer (M2)
    q = add("export")
    q.add_argument("record")
    q.add_argument("tar")
    q = add("import")
    q.add_argument("tar")
    q.add_argument("into")
    add("audit").add_argument("record")
    # -- redo (M3)
    q = add("realize")
    q.add_argument("record")
    q.add_argument("--producer", required=True)
    q.add_argument("--into", required=True)
    q.add_argument("--recursive", action="store_true",
                   help="DAG-aware: also rehydrate component dependencies, bottom-up")
    q = add("prove")
    q.add_argument("m1"); q.add_argument("m2"); q.add_argument("m3")
    q.add_argument("--freeze-dry", action="store_true", help="record the three-machine proof on M1 (residue; solid is the mint ceremony's)")
    q = add("attest")
    q.add_argument("record")
    q.add_argument("--key", default=None, metavar="SSH_KEY")
    q.add_argument("--as", dest="identity", default=None, metavar="IDENTITY")
    q.add_argument("--check", action="store_true")
    q.add_argument("--signers", default=None, metavar="ALLOWED_SIGNERS")
    q = add("mint")
    q.add_argument("record")
    q.add_argument("--key", default=None, metavar="SSH_KEY")
    q.add_argument("--as", dest="identity", default=None, metavar="IDENTITY")
    q.add_argument("--check", action="store_true")
    q.add_argument("--signers", default=None, metavar="ALLOWED_SIGNERS")
    # -- compose
    q = add("pack")
    q.add_argument("name")
    q.add_argument("--produce", nargs="+", required=True, metavar="GLOB")
    q.add_argument("--seed", nargs="*", default=[], metavar="GLOB")
    q.add_argument("--gate", required=True)
    q.add_argument("--output", required=True)
    q.add_argument("-C", "--root", default=".")
    q = add("pull")
    q.add_argument("component")
    q.add_argument("-C", "--into", default=".")
    add("tree").add_argument("workspace", nargs="?", default=".")
    add("records").add_argument("workspace", nargs="?", default=".")
    # -- internal: agent plumbing, invoked by installed hooks (unlisted)
    q = add("hook")
    q.add_argument("-C", "--workspace", default=None)

    for name in ("verify", "audit", "realize", "prove", "condense", "pack", "records",
                 "pull", "export", "import", "status", "tree", "hooks", "attest", "mint"):
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
            r.setdefault("proven", None)
            emit(r, j, _r_prove)
            return 0 if r["satisfied"] else 1
        if args.cmd == "pack":
            r = pack_mod.pack(args.root, args.name, args.produce, args.seed, args.gate, args.output)
            return emit(r, j, _r_pack)
        if args.cmd == "records":
            ws = os.path.abspath(args.workspace)
            return emit({"workspace": ws, "records": registry_mod.records(ws)}, j, _r_records)
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
        if args.cmd == "mint":
            if args.check:
                r = attest_mod.mint_check(args.record)
                emit(r, j, _r_mint_check)
                return 0 if r["ok"] else 1
            if not args.key or not args.identity:      # review, don't authorize
                return emit(attest_mod.review_packet(args.record), j, _r_review)
            return emit(attest_mod.mint(args.record, args.key, args.identity), j, _r_mint)
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
                r = feedback_mod.pilot(ws)
                if registry_mod.records(ws):        # deps folded in: the drawer's DAG
                    r["drawer"] = registry_mod.deps(ws)
                return emit(r, j, _r_tree)
            return emit(registry_mod.anatomy(ws), j, _r_anatomy)
    except kernel.ReticuliError as e:
        print(f"ret: {e}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
