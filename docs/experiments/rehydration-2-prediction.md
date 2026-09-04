# Second live rehydration — cost prediction (written BEFORE the run)

A prediction-then-measure experiment: predict my own cost, commit it, then run
and score the prediction. Committed before the run so there is no hindsight.

**Run:** full 8-rung recursive agentic rehydration of the repo, sonnet
(`claude-sonnet-5`), `RETICULI_AGENT_BUDGET=10`/rung, against the *current*
carved claims (roots kernel `a3548eec` … whole `cc1a10e7`).

**Basis:** the per-cell sonnet-agentic rows in `reflection_profile.jsonl`
(measured against the *old*, looser claims), adjusted upward for what the carve,
round two, and the mint chain added to each rung. Workshop and vessel have **no
per-cell data** — the only prior is the capstone, where workshop hit a \$5 budget
death — so they are the least certain.

## Per-rung point estimate (usd, tokens)

| rung | old (profile) | why harder now | predicted usd | predicted tok |
|---|---|---|---|---|
| kernel-core | \$1.22 / 42k | seed-sensitivity, tolerance, no-network, mint primitives, usage guard | 1.6 | 55k |
| exchange | \$1.30 / 46k | **the whole mint chain** + leak/determinism/attest-travel | 2.1 | 75k |
| authoring | \$1.54 / 46k | cold-certification | 1.85 | 55k |
| agents | \$0.70 / 20k | ~unchanged | 0.7 | 20k |
| surface | \$1.33 / 39k | phase-sectioned help + verb floor + `mint` verb | 1.85 | 55k |
| workshop | *(no data)* | import-safety + bigger suite; capstone hit \$5 | 5.5 | 120k |
| vessel | *(no data)* | build-hygiene clause; mostly declarative | 1.5 | 45k |
| reticuli (docs) | \$0.34 / 3.6k | guide is now 3.3k words (mint chain, trust ladder) | 1.5 | 30k |

## The bet

- **Total: ~\$19** (range **\$14–26**), **~500k tokens** (range 380–650k).
- **Lands 8/8.**
- **Dominant cost: workshop (~\$5.5), then exchange (~\$2.1).** These two rungs
  are ~40% of the bill.
- **Retries: 1–2** (transient), most likely on workshop or exchange. **Budget
  deaths: 0** at \$10/rung.
- **Wall clock: 25–45 min.**
- **Biggest way I'm wrong:** workshop (no prior data; could be \$3 or \$9), and
  the enlarged guide making the reticuli rung cost more than \$1.5.

Actuals and the score go below after the run.

## Actuals (2026-09-04)

**Landed 8/8** at the committed roots; the live M3 passes the three-machine test
(`ret prove . M2 M3` → satisfied/integrity/reuse/equivalence/audited all true).
**Total: \$15.79, 405,608 tokens, 41 calls, 67 min wall-clock.**

| rung | pred \$ | act \$ | pred tok | act tok | calls | note |
|---|---|---|---|---|---|---|
| kernel-core | 1.6 | **3.02** | 55k | 89k | 2 | 2× under — worst miss; the genesis is heaviest |
| exchange | 2.1 | 1.72 | 75k | 62k | 3 | over; the mint chain was cheaper than feared |
| authoring | 1.85 | 1.62 | 55k | 52k | 4 | close |
| agents | 0.7 | 0.56 | 20k | 15k | 1 | close; clean one-shot |
| surface | 1.85 | 1.63 | 55k | 55k | 2 | tokens nailed |
| workshop | 5.5 | **5.37** | 120k | 98k | 22 | **nailed the \$** (2% off) — the no-data rung; 22 calls of iteration |
| vessel | 1.5 | 0.55 | 45k | 8k | 5 | 3× over — declarative, far cheaper |
| reticuli | 1.5 | 1.31 | 30k | 26k | 2 | close |
| **total** | **19.0** | **15.79** | **500k** | **406k** | **41** | ~20% over, inside the \$14–26 band |

## Score

- **8/8 landed: correct.** No budget deaths (predicted 0). Both correct.
- **Total \$ and tokens: inside the predicted ranges**, ~19–20% high — a
  conservative overbet.
- **Best call: workshop** — the rung with *no prior data*, predicted from the
  capstone's \$5-death alone, came in at \$5.37 vs \$5.5 (2% off) and was the
  dominant single cost exactly as called.
- **Worst call: kernel-core** — 2× under. The deepest rung is the heaviest, not
  the lightest: cost concentrates at the bottom of the abyss, the same place the
  significance does. I systematically overtaxed the outer/handshake rungs
  (agents, vessel, surface all came in under) and undertaxed the genesis.
- **Two real misses beyond dollars:** iteration count (predicted "1–2 retries";
  actual 41 calls, workshop alone 22 — the agentic producer iterates hard per
  rung), and wall-clock (predicted 25–45 min; actual 67).

**Takeaway for the paper:** against the *carved* claims — stricter than the
capstone faced — a live model still lands 8/8 and the redo passes the
three-machine test, for ~\$16. The tightening did not push the basin out of
reach; it made the deepest rung heavier and left the outer rungs cheap. Cost is
bottom-weighted, and the workshop stratum remains the fragile, iteration-hungry
one.
