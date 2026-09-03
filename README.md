<p align="center"><img src="logo.png" width="170" alt="ζ Reticuli — two stars, one system"></p>

# Reticuli

**Sealed, reproducible records of model-assisted computation. The invariant is
the three-machine test.**

When an AI helps write scientific software, what survives review — a chat
transcript? Reticuli keeps what a reviewer actually needs: the inputs, the
acceptance checks, and the verdict, sealed as a *record* whose identity is

```
root = hash( recipe + inputs + pinned verdicts )    # the implementation is free
```

The code is deliberately excluded — any implementation passing the same checks
(yours, a colleague's, any model's) is *the same claim*: two stars, one system.
Replication becomes mechanical: **M1** the original, **M2** a copy that
traveled by content, **M3** an independent redo. `ret prove` re-runs every
machine's checks against its own bytes (a carried verdict fails `ret audit`)
and compares what the redo cost.

## Quickstart — the full proof

```bash
pip install "git+https://github.com/rz4/reticuli"

ret init && ret hooks                   # a session; Claude Code traces itself
ret run "python3 checker.py"            # author a gate -> VERIFIED
ret condense --accept VERIFIED --into M1        # M1: the sealed claim
ret export M1 claim.tar                         # the record travels by content
ret import claim.tar M2                         # M2: verified from bytes alone
ret realize M1 --producer "$MODEL" --into M3    # M3: independent redo, any model
ret prove M1 M2 M3                      # three machines, one root
ret attest M3 --key ~/.ssh/id_ed25519 --as you@lab.gov    # sign it for others
```

## Why

The checks are the claim: edit the implementation and the root holds; edit a
check and it moves. Records commit like lockfiles; checks run sandboxed; every
redo's cost is ledgered. This repo is its own evidence — eight records, kernel
to README, each regrown independently by a live model onto the same roots;
even this file is free, gated only by its own consumability check.

Depth: [the guide](docs/guide.md). Design essays and experiment data live in
`docs/notes/` and `docs/experiments/` — residue, carried but never regrown.
