# Fifth live rehydration — cost prediction (written BEFORE the run)

Predict, commit, run, score. The first full 8-rung run against the claims with
**both live-caught blockers closed**: run 4's genesis handshake regression
(#3b reverted to bare-env) and run 3's workshop jail-seam (the bench now
re-jails). Roots kernel `2ec592de` … whole `cc1a10e7`. Settings as before:
sonnet (`claude-sonnet-5`), `RETICULI_AGENT_BUDGET=10`/rung, recursive.

**What's new since the last completed run (run 3, which reached workshop):**

- **kernel-core** carries all of round A+B (trusted-signer ceremony, env scrub,
  path confinement, timeout, distinctness) but with the bare-env jail handshake.
  Validated live in isolation after the #3b revert: regenerated and landed at
  `2ec592de` for **\$1.69**.
- **exchange** carries the round-B ceremony (trusted-anchor mint_check, packet
  binding, proof coupling, re-mint) — **never reached by a live run** (run 4 died
  at the genesis first). The biggest unknown.
- **workshop** now `_rejail`s: the producer's own gate-runs are jailed, so it
  must make its regenerated suite **jail-tolerant** to pass — strictly harder
  than run 3, where it shipped a fragile suite and only the verdict caught it.

## Per-rung point estimate (usd, tokens)

| rung | prior live | why now | predicted usd | predicted tok |
|---|---|---|---|---|
| kernel-core | \$1.69 (kc-validate) | same claim, bare-env handshake | 1.7 | 60k |
| exchange | \$3.90 (run 3, pre-round-B) | + round-B ceremony, unproven live | 4.5 | 130k |
| authoring | \$1.48 (run 3) | unchanged | 1.5 | 46k |
| agents | \$0.52 (run 3) | unchanged | 0.55 | 12k |
| surface | \$1.58 (run 3) | unchanged | 1.6 | 46k |
| workshop | \$6.74 (run 3, failed) | now must reach jail-tolerance under the re-jail | 7.5 | 120k |
| vessel | \$0.55 (run 2) | unchanged | 0.6 | 10k |
| reticuli | \$1.31 (run 2) | unchanged | 1.3 | 26k |

## The bet

- **First 8/8 against the fully-hardened claims** — this is the headline call,
  and the first run where I believe it is achievable (both known blockers
  closed). Total **~\$19–20** (range **\$15–30**), **~450k tokens**.
- **Workshop is the death risk, and it moved *up*.** The `_rejail` makes the
  producer iterate to a jail-tolerant suite — it now *sees* the jailed failures
  it was previously blind to, which is the fix, but it also means more iteration.
  I put **~35% on a workshop budget death at \$10/rung** (the producer thrashes
  making quarantine tests inherited-tolerant). If it dies, it's a budget death,
  not a seam failure — a different, better failure than run 3.
- **Exchange is the accuracy risk** — the round-B ceremony is unproven live;
  \$4.5 is a guess that could be \$3 or \$7.
- **Wall clock: 75–120 min.** Retries: 1–3 (transient), most likely workshop.
- **Biggest way I'm wrong:** workshop — either a budget death (~35%), or the
  re-jail interacting badly with the producer's own tool sandbox (a new
  failure mode the isolated kc-validate did not exercise, since kernel-core's
  suite is tiny). If workshop lands, 8/8 is very likely.

Actuals and the score go below after the run.
