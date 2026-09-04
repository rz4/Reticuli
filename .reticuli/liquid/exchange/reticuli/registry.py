"""Composition — records become components.

A session's records live in `.reticuli/{liquid,solid}/<name>/`. A dry seed whose
bytes match a registry record's output is a **dependency**: content-addressed, so
it survives copies. `pull` brings a record in as seeds; `deps` draws the DAG.

Duality: `solid` is a record's view of itself; `dry` is a dependent's view of the
same record. A freeze-dried record is the archetypal dry seed.
"""
from __future__ import annotations

import os
import shutil

from . import kernel


def records(ws: str) -> list[dict]:
    """Sealed records in the session's liquid/solid drawers."""
    ws = os.path.abspath(ws)
    found: list[dict] = []
    for drawer in ("liquid", "solid"):
        base = os.path.join(ws, kernel.STORE, drawer)
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            rec = os.path.join(base, entry)
            if kernel.phase(rec) == "vapor":
                continue
            m = kernel.read_manifest(rec)
            found.append({"name": m["name"], "root": m["root"],
                          "phase": "solid" if m.get("proof") else "liquid",
                          "drawer": drawer,
                          "path": os.path.relpath(rec, ws).replace(os.sep, "/")})
    return found


def _index(ws: str) -> dict:
    """{output_hash: (component, root, output)} over every registry record."""
    idx: dict[str, tuple[str, str, str]] = {}
    for r in records(ws):
        rec = os.path.join(ws, r["path"])
        recipe = kernel.load_recipe(rec)
        for step in recipe.get("step", []):
            f = os.path.join(rec, step["output"])
            if os.path.isfile(f):
                idx.setdefault(kernel._hf(f), (r["name"], r["root"], step["output"]))
    return idx


def detect_components(ws: str, seeds: list[str]) -> list[dict]:
    """Content-match each dry seed against the registry: the components this
    record depends on."""
    idx = _index(ws)
    links = []
    for s in seeds:
        f = os.path.join(ws, s)
        if os.path.isfile(f):
            hit = idx.get(kernel._hf(f))
            if hit:
                links.append({"input": s, "component": hit[0], "root": hit[1], "output": hit[2]})
    return links


def pull(component: str, into: str = ".") -> dict:
    """Bring a sealed record into this session as a dependency: register it in
    the drawer and materialize its outputs as dry seeds a gate can read."""
    src = os.path.abspath(component)
    if kernel.phase(src) == "vapor":
        raise kernel.ReticuliError(f"pull: no record in {component}")
    m = kernel.read_manifest(src)
    name = m["name"]
    drawer = "solid" if m.get("proof") else "liquid"
    dst = os.path.join(os.path.abspath(into), kernel.STORE, drawer, name)
    if os.path.exists(dst):
        raise kernel.ReticuliError(f"pull: '{name}' is already in the registry ({drawer}/{name})")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst)
    recipe = kernel.load_recipe(src)
    materialized = []
    for step in recipe.get("step", []):
        f = os.path.join(src, step["output"])
        if os.path.isfile(f):
            kernel._copy(f, os.path.join(os.path.abspath(into), step["output"]))
            materialized.append(step["output"])
    return {"component": name, "root": m["root"], "drawer": drawer,
            "registered": os.path.relpath(dst, os.path.abspath(into)).replace(os.sep, "/"),
            "materialized": materialized}


def _registry_of(record: str) -> str:
    """The session whose drawers hold this record's components. A self-record
    hosts them in its *own* store (repo root: .reticuli/liquid/<component>); a
    record sitting in a drawer (<ws>/.reticuli/<drawer>/<name>) finds them three
    directories up."""
    p = os.path.abspath(record)
    for drawer in ("liquid", "solid"):
        if os.path.isdir(os.path.join(p, kernel.STORE, drawer)):
            return p
    ws = os.path.dirname(os.path.dirname(os.path.dirname(p)))
    return ws if os.path.isdir(os.path.join(ws, kernel.STORE)) else os.path.dirname(p)


def rehydrate(record: str, producer: str, into: str, ws: str | None = None) -> dict:
    """DAG-aware rehydrate: recursively regenerate a record *and its component
    dependencies*, bottom-up. Each component is rehydrated from its own recipe
    and its output threaded up as this record's seed — so the whole chain
    reproduces from the leaves, not just one layer. This is the layered
    self-host: rehydrate the kernel, thread it into the CLI, and so on.
    """
    record = os.path.abspath(record)
    into = os.path.abspath(into)
    ws = os.path.abspath(ws) if ws else _registry_of(record)
    manifest = kernel.read_manifest(record)
    seeds = set(kernel._seeds(kernel.load_recipe(record)))
    by_root = {r["root"]: os.path.join(ws, r["path"]) for r in records(ws)}

    seed_from: dict[str, str] = {}
    produce_from: dict[str, str] = {}
    rehydrated = []
    # group links by component — one component may supply several outputs, but is
    # rehydrated exactly once (into deps/<name>) and its outputs threaded up
    groups: dict[tuple, list] = {}
    for link in manifest.get("components", []):
        groups.setdefault((link["component"], link["root"]), []).append(link)
    for (name, root), links in groups.items():
        comp = by_root.get(root)
        if comp is None:
            raise kernel.ReticuliError(
                f"rehydrate: component {name}@{root[:12]}… not in registry")
        comp_into = os.path.join(into, kernel.STORE, "deps", name)
        # resumable: a dep already sealed at the expected root is reused, so an
        # interrupted rehydration never re-pays for completed rungs (prove/audit
        # still validates everything at the end)
        if (kernel.phase(comp_into) != "vapor"
                and kernel.read_manifest(comp_into)["root"] == root):
            sub = {"root": root}
        else:
            sub = rehydrate(comp, producer, comp_into, ws)       # recurse: leaf first
        rehydrated.append({"component": name, "root": sub["root"]})
        for link in links:
            src = os.path.join(comp_into, link["output"])
            # a link into a seed is pinned data; into a produce step it's free code
            (seed_from if link["input"] in seeds else produce_from)[link["input"]] = src

    # deps now live under into/.reticuli/deps — thread them into the record and seal
    result = kernel.realize(record, producer, into, seed_from=seed_from,
                            produce_from=produce_from, exist_ok=True)
    # carry the provenance forward: realize seals bare {name, root}, but a redo
    # of a composed record must keep the links it was rebuilt from (same root —
    # components are manifest metadata, outside the claim) so its anatomy is not
    # lost. Without this a rehydrated record's `ret tree` is a stump.
    if manifest.get("components"):
        kernel.seal(into, components=manifest["components"])
    result["rehydrated_components"] = rehydrated
    return result


def mint_root(record: str, ws: str | None = None) -> str:
    """The chain root: fold this record's mint over its components', bottom-up
    (leaf first), via kernel.mint_node. Solid identity binds the whole DAG — the
    kernel's mint is the genesis, and a change at any rung moves its mint and
    every mint above it, never one below. This composes the invariant's fold; it
    does not sign — authorization is the mint ceremony's job (attest.mint)."""
    record = os.path.abspath(record)
    ws = os.path.abspath(ws) if ws else _registry_of(record)
    m = kernel.read_manifest(record)
    by_root = {r["root"]: os.path.join(ws, r["path"]) for r in records(ws)}
    comp_roots = {link["root"] for link in m.get("components", [])}
    comp_mints = [mint_root(by_root[cr], ws) for cr in sorted(comp_roots) if cr in by_root]
    return kernel.mint_node(m["root"], kernel.realization_digest(record), comp_mints)


def anatomy(record: str, ws: str | None = None) -> dict:
    """The record lens: the chain of rungs, leaf-ward. Each rung shows its dry
    seeds (the claim), its own free stratum, the files its component supplies,
    and its pinned verdicts — the repo's structure as the record sees it."""
    record = os.path.abspath(record)
    ws = os.path.abspath(ws) if ws else _registry_of(record)
    by_root = {r["root"]: os.path.join(ws, r["path"]) for r in records(ws)}

    def node(d: str) -> dict:
        m = kernel.read_manifest(d)
        recipe = kernel.load_recipe(d)
        steps = recipe.get("step", [])
        supplied = {f for s in steps if s["kind"] == "produce" and "from" in s
                    for f in [kernel._out(s)]}
        groups: dict[tuple, list] = {}
        for link in m.get("components", []):
            groups.setdefault((link["component"], link["root"]), []).append(link["input"])
        n = {"name": m["name"], "root": m["root"],
             "phase": "solid" if m.get("proof") else "liquid",
             "seeds": kernel._seeds(recipe),
             "free": [kernel._out(s) for s in steps if s["kind"] == "produce"
                      and s.get("class") == "free" and kernel._out(s) not in supplied],
             "pins": [kernel._out(s) for s in steps
                      if s.get("class", "exact") != "free"],
             "components": []}
        for (name, root), files in groups.items():
            comp = by_root.get(root)
            n["components"].append({"component": name, "root": root,
                                    "files": sorted(set(files)),
                                    "rung": node(comp) if comp else None})
        return n

    return {"workspace": ws, "record": node(record)}


def deps(ws: str) -> dict:
    """The component DAG: each record's `components` provenance, with broken
    links (upstream no longer in the registry) flagged. Includes the workspace's
    own top-level record — a self-record layers on its drawer, but isn't in it."""
    ws = os.path.abspath(ws)
    recs = records(ws)
    if kernel.phase(ws) != "vapor":
        m = kernel.read_manifest(ws)
        if m["root"] not in {r["root"] for r in recs}:
            recs = [{"name": m["name"], "root": m["root"], "drawer": ".", "path": ".",
                     "phase": "solid" if m.get("proof") else "liquid"}] + recs
    roots = {r["root"] for r in recs}
    nodes = []
    for r in recs:
        m = kernel.read_manifest(ws if r["path"] == "." else os.path.join(ws, r["path"]))
        edges = [{"input": link["input"], "component": link["component"],
                  "root": link["root"], "status": "ok" if link["root"] in roots else "missing"}
                 for link in m.get("components", [])]
        nodes.append({"name": r["name"], "root": r["root"], "phase": r["phase"],
                      "depends_on": edges})
    return {"workspace": ws, "records": nodes}
