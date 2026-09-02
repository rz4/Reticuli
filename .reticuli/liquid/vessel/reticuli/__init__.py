"""Reticuli — sealed, reproducible records of model-assisted work.

The invariant is the three-machine test: a claim is valid iff an independent redo
lands on the same root. The root is the claim (recipe + dry seeds + pinned
verdicts, free outputs excluded), so the basin of attraction is the preimage of
the root.
"""
from .kernel import (  # noqa: F401
    ReticuliError,
    claim,
    freeze_dry,
    phase,
    realize,
    seal,
    three_machine,
    verify,
)

__version__ = "0.1.0"
