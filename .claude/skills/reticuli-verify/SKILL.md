---
name: reticuli-verify
description: Use to independently check a Reticuli record — that it travels intact, its verdicts are earned rather than carried, and an independent redo reproduces its root (the three-machine test). For vetting a record you received, or your own before handing it off. Does not authorize/sign (that is reticuli-mint, a human act).
---

# Verifying a Reticuli record — the three-machine test

The invariant: a claim is valid iff three machines share one root and every one
re-earns its verdicts.

```
M1  the claim            the record as authored
M2  a byte-reuse         M1's outputs carried verbatim, produces nothing
M3  an independent redo  the free code rebuilt from the recipe by any producer
valid  ⇔  roots equal  ∧  each machine's gates re-run clean (audit)  ∧  cost comparable
```

> If `ret` is not on PATH, use `python3 -m reticuli`.

## Steps

1. **M2 — byte-reuse:** `ret export rec claim.tar && ret import claim.tar M2`.
   Import verifies from the bytes alone; M2 proves the record is self-contained.
2. **M3 — independent redo:** `ret realize rec --producer "<cmd or model>" --into M3`.
   The producer is any command/model that writes the free files from the recipe
   (blind to M1's implementation). Add `--recursive` if the record has components
   (it rehydrates the whole DAG, leaf-first).
3. **Judge:** `ret prove rec M2 M3`. `satisfied` requires `integrity` (each
   verifies fresh) + `reuse` (M2 carries M1's outputs) + `equivalence` (one root
   across all three) + `audited` (verdicts re-earned) + comparable cost.

For soundness without a full redo: **`ret audit rec`** rebuilds a scratch room
from the recipe/seeds/outputs (no verdicts carried in), re-runs every gate
**jailed**, and requires each pinned output to reproduce exactly. A copied
verdict does not survive it.

## Read the result honestly (the trust ladder)

1. **root match** — same claim (identity).
2. **audit** — verdicts earned by these bytes, not fabricated.
3. **attestation** — a named keyholder ran this and signed it (verify against
   your allowed-signers; an unknown key is *intact*, not *trusted*).
4. **solid mint** — these exact bytes, frozen and authorized by a signer you
   trust. A record on disk gives you 1–3, never 4.

Limits to state, not hide: `prove` refuses identical M1/M2/M3 paths and reports
`independence = "unestablished"` — audit shows *these bytes earn these verdicts*,
not that M3 was produced without copying M1 (that is attestation's job). Off the
checks' support, behavior is unconstrained — the basin is real; the root was
never a claim about the free bytes.

Depth: `docs/guide.md` (Soundness; What a root promises).
