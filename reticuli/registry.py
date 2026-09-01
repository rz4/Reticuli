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
