"""The repo itself is a *layered* self-record: the whole verifies fresh, declares
the kernel-core component it layers on, and kernel-core verifies fresh too. Runs
against the committed self-record; skips if this checkout isn't sealed."""
import os

import pytest

from reticuli import kernel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_repo_is_a_fresh_layered_self_record():
    if kernel.phase(ROOT) == "vapor":
        pytest.skip("repo not sealed in this checkout")
    assert kernel.verify(ROOT)["ok"], "the whole record must verify fresh"
    components = kernel.read_manifest(ROOT).get("components", [])
    assert any(c["component"] == "kernel-core" for c in components), "layers on kernel-core"

    core = os.path.join(ROOT, kernel.STORE, "liquid", "kernel-core")
    assert kernel.phase(core) != "vapor", "kernel-core record is present"
    assert kernel.verify(core)["ok"], "kernel-core must verify fresh"
    # every component link points at the kernel-core that is actually present
    assert {c["root"] for c in components} == {kernel.read_manifest(core)["root"]}
