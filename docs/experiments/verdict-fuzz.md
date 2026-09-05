# The verdict-differential fuzz — pointing the instrument at the kernel itself

Every prior experiment used regeneration to probe a *specimen's* spec
(quirkcalc, tomli). This one turns the instrument on Reticuli: the committed
kernel and two regrown specimen kernels — the run-5 capstone draw and the
kc-validate draw, all three honest realizations of the **same kernel-core
claim** (root `2ec592de`) — are asked the *same questions about the same
records*, across a tamper alphabet, and every disagreement is a counterexample:
a region where `kernel_check` is silent and the basin is wider than the
committed bytes suggest. This is the CEGIS loop applied to the claim itself,
with the verifier aimed at our weakest floor, **checker adequacy**.

Kernels under test (sha256-prefixed; the draws are ~400 lines to the committed
607, byte-different throughout): committed `1fa708dd`, run-5 draw `41a7a1c4`,
kc-validate draw `52e95ad1`. Harness: [`vfuzz/harness.py`](vfuzz/harness.py);
data: [`vfuzz/divergences.jsonl`](vfuzz/divergences.jsonl) (205 rows, seed
20260905). Two modes separate two questions: **interop** (records sealed by the
committed kernel, judged by all three — do records *travel*?) and **native**
(each kernel re-seals its own copy before the tamper — do the *verdict
semantics* agree, hash values aside?). Zero model calls; ~3 minutes local.

## Predictions, registered before the run

- **P1 — root canonicalization is free, records won't travel.** CONFIRMED,
  before the fuzz even fuzzed: on a *pristine* record all three kernels compute
  a **different root for the same bytes**. `kernel_check` pins only
  self-consistency (root invariant under free edits, moves under seed edits),
  never a root *value* — and in the rungs, the regrown kernel's own `claim()`
  is never asked to reproduce a committed root.
- **P2 — the cost-band edge (2×, 3×, 0, equal) diverges.** REFUTED — all
  agree, though only 1.5× and 4× are pinned.
- **P3 — refusal exception shapes differ.** CONFIRMED (SHAPE class,
  throughout).
- **P4 — multi-statement mint semantics (one bad + one good) diverge.**
  REFUTED — all three accept the good statement.
- **P5 — symlink-aliased three-machine distinctness diverges** (only literal
  `m1,m1,m1` is pinned). REFUTED — all three refuse the alias.

Two of five wrong, and the misses are the meta-finding (below).

## The findings

**1. Roots, digests, and mint locations are implementation-relative — records
do not travel between basin members.** Three kernels, three canonicalizations,
three roots for identical bytes; realization digests likewise; and the mint
directory itself differs (`.reticuli/mint` vs `mint/`). "Any implementation
passing the same checks is the same claim" holds rung-locally, but the root —
the interchange currency the three-machine test compares — is only meaningful
among parties running the *same* kernel. The M2 leg ("traveled by content")
silently assumes root-canon agreement. If roots must be claim-level facts, the
cage needs a **golden-vector clause**: known recipe + seeds → known root hex.

**2. `audit` semantics forked: both draws re-earn the verdicts and nothing
else.** ~60 ACCEPTS rows, the bulk of the battery: on a record whose *seed* was
edited post-seal (claim broken, gate still passing), committed `audit` fails;
both draws pass. Same for escaping seed paths (committed refuses; draws never
consult confinement on the audit path) and corrupt manifests (draws ignore the
manifest entirely). The check pins audit only through a fabricated-output case
— gate *fails* — never a case where the gate passes but the claim is broken.
"Audit is the deep check" is narrated; *how deep* is unpinned.

**3. Symlink confinement exists only in the committed bytes.** The check pins
`../` and absolute paths; symlinks are silent. Result, maximal width: run-5's
lexical `_safe` (normpath, no realpath) **follows an out-of-root symlink seed
and reads outside the record**; kc-validate refuses more broadly than
committed; committed realpath-refuses. A payload class (exfil-by-symlink)
separates cleanly from every honest record — divergence-rule carvable.

**4. One draw calls a forged packet solid — because the spec never decided
what the packet file *is*.** Swap the packet file's root under an intact
signed statement: committed demotes (the packet must cohere with the statement
digest); kc-validate stays **solid** — its `phase()` *reconstructs* the packet
from the record's live state and hashes that against the statement, never
reading the packet file. That reading is defensible — arguably stronger — but
it means the reviewable artifact can be garbage while phase says solid. A
semantic fork with security texture: decide whether the packet file is
authoritative or residue, then pin the decision.

**5. Hostile-bytes robustness is undisciplined — committed included.** Corrupt
manifest: committed *crashes* raw (`UnicodeDecodeError`), run-5 raises
`JSONDecodeError`, kc-validate sometimes verifies OK. Corrupt recipe: committed
`KeyError`, draws compute a root. Committed `phase()` says "liquid" on a
manifest its own `verify()` cannot parse. The refusal discipline (clean
`ReticuliError` on hostile record bytes) is itself an unpinned property.

**6. The three-machine surface: zero divergences.** Satisfied, equivalence,
per-leg audit, one-root, independence reporting, cost comparability — 3/3
agreement everywhere, *including the unpinned edges* (P2, P4, P5). The
best-specified surface is the one the docs narrate hardest.

## The meta-finding

Where the claim's *narration* is dense — the three-machine invariant, the
doctored-M2 story, the cost band's "a band, not equality" — independent draws
converged even on cases the check never poses. Where the narration is thin —
what audit *is*, what the packet file *is*, what a root *is between parties* —
the basin forked, twice with security stakes. This is run 5's cost lesson
("cost collapses where the check narrates its contract") measured on the
verdict surface itself: **narration is load-bearing spec.** The fuzz found the
paragraphs we never wrote.

## Carving agenda (measured, not yet carved)

By the divergence rule, in stakes order: (a) audit's claim-integrity clause —
gate-passes-but-claim-broken must not audit clean; (b) symlink confinement at
claim/audit; (c) the packet-file decision, then its pin; (d) the golden-vector
root clause if records must travel (this one trades enormous honest width for
interchange — a design fork, not a patch); (e) refusal discipline on hostile
bytes; (f) pin `MINT`'s location if mints must travel. Each lands as a
kernel_check clause only with a payload it separates; (c) and (d) are
decisions before they are clauses.

## Honest limits

n = 2 draws, both Claude-family — a cross-vendor kernel draw would probe
different silence. The tamper alphabet is hand-chosen; the random dimension is
byte flips only, 40 trials. The fuzz is a sampler, as ever. And the harness
judges records *built by the committed kernel* (interop) or *self-sealed*
(native) — a third direction, draw-built records judged by committed, was not
run.

## Status

Measured 2026-09-05. Nothing carved; the agenda above awaits triage. The
specimen kernels live in session scratch (identified here by digest) and are
regenerable by any kernel-core rehydration; the harness takes kernel paths as
arguments and runs against any draw.
