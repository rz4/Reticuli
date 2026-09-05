# Fifth live rehydration — the fully-hardened repo reproduces, 8/8

The capstone of the live-rehydration program: the first full 8-rung run against
the claims with **every round-A/B wall in place and both live-caught blockers
closed** (#3b's bare-env handshake, the workshop re-jail). It **landed 8/8 at the
committed roots and passed its own three-machine test.** Prediction score:
[rehydration-5-prediction.md](rehydration-5-prediction.md).

## Result

A fresh sonnet model, given only the carved checks, regrew all eight rungs —
byte-different free code throughout — and:

- **Landed 8/8 at the committed roots** (kernel-core `2ec592de` … whole
  `cc1a10e7`), verified rung by rung.
- **`ret prove . M2 M3` → satisfied = true**, with integrity, reuse,
  equivalence, and audited all true — M1 the repo, M2 its export imported, M3
  this live rehydration, all on the same whole root.
- **Total: \$18.90, ~515k tokens, 41 calls, ~93 min.**

Every hardening a live model had to reinvent from the check text alone, and did:
the trusted-signer mint ceremony, the env scrub, path confinement, the gate
timeout, distinctness, the bare-env jail handshake, and — the one that killed
run 3 — a **jail-tolerant test suite** at the workshop.

## The two carves that unblocked it, both confirmed live

- **The workshop jail-seam is closed (run 3's death).** With the bench now
  re-jailing during the producer's own iteration, the producer *saw* the jailed
  failures it was previously blind to and ground its way to a jail-tolerant suite
  — **22 calls on workshop alone**, the heaviest single rung by far (\$7.85), the
  cost of actually converging where run 3 had shipped a fragile suite and died at
  the verdict. The carve did exactly what it was meant to: moved the failure from
  the invisible verdict into the producer's visible loop, where it could be
  fixed.
- **The genesis handshake is robust (run 4's death).** kernel-core landed for
  \$1.89 under the bare-env inheritance signal — the regression that broke run 4
  is gone, confirmed now in the full chain, not just isolation.

## Prediction scorecard

| rung | pred \$ | act \$ | act tok | calls | note |
|---|---|---|---|---|---|
| kernel-core | 1.70 | 1.89 | 71k | 2 | close |
| exchange | 4.50 | **2.26** | 75k | 3 | 2× over — the round-B ceremony was cheaper than feared (narration teaches) |
| authoring | 1.50 | 1.24 | 39k | 4 | close |
| agents | 0.55 | 0.63 | 16k | 1 | close |
| surface | 1.60 | **2.85** | 127k | 2 | 1.8× under — the one rung that ran hot |
| workshop | 7.50 | 7.85 | 147k | 22 | **nailed**; 22 calls to reach jail-tolerance |
| vessel | 0.60 | 0.91 | 16k | 5 | close |
| reticuli | 1.30 | 1.27 | 24k | 2 | nailed |
| **total** | **19.25** | **18.90** | **515k** | **41** | **within 2%** |

- **8/8 landed: correct** — the headline call, the first time it was achievable
  and the first time it happened.
- **No budget death: correct**, against my own ~35% workshop-death bet. The
  re-jail made workshop *harder* (it must now reach jail-tolerance), and it still
  landed at \$7.85 vs a \$7.50 bet — the single best per-rung call, on the
  riskiest rung.
- **Total nailed to ~2%** (\$18.90 vs \$19.25), though two rungs missed in
  opposite directions and cancelled: exchange came in half (the ceremony
  regenerated cheaply, as every narrated contract has), surface ran nearly double
  (the one rung that iterated hot — worth watching next time).
- **The overall lesson of the five runs, confirmed:** cost concentrates where a
  producer must *iterate blind against a moving target* (workshop, 22 calls), and
  collapses where the check *narrates its own contract* (exchange, the kernel
  ceremony). Separability and narratability, not raw claim size, set the price.

## Status

Measured 2026-09-05. The fully-hardened repo — every attack from two adversarial
reviews walled, every live-caught reproduction blocker closed — reproduces end
to end under an independent live model and passes its own three-machine test for
~\$19. This is the strongest evidence to date that the object can survive its own
test at flight stage. Not minted: the solid mint remains the user's act.
