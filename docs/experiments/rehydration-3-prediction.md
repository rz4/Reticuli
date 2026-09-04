# Third live rehydration — cost prediction (written BEFORE the run)

Same protocol as [run 2](rehydration-2-prediction.md): predict my own cost,
commit it, run, score. Committed before the run so there is no hindsight.

**Run:** full 8-rung recursive agentic rehydration, sonnet (`claude-sonnet-5`),
`RETICULI_AGENT_BUDGET=10`/rung — identical settings to run 2, so the only
variable is the **hardened claims** (roots kernel `669636b2` … whole
`cc1a10e7`). This is the first live run against the attack-review carve.

**Basis:** run 2's per-rung actuals, adjusted for what the carve added. Six of
eight rungs' claims are byte-unchanged since run 2; the whole delta is
concentrated in two rungs:

- **kernel-core** got the largest single-rung claim growth of any re-mint yet:
  the `minted()` ceremony (an intact-signature test via `ssh-keygen
  check-novalidate`, packet-digest canonicalization, realization-drift
  demotion, solid⇔verified phase), the M2-root clause (equivalence over the
  root set), proven-not-solid, and mint-fold commutativity. The check itself
  now runs a full keygen/sign/tamper/restore cycle in the gate.
- **exchange** got attest drift detection, mint_check packet binding,
  mint_root elision refusal, proof status in the ceremony, and
  phase-follows-the-verifiable-state in the registry.

## Per-rung point estimate (usd, tokens)

| rung | run 2 actual | why different now | predicted usd | predicted tok |
|---|---|---|---|---|
| kernel-core | \$3.02 / 89k | minted() ceremony + M2-root + proven/solid split | **5.0** | 130k |
| exchange | \$1.72 / 62k | drift, packet binding, elision refusal, proven | 2.6 | 80k |
| authoring | \$1.62 / 52k | unchanged claim | 1.6 | 50k |
| agents | \$0.56 / 15k | unchanged claim | 0.6 | 15k |
| surface | \$1.63 / 55k | unchanged claim | 1.6 | 55k |
| workshop | \$5.37 / 98k | claim unchanged; supplied modules larger (minted) | 5.5 | 100k |
| vessel | \$0.55 / 8k | unchanged claim | 0.6 | 10k |
| reticuli (docs) | \$1.31 / 26k | claim unchanged; guide grew but is free | 1.3 | 26k |

## The bet

- **Total: ~\$19** (range **\$15–26**), **~470k tokens** (range 380–620k).
- **Lands 8/8.**
- **Cost stays bottom-weighted and sharpens**: kernel-core becomes the #2 rung
  (~\$5.0), closing on workshop (~\$5.5); the two together ≥ 50% of the bill.
  The six unchanged rungs come in within ±25% of their run-2 actuals.
- **Ledger calls: 41–45** (run 2: 41 — calls track produce steps + retries,
  not iteration depth). **Wall clock: 70–100 min** (run 2: 67).
- **Budget deaths: 0** at \$10/rung — but kernel-core is the likeliest death
  if I'm wrong (~20%): the minted() ceremony is new behavior with an external
  tool (ssh-keygen) the agent's allowlist won't let it probe directly; it must
  debug through the check.
- **Biggest way I'm wrong:** kernel-core (could be \$3.5 if the check's
  narration carries the design as well as it carried the seed-sensitivity
  story, or \$8+ if the agent thrashes on signature/digest canonicalization).

Actuals and the score go below after the run.
