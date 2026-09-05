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

## Carved (2026-09-05)

Three of the six findings were promoted to `kernel_check` clauses the same day,
in stakes order, per the plain-English agenda:

- **Finding 2 (audit is claim-deep).** New clause: a record whose dry *seed* is
  edited after sealing — the claim broken, the gate still green — must fail
  `audit`. Both draws blessed it; an honest kernel folds claim integrity in.
- **Finding 3 (symlink confinement).** New clause: a seed that is a symlink
  whose target leaves the record is refused by `claim`. `_safe` must resolve
  links, not judge lexically — the exfil-by-symlink payload class.
- **Finding 5 (hostile-bytes discipline).** Fixed the committed kernel first
  (it was an offender): `load_recipe` and `read_manifest` now refuse malformed
  recipe/manifest bytes with `ReticuliError` instead of leaking a raw
  `TOMLDecodeError`/`JSONDecodeError`, and `phase` no longer answers "liquid"
  about a manifest it cannot parse. New clause pins all three.

Editing the `kernel_check` seed moved **only** the kernel-core root
(`2ec592de` → `b2f5b117`); the other seven held — localization confirmed live.
The check passes bare and jailed; the 48-test suite is green.

**Finding 4 decided and carved (2026-09-05).** The packet file is
**authoritative**, not disposable residue: solidity must verify the stored
review bundle against the signature, so swapping the packet file demotes even
when the live record is untouched. New `kernel_check` clause; the committed
kernel already did this (reads and binds the file), so it is a pure pin — teeth
confirmed against the kcval draw, whose `phase()` reconstructs the packet from
live state and so calls a forged packet solid (it fails the new clause). The
complementary direction (file honest, record drifted) was already pinned by the
post-mint `g.txt` edit. Editing the seed moved only kernel-core
(`b2f5b117` → `498e426a`); the other seven held.

**Finding 1 decided and carved (2026-09-05).** The root is an **interchange
currency**, not a private serial number: the canonical hash-preimage layout is
now pinned in `kernel_check` (a serialization spec plus a six-vector golden
battery), so every conformant kernel computes the same root hex for the same
record — a record travels, and a *rehydrated* kernel can verify what the
committed one sealed. The decision was forced by the project's own method:
**the rehydrated Reticuli is the test**, and until this pin a regrown kernel
computed a different canon (`claim()` gave `a2ec25f2…` where committed gave
`0c1f4da0…`) and read committed-sealed records as tampered — so "regrown onto
the same roots" was really "the committed kernel sealed the regrown code," never
the regrown kernel agreeing. The pin freezes the *current* format (committed's
roots do not churn), so it is a one-way commitment to today's serialization.
Teeth: the fresh and kcval draws both fail the battery (different canon). Seed
edit moved only kernel-core (`498e426a` → `19bab9d5`); the other seven held.

Golden vectors alone would not be rehydration-compatible — a hash cannot be
reversed, so a regrown kernel cannot match the hex blind. The spec in the seed
is what lets the agentic loop converge: it runs `kernel_check`, sees "your root
is X, want Y," and iterates its `claim()` until the bytes agree. The vectors are
counterexamples; the loop is CEGIS.

*Live-validated (2026-09-05).* An independent kernel-core rehydration (sonnet-5,
`$2.59`, ~14 min) — 971 lines different from committed — **converged on the
canonical serialization**: the regrown kernel's `claim()` computes `0c1f4da0…`
where committed does (they **agree**), it computes `19bab9d5…` for the committed
kernel-core drawer, and — the exact thing that failed before the carve — it
**verifies a committed-sealed record as `ok = True`**. Records travel between two
independent kernels. The spec-plus-vectors form is sufficient; the pinned-
reference-function fallback is not needed. Re-fuzzing committed vs this regrown
kernel: divergences `126 → 84`, and **every pristine-record verify/audit/claim
divergence is gone** (`divergences-currency.jsonl`).

What the root carve did not close, and the follow-on carve that did: the
**realization digest** — the free crystal a mint binds — was still
implementation-relative after the root pin (28 residual `rdigest` divergences),
so *records* travelled but *mints* did not (a mint bound to one kernel's digest
would not verify under another). The currency was then **extended to
`realization_digest`** (2026-09-05) with the same spec-plus-vectors technique: a
preimage spec plus a six-vector `RD_GOLDEN` battery (one free output, two, an
absent-and-omitted free output, a `from`-excluded output, unicode, and none).
Teeth are pointed: the `kernel_currency` draw — which already *agrees on the
root* — fails precisely at `rd1-one-free`, exactly the residual gap. Editing the
seed moved only kernel-core (`19bab9d5` → `712d4976`); the other seven held.

*Live-validated (2026-09-05).* A second independent rehydration (sonnet-5,
`$3.30`, 970 lines different from committed) converged on **both** canonical
serializations at once: root agree, realization digest agree (`81a409f2…`), and
— the decisive test — a record the **committed** kernel minted verifies as
**`solid` under the regrown kernel**. Mints travel between independent kernels;
cross-implementation *solid* holds. Re-fuzzing committed vs this regrown kernel:
divergences `84 → 31`, `rdigest 28 → 1` (the lone survivor a byte-flip artifact).
The regrown kernel even chose the same mint directory (`.reticuli/mint`)
independently, so the unpinned mint *location* happened to agree here too.

The residual `31` were almost entirely **refusal-discipline SHAPE**: on an
*already-damaged* record (a deleted or path-escaping seed, a corrupt recipe)
committed's `phase` returned `"liquid"` while the regrown kernel *raised*. Both
agreed the record was not solid; they differed only in how they voiced the
refusal — but it exposed a real inconsistency in *committed*: `phase` read only
the manifest, so it answered `"liquid"` about a record its own `verify` refuses.

**Both micro-carves done (2026-09-05).** (1) *phase agrees with verify on
validity*: `phase` now recomputes the claim, so a record whose recipe is
malformed, escapes confinement, or names a missing seed is refused (a directory
with a recipe but no manifest is still `"vapor"` — unsealed, not an error); and
`_hf` refuses a missing declared file with `ReticuliError` instead of a raw
`OSError`. (2) *free-output symlink confinement*: `audit` refuses a free output
symlinked out of the record (it copies every produce output through the
confinement boundary; a free output is never hashed, but copying one that
escapes is the same exfiltration a seed symlink would be). Both are `kernel.py`
changes plus pins; the mint-currency draw fails the new pins (teeth). Seed edit
moved only kernel-core (`712d4976` → `fab7a497`); the other seven held. With
these, every fuzz finding is either carved or a decided design choice, and no
divergence remains on an honest record. Data: `divergences-mint.jsonl`.

**Finding 6** (three-machine surface, zero divergence) needed nothing.

## Live validation — the basin holds the carve, not just the committed bytes

The run-4 lesson: a hardening clause is only real if an *independent
regeneration* satisfies it — the committed bytes passing the check proves
nothing about the basin. So the carve was validated by a fresh kernel-core
rehydration of `b2f5b117`: an agentic Claude producer (sonnet-5) regrew
`reticuli/kernel.py` from the stricter `kernel_check.py` **alone**, no reference
implementation. Result:

- **A genuinely independent draw.** 953 lines differ from committed, 25
  top-level defs vs committed's ~35 — a full rewrite, not a copy.
- **It passes the stricter check, jailed.** All three new clauses satisfied by
  a draw that had never seen them — the authoritative gate, in the verdict
  environment.
- **It lands at `b2f5b117`.** Same claim root as committed, though its
  `kernel.py` is byte-different and its `__init__.py` is empty where committed's
  is 505 bytes — the implementation-is-free property, live.
- **Cost `$2.95`** (101,991 tokens) vs the pre-carve kernel-core's `$1.69` —
  ~75% more. The three clauses made the invariant measurably harder to regrow;
  cost concentrates where the check narrates more contract (the run-5 lesson).

Then the fuzz was re-run, committed vs this fresh same-claim draw:

| | pre-carve (vs old draws) | post-carve (vs fresh draw) |
|---|---|---|
| total divergences | 205 | 126 |
| ACCEPTS (draw blesses what committed refuses) | ~45 | 6 |
| carved classes still divergent | — | **none** |

The three carved classes are **quiet**: seed-edited-record (audit
claim-integrity), seed-symlink (confinement), and corrupt manifest/recipe
(hostile-bytes) all show zero ACCEPTS — the fresh draw refuses each, where the
pre-carve draws blessed them. The 6 residual ACCEPTS are all `@n` random
byte-flips on the manifest/recipe, and all are **flip-index artifacts, not
counterexamples**: native mode flips byte *i* of each kernel's *own* manifest,
but the two manifests differ in length (102 vs 95 bytes — finding 1 again), so
"flip byte 8" corrupts committed's JSON while landing on a benign space in the
draw's. The remaining 120 divergences are dominated by finding 1 (roots don't
travel: interop records sealed by committed don't verify under a different
canon) plus exception-shape cosmetics and two minor new unpinned edges (the
draw is *stricter* on free-output symlinks, and differs on a zero-cost-band
edge — both safe-direction, both future-carve candidates).

**A harness artifact, noted honestly.** `realize` reported "failed" though the
gate passed: the agent wrote a valid *empty* `__init__.py`, and the producer's
`getsize(out) > 0` success guard rejects an intentionally-empty free output. The
regeneration landed in the basin; the guard is a false-negative on a legitimate
minimal realization (existence, not size, is the signal for a free file that may
be empty). **Fixed** (commit `1ede141`): both agentic producers now key
completion on the gate passing rather than a file's size; the oneshot producers,
which cannot emit a 0-byte file, are unchanged. A free-code fix — all eight
roots held.

Post-carve data (committed vs the fresh `b2f5b117` draw):
[`vfuzz/divergences-postcarve.jsonl`](vfuzz/divergences-postcarve.jsonl).

## Capstone — one independent regrowth converges on the whole hardened kernel

A final kernel-core rehydration (sonnet-5, `$2.81`, 999 lines different from
committed) against the *fully hardened* check — every clause this arc added —
agreed on **all seven pinned dimensions at once**: root, realization digest,
verify-a-committed-record, mint-travel (it reads a committed mint as `solid`),
`phase` refuses an escaping seed, `phase` returns `vapor` on a no-manifest
record, and `audit` confines a free-output symlink. Fuzzing committed vs this
draw: `16` divergences (from `205` at the arc's start), **zero on any honest
record**; the residual is damaged-record refusal-discipline SHAPE plus native
byte-flip artifacts. Data: `divergences-capstone.jsonl`.

The capstone also independently reproduced a *new* hole (see below): the draw
accepts an unknown step `kind`, because the check does not pin the vocabulary —
the basin inherits the gap, not just committed. Exactly the point that an
unpinned property is not a property.

## A reviewer's three holes (2026-09-05)

An external review of this exact version found three concrete holes the fuzz had
not reached, all in the *authoring* machinery rather than the kernel invariant:

1. **condense and pack bypass the scrubbed-bounded gate contract.** Both called
   `_jailed(cmd, room, {**os.environ, …})` — the full environment, no
   `_gate_timeout` — so a gate run by `pack`/`condense` could read an inherited
   secret and seal it into the verdict (reproduced: `pack` sealed a fake
   credential into `VERIFIED`). `realize` and `audit` scrub via `_gate_env`;
   these two did not.
2. **condense confines recipe paths too late.** Trace-derived seed/output paths
   were copied with raw `os.path.join` *before* `_safe`; a traced read of
   `../secret.txt` was copied outside the `.building` room before seal refused
   the record. The invariant held at sealing, but the boundary was already
   crossed on the way there.
3. **Recipe-shape validation admits unknown step kinds.** `load_recipe` required
   a `kind` but not that it be recognized; a `kind="weird"` step with no output
   sealed, verified, and audited clean, then `realize` crashed with a raw
   `KeyError('output')` — an implementation exception where the hostile-bytes
   discipline promises `ReticuliError`.

**Carved (2026-09-05).** One architectural correction, as the reviewer proposed:

- **A single gate-execution entry point, `kernel.run_gate`**, owns the contract —
  scrubbed env (`_gate_env`), bounded wall-clock (`_gate_timeout`), quarantine
  (`_jailed`). `realize`, `audit`, `condense`, and `pack` all run gates through
  it. `kernel_check` pins that `run_gate` scrubs (a gate cannot seal an inherited
  secret); `authoring_check` pins, *structurally* (an AST clause), that condense
  and pack never call `_jailed` directly — so a refactor cannot quietly reopen
  the hole, and behaviorally that `pack` cannot seal a secret.
- **`_safe` at the authoring copy**: condense routes trace-derived seed/output
  paths through the confinement boundary *before* copying, like realize and
  audit. `authoring_check` pins that an escaping traced read is refused with
  nothing copied out of the room.
- **The `kind` vocabulary is closed**: `load_recipe` refuses any kind but
  `produce`/`gate`; `kernel_check` pins that an unknown kind is a `ReticuliError`
  at parse, never a raw `KeyError` in `realize`.

The change entered exactly two rungs — kernel-core (`fab7a497` → `7c31e5a3`,
finding 3 + the scrub pin) and authoring (`b7610cbb` → `e4f720ae`, findings 1
and 2) — everything between and above held, the whole root included. All three
holes reproduced before and are closed after; checks pass bare and jailed, 48
tests green.

*Regeneration-validated (2026-09-05).* A recursive rehydration of the authoring
rung (sonnet-5, `$2.18` for the authoring stratum) regrew kernel-core → exchange
→ authoring leaf-first; **all three landed at their committed roots**
(`7c31e5a3`, `39546fe6`, `e4f720ae`). The regrown kernel (1018 lines different
from committed) grew `run_gate` and used it; the regrown condense and pack call
`_jailed` **zero** times and route through `run_gate` instead. A fresh authoring
draw *independently adopted the single-entry-point architecture* — the AST clause
forbids `_jailed`, so the agentic loop iterated until condense/pack complied. The
architectural contract is expressible from the check alone, and regeneration
reproduces it: the reviewer's three holes are closed in the basin, not merely in
the committed bytes.

## Status

Measured 2026-09-05 against kernel-core `2ec592de`; three findings carved the
same day (kernel-core now `b2f5b117`) and the carve validated live by an
independent rehydration (fresh draw passes the stricter gate jailed, lands at
`b2f5b117`, `$2.95`; the three carved divergence classes went quiet). The two regrown specimens are of the
*pre-carve* claim, so re-running the harness with the current committed kernel
is a cross-claim comparison; the clean re-measurement is a fresh kernel-core
rehydration of `b2f5b117` fuzzed against committed — expected to show the three
carved classes gone. The harness takes kernel paths as arguments and runs
against any draw.
