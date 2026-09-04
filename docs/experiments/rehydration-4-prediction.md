# Fourth live rehydration — cost prediction (written BEFORE the run)

Same protocol as runs [2](rehydration-2-prediction.md) and
[3](rehydration-3-prediction.md): predict, commit, run, score. The first live
run against the **round-B hardened claims** (both adversarial-review carves) —
roots kernel `e03676b7` … whole `cc1a10e7`. Settings identical to runs 2–3:
sonnet (`claude-sonnet-5`), `RETICULI_AGENT_BUDGET=10`/rung, recursive.

**What changed since run 3 (which landed kernel `669636b2`):** two rungs'
claims grew, hard:

- **kernel-core** absorbed the biggest claim growth in the project's history:
  the whole trusted-signer `minted()`/`phase()` (an `ssh-keygen -Y verify`
  against a trust anchor, packet-digest binding, realization-drift demotion,
  proof-recorded coupling, `_signers()` resolution), the scrubbed gate
  environment, the unforgeable jail-inheritance token, `_safe` path
  confinement, the `gate_timeout` killpg bound, and three_machine distinctness —
  on top of everything run 3 already faced. The check itself now runs a full
  keygen / sign / anchor / drift / restore lifecycle, plus untrusted-signer and
  no-proof negatives.
- **exchange** grew the ceremony clause: trusted-anchor mint_check, packet
  binding, a genuine proof recorded and re-mint, phase-follows-verifiable-state.

Six of eight claims are byte-unchanged since run 3 (authoring, agents, surface,
workshop, vessel, reticuli).

## Per-rung point estimate (usd, tokens)

| rung | run 3 actual | why different now | predicted usd | predicted tok |
|---|---|---|---|---|
| kernel-core | \$1.56 / 54k | the entire trusted-signer ceremony + env scrub + token + path/timeout/distinctness | **3.5** | 100k |
| exchange | \$3.90 / 120k | trusted-anchor ceremony + re-mint + proof coupling | 4.5 | 130k |
| authoring | \$1.48 / 46k | unchanged | 1.5 | 46k |
| agents | \$0.52 / 11k | unchanged | 0.55 | 12k |
| surface | \$1.58 / 44k | unchanged | 1.6 | 46k |
| workshop | \$6.74 / (failed) | unchanged claim; the jail-seam risk (see below) | 6.0 | 110k |
| vessel | — (unreached) | unchanged; reached only if workshop lands | 0.6 | 10k |
| reticuli | — (unreached) | unchanged; reached only if workshop lands | 1.3 | 26k |

## The bet

- **Total if it completes: ~\$19–20** (range **\$15–28**); **~480k tokens**.
- **The real test: do kernel-core and exchange land at their committed roots?**
  I bet **yes** — the round-B checks narrate their own design heavily, and every
  live run so far shows a producer builds to a narrated contract (run 3's kernel
  came in 3× *under* because the ceremony taught its own shape). So I predict the
  much-larger kernel claim still lands, and cheaper than its size suggests
  (\$3.5, not the \$5+ its line-count would imply).
- **8/8 is a coin-flip, and workshop is why.** Run 3 died at workshop on the
  **jail-seam** (the regrown `test_quarantine.py` hard-asserts a backend that
  jail-inheritance changes), an issue orthogonal to round B and **not yet
  carved**. I put **~55% on workshop tripping it again** (the producer must, by
  luck, write ambient-jail-tolerant quarantine tests). If it does, the run is
  ~7/8-blocked-at-workshop, ~\$17 spent, vessel+reticuli unreached — a repeat
  data point, but with the round-B kernel/exchange landing as the new signal.
- **Budget deaths: 0** at \$10/rung (workshop dies on a gate failure, not
  budget, if it dies). **Wall clock: 70–110 min.**
- **Biggest way I'm wrong:** kernel-core could thrash on the trusted-signer
  ceremony (an `ssh-keygen -Y verify` contract the agent can't probe directly,
  since its tool allowlist is python-only) and blow toward \$8, or even fail to
  land — that's the round-B claim most likely to defeat a blind producer.

Actuals and the score go below after the run.
