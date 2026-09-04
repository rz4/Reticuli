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

## Actuals (filled after the run)

_pending_
