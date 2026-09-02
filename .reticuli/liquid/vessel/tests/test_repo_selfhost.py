"""The repo itself is a *layered* self-record: six rungs ordered by interface
volatility (kernel-core -> exchange -> authoring -> agents -> surface ->
contact, the README), each verifying fresh and layering on exactly its
predecessor. Runs against the committed self-record; skips if this checkout
isn't sealed."""
import os

import pytest

from reticuli import kernel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAIN = ["kernel-core", "exchange", "authoring", "agents", "surface",
         "workshop", "vessel"]   # drawers, inner -> outer


def _links(d: str) -> set:
    return {c["root"] for c in kernel.read_manifest(d).get("components", [])}


def test_repo_is_a_fresh_layered_self_record():
    if kernel.phase(ROOT) == "vapor":
        pytest.skip("repo not sealed in this checkout")
    assert kernel.verify(ROOT)["ok"], "the whole record must verify fresh"
    drawer, root = {}, {}
    for name in CHAIN:
        d = os.path.join(ROOT, kernel.STORE, "liquid", name)
        assert kernel.phase(d) != "vapor", f"{name} record is present"
        assert kernel.verify(d)["ok"], f"{name} must verify fresh"
        drawer[name], root[name] = d, kernel.read_manifest(d)["root"]
    # each rung layers on exactly its predecessor — a linear chain, leaf to contact
    assert _links(ROOT) == {root["vessel"]}, "contact layers on the vessel"
    assert _links(drawer["vessel"]) == {root["workshop"]}, "the vessel layers on the workshop"
    assert _links(drawer["workshop"]) == {root["surface"]}, "the workshop layers on the surface"
    assert _links(drawer["surface"]) == {root["agents"]}, "the surface layers on agents"
    assert _links(drawer["agents"]) == {root["authoring"]}, "agents layers on authoring"
    assert _links(drawer["authoring"]) == {root["exchange"]}, "authoring layers on exchange"
    assert _links(drawer["exchange"]) == {root["kernel-core"]}, "exchange layers on the kernel"
