<p align="center"><img src="logo.png" width="170" alt="ζ Reticuli — two stars, one system"></p>

# Reticuli

**Sealed, reproducible records of model-assisted work. The invariant is the
three-machine test.**

A record is valid iff an independent redo lands on the same claim:

```
root = hash( recipe + dry seeds + pinned verdicts )    # the implementation is free
```

Two different implementations that pass the same checks share a root — like the
two stars above: one system. M1 a claim, M2 a reuse of its outputs, M3 an
independent redo; `ret prove` is their root equality with every machine's gates
re-run against its own bytes (`ret audit` — a carried verdict does not survive)
and the redo's cost compared (C3/C1 within tolerance).

## Quickstart

```bash
pip install "git+https://github.com/rz4/reticuli"

ret init && ret hooks              # a session; Claude Code now traces itself
ret run "python checker.py"        # author a gate -> VERIFIED
ret condense --accept VERIFIED --into rec
ret realize rec --producer "$MODEL" --into M3        # the independent redo
ret prove rec M2 M3                # three machines, one root
ret attest M3 --key ~/.ssh/id_ed25519 --as you@lab   # sign it for others
```

## Why

The checks are the claim: edit the implementation and the root holds; edit a
check and it moves. Records commit like lockfiles, travel by content, carry a
cost ledger, and jail their gates where the platform has one. This repo is its
own proof — eight
records, kernel to README, each rung regrown *blind* by a live model onto the
same roots; even this file is a free output, gated only by its own
consumability check.

Depth: [the guide](docs/guide.md) · [the basin](docs/basin.md) ·
[prior art](docs/landscape.md)
