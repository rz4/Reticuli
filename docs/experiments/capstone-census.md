# The capstone census — what made it to the other side

**Specimen:** `scratch/M3` — the capstone rehearsal's M3 (2026-09-03): a full
eight-rung agentic rehydration (sonnet, no reference implementation in any
room) that landed the exact committed root `b4365b16…`, `satisfied=true`,
`audited=true`. **Baseline:** the committed tree (M1) at the same root.
**Method:** per-file byte/line comparison; a wall map read off the eight rung
checks (what each battery actually asserts); and side-by-side behavioral
experiments running both kernels on identical fixtures. n = 1 specimen, one
model, one run — a census, not a distribution.

The reading rule that makes this an instrument: **every divergence between M1
and a landed M3 is, by construction, outside the claim.** The census is a
direct readout of the basin's unforced dimensions.

## Headline numbers

- **41 of 44 files byte-divergent.** The only identical files are exactly the
  identity class: the seed (`docs_check.py`), the recipe (`reticuli.toml`),
  the verdict (`VERIFIED`).
- **Mass conserved, redistributed: 4,052 lines (M3) vs 4,008 (M1)** over the
  divergent files — but every implementation module is leaner (kernel 262 vs
  393, cli 231 vs 389, every script roughly halved) while the tests balloon
  (112 tests / 242 asserts vs 49 / 113; `test_cli` 226 vs 51 lines). Line
  mass flows along the pressure gradient of the checks: overbuild under the
  toothy clause, minimum under the compile-only clause.
- **All 15 test filenames identical, all 15 contents different** — the recipe
  pins the file inventory (names are structure, hence identity), so the
  filename acts as a one-word prompt: `sweep.py` grew a sweeper (of records,
  not experiments), `probe.py` a prober, `envelope.py` an envelope-builder.
  Names forced; purposes free.

## Measured behavioral divergences (experiments, not readings)

Same fixture, both kernels, side by side:

| Property | M1 (committed) | M3 (regrown) | Forced by a gate? |
|---|---|---|---|
| Edit a **seed** ⇒ verify breaks, recomputed root moves | yes | **no — ok=true, root holds** | no (kernel_check's fixture has no `inputs`) |
| Edit **free** bytes ⇒ root holds | yes | yes | yes (root-is-the-claim clause) |
| 1.5× redo cost comparable | **yes** (tolerance 2.0) | **no** (strict equality) | no (battery only pins 4:1 fails, unmeasured→None) |
| Export byte-deterministic | yes | yes | no — crossed anyway (concept stated in the seed's docstring) |
| Stray undeclared file travels in export | no (declared-content-only) | **yes** (walks the room) | no (battery only excludes the ledger) |

The first row is the deep one. M3's root is `hash(step structure + validated
outputs)`; record `inputs` are never hashed. Its own README documents this
honestly — "root = hash(structure + every validated output's bytes)" — and
that sentence *satisfies the docs needle*. The invariant's most-quoted
property, "edit a check and it moves," holds in M3 only via `pack`'s
convention (checks as `class = "validated"` steps — authoring_check does force
that path) and fails on the kernel `inputs` path and the condense path. **Two
kernels in the same basin disagree about which bytes are identity.**

## The wall map (what each rung forced vs what drifted)

- **kernel-core** — Crossed: seal/verify/realize/three-machine, audit
  ("earned, not carried" — the fabricated-M3 battery), calls-ledger,
  jail-with-refusal, the `RETICULI_JAILED` inherit contract (M3 even invented
  a *different* nested-jail fallback: chmod the parent read-only). Drifted:
  seed-sensitivity of the root (above); cost unit hierarchy
  (usd>tokens>calls>seconds) and tolerance ratio — no `usd`/`tokens`/
  `tolerance` anywhere in M3.
- **exchange** — Crossed: content-addressed links, DAG + leaf-first
  rehydrate, pull, ledger-stays-home, verify-on-import,
  audit-before-attest (free-tamper and broken-pin both refuse), the
  "signed" verdict vocabulary. Drifted: in-toto Statement shape (M3 signs a
  minimal `{root, identity}` JSON), attestations traveling in export (M3's
  export skips `.reticuli` entirely), declared-content-only export,
  resumable rehydrate (our capstone scar — unforced, absent).
- **authoring** — Crossed: pilot senses condensability, condense accounts C1
  (calls + seconds — M3 satisfied `seconds` by **monkey-patching
  `kernel.cost`** at import), recipe round-trip through `dump_recipe`,
  pack's implementation-free/check-moves-root law. Drifted: **condense
  certifies cold** — docstring only, never asserted; M3's condense trusts
  the trace outright (no clean room, no cold re-run; unsoundness deferred to
  audit). Pack's warm gate runs unjailed in M3 (M1 jails it).
- **agents** — Crossed essentially whole: payload→event mapping (prompt/
  write/read/bash), outside-session and no-session guards, idempotent
  install preserving foreign settings. Drifted: the wired command string
  (`python3 -m reticuli.hooks` vs `ret hook`) — unasserted, free.
- **surface** — Crossed: **exactly the ten verbs the battery drives**, the
  two tree lenses, verdict strings, exit codes, git-native init. Drifted:
  the other ~8 M1 verbs (`export`, `import`, `audit`, `attest`, `pull`,
  `deps`, `anatomy`, `rehydrate`, `cost`) — all evaporated from the CLI
  while surviving as library functions where inner gates force them. The
  regenerated CLI is the literal fixed point of its check.
- **workshop** — Crossed: a passing suite with real teeth (the mutant-seal
  clause), seven compiling scripts, a sweep that plans. Drifted: the entire
  operational meaning of the bench — probe/sweep/envelope came back as
  different species; no script reads any `RETICULI_*` variable; the honest
  experiment pipeline (claim_root stamps, audit-gated landings, specimens)
  is invisible to the claim.
- **vessel** — Crossed: `ret` → `reticuli.cli:main`, install metadata,
  PyPI release workflow, git-native ignore/attributes lines. Drifted /
  Goodhart exhibit: the CI needle `--recursive` satisfied by an English
  **comment** ("re-earns every one of its --recursive(ly) sealed
  components") in a CI that runs no such flag; `.reticuli/liquid/` is
  *gitignored* — "records commit like lockfiles" is prose and didn't cross.
- **reticuli (docs)** — Crossed: word budget, install line, an invariant
  formula, three-machine story, verb-complete + env-complete guide, no
  residue links. Drifted: the README's quickstart shrank to match the
  shrunken CLI (no export/import proof); the guide documents the five-var
  environment contract while **nothing in the codebase reads four of
  them** — the guide even says so itself ("This is the one variable the
  kernel consults today") and attributes `RETICULI_MODEL` to producers that
  hardcode their model. The docs rung forces words, not wiring.

## Structural finding: seeds don't thread up

The flat M3 room contains only the top seed + step outputs. Lower-rung
identity files — the seven inner checks, LICENSE, logo.png — are *seeds* of
their own rungs, and the chain threads only outputs upward. So the assembled
top room is **a valid record but not a functionally self-equivalent repo**:
it cannot re-run its own lower gates and would fail vessel_check in place.
Freeze-dry-to-working-repo needs an explicit assembly step that materializes
every rung's seed set into the final tree.

## How concepts cross (the channel hierarchy)

Observed crossing fidelity, best to worst:

1. **Gate-asserted behavior** — always crosses (that is what landing means).
2. **Prose inside the seed** — often crosses (the check's docstring is
   in-room context: "deterministic tar" became real behavior unasserted;
   `RETICULI_JAILED`'s stated contract shaped a novel mechanism).
3. **Needle words** — the letters cross, the meaning may not (`--recursive`
   in a comment; a true-but-different invariant formula).
4. **Out-of-room prose** (README/guide/design essays) — does not cross at
   all except where a needle demands the words back.

## Triage

**Carve (promote into checks — each edit moves only its rung's root, and each
new clause must reject this specimen while byte-copy stays 8/8, stub 0/8):**
- kernel_check: seed-sensitivity battery (fixture gains `inputs`; edit seed ⇒
  root moves and verify breaks; edit free ⇒ neither).
- kernel_check: tolerance battery (1.5:1 comparable, 4:1 not).
- exchange_check: declared-content leak test (stray file must not travel);
  double-export byte equality; attestations travel.
- authoring_check: cold-certification (a trace whose accepted output does not
  reproduce cold must refuse to condense).
- surface_check: raise the verb floor so the README's proof is executable
  (`export`/`import`/`audit`/`attest` end-to-end) — and fix the stale
  `readme_check.py` reference while the rung is open.
- docs_check: the invariant needle must name the seeds/inputs term.
- Needle hygiene everywhere: assert behavior or structured content, not
  substrings a comment can satisfy.
- rehydrate must re-record the provenance it just used: it threads component
  links but seals without them, so a regenerated room's manifest loses its
  anatomy (`ret tree` on the capstone M3 is shallow; on M1 it is deep). The
  links are in hand at seal time — persist them.
- At the same re-mint: move the eight `*_check.py` seeds into a `checks/`
  directory, making the identity/free boundary physical (tests/ discovers,
  checks/ ratifies — promotion becomes a `git mv` across the boundary).
  Paths are identity, so this is a deliberate all-rung root move; batch it
  with the carve.

**Legitimately free (the freedom the design wants — leave it):** module
internals, the monkey-patch vs built-in architecture, jail fallback
mechanism, statement file layout, CLI prog name, test suite size and style,
hook command string, prose voice throughout.

**M1 candidates for demotion (the basin says they are not the tool):** the
experiment instruments (`probe.py`, `sweep.py`, `envelope.py`) — move to
experiments residue; keep producers claimed and promote the producer
methodology prose to a gate. Reconsider which of the ~8 unforced CLI verbs
are story-critical (force those) vs library-only conveniences.

**M1 defects found by the census:** stale `readme_check.py` in
`surface_check.py:9` (inside an identity seed — fix at the next deliberate
surface re-mint); the `--recursive` CI needle satisfiable by prose.

## Carve executed (2026-09-03)

Every item in the carve list above landed in one deliberate re-mint, plus the
CLI reorganization the census discussion produced: the eight checks moved to
`checks/` (the identity/free boundary made physical), `--help` reorganized
into five process-ordered phase groups (session/author/transfer/redo/compose —
ratified in surface_check), `show` dropped, `deps` folded into `tree` (session
lens now carries the drawer graph), `hook` unlisted, rehydrate now preserves
component provenance in the manifest. New roots, inner to outer: kernel-core
`ebada06f…`, exchange `9ee4b5be…`, authoring `b7610cbb…`, agents `c3b3e782…`,
surface `e88c86e4…`, workshop `95be11f4…`, vessel `14309559…`, whole
`cc1a10e7…`.

Regression discipline held: **every new clause rejects the capstone specimen**
(kernel dies at "editing a dry seed moves the claim"; authoring at "condense
must refuse a verdict it cannot re-earn cold"; surface at the missing phase
sections and verb floor; the docs and vessel needles reject M3's README, guide,
and CI; exchange rejects on API mismatch, its leak clause verified by direct
measurement) — while the committed tree passes all eight gates, the byte-copy
recursive rehydration lands the whole root exactly, a stub producer still
refuses, and `prove` over (repo, imported export, byte-copy redo) returns
`satisfied = true`, all machines audited.

One observation banked for theory: when the surface seed changed in isolation,
only the surface root moved — the whole root held. Rung claims do not
transitively pin the claims below them; the chain binds through component
links and audit, not root composition.

## Limits

One specimen, one model (sonnet, agentic), one run, self-referential subject.
The census enumerates *observed* unforced dimensions; it cannot enumerate the
unobserved ones. Distribution claims need n ≥ 3 and a second model family —
and all divergence language here is **realization diversity / content
divergence**, never evidence of independence.
