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
    """The session whose .reticuli/{liquid,solid} holds this record: a record at
    <ws>/.reticuli/<drawer>/<name> is three directories below <ws>."""
    p = os.path.abspath(record)
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
    by_root = {r["root"]: os.path.join(ws, r["path"]) for r in records(ws)}

    seed_from: dict[str, str] = {}
    rehydrated = []
    for link in manifest.get("components", []):
        comp = by_root.get(link["root"])
        if comp is None:
            raise kernel.ReticuliError(
                f"rehydrate: component {link['component']}@{link['root'][:12]}… not in registry")
        comp_into = os.path.join(into, kernel.STORE, "deps", link["component"])
        sub = rehydrate(comp, producer, comp_into, ws)           # recurse: leaf first
        rehydrated.append({"component": link["component"], "root": sub["root"]})
        seed_from[link["input"]] = os.path.join(comp_into, link["output"])

    # deps now live under into/.reticuli/deps — seed the record from them and seal
    result = kernel.realize(record, producer, into, seed_from=seed_from, exist_ok=True)
    result["rehydrated_components"] = rehydrated
    return result


def deps(ws: str) -> dict:
    """The component DAG: each record's `components` provenance, with broken
    links (upstream no longer in the registry) flagged."""
    ws = os.path.abspath(ws)
    recs = records(ws)
    roots = {r["root"] for r in recs}
    nodes = []
    for r in recs:
        m = kernel.read_manifest(os.path.join(ws, r["path"]))
        edges = [{"input": link["input"], "component": link["component"],
                  "root": link["root"], "status": "ok" if link["root"] in roots else "missing"}
                 for link in m.get("components", [])]
        nodes.append({"name": r["name"], "root": r["root"], "phase": r["phase"],
                      "depends_on": edges})
    return {"workspace": ws, "records": nodes}
