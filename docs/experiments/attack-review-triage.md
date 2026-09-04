# Adversarial review — measured triage

An external adversarial review of the public repo (at `024f7d9`) named five
regression attacks and a wider catalog. Discipline: every named attack was
**run, with controls**, before being believed — honest fixture accepted first,
then the reviewer's mutation applied, and the tool's verdict recorded. LANDS =
the tool accepts the attacked record. Battery: a scratch harness over
`kernel`/`attest`/`registry` with ephemeral throwaway keys.

## Scorecard: 6/6 land

| # | attack | measured result |
|---|---|---|
| 1 | **M2 root substitution** | LANDS — doctored M2 recipe (different claim, byte-identical outputs): `satisfied=True` with `root(M2) ≠ root(M1)` |
| 2 | **Fake-solid injection** | LANDS — `"proof"` written into manifest by hand: `phase=solid`, `verify.ok=True` |
| 3 | **Attestation drift** | LANDS — free output swapped after signing: signed output hashes no longer match disk, `attest.check ok=True` |
| 4 | **Packet substitution** | LANDS — review packet forged: `mint_check ok=True`; packet deleted: still `ok=True` |
| 5a | **Mint without proof** | LANDS — liquid record, no three-machine test ever run: `mint()` signs, ceremony completes |
| 5b | **Missing-component elision** | LANDS — declared component removed from registry: `mint_root` silently folds a different chain root (`1933f81c` → `25a847b9`), no refusal |

## Mechanism and fix class, per attack

1. **M2 root.** `three_machine` computes all three roots but tests only
   `roots["M3"] == roots["M1"]`; M2 is held to byte-reuse (`_outputs`) and
   self-integrity. The docstring says "all three share a root" — the code
   contradicts its own claim. **Forced fix**: equivalence over the root *set*.
2. **Fake-solid.** `phase()` = truthy `manifest["proof"]`, and the manifest is
   metadata outside the root. Also strippable (downgrade). **Design fork**:
   what "solid" verifiably means locally — see below.
3. **Attestation drift.** `check()` verifies the signature and that the
   statement names the current root — but never compares the statement's signed
   `outputs` hashes to the bytes on disk. Free bytes are outside the root by
   design, so the realization can drift under an attestation that says "this
   realization." **Forced fix**: check signed outputs against disk; a
   byte-different realization *should* invalidate an attestation.
4. **Packet substitution.** The signature binds `packet_digest`, but
   `mint_check()` never re-hashes the stored packet (or notices its absence).
   The packet is the answer to the confused-deputy problem; unbound, it is
   decoration. **Forced fix**: recompute the packet digest, fail on mismatch
   or absence.
5. **Mint-without-proof.** `mint()` requires `audit` only — deliberate
   separation of authorization from proof (the authorized/proven distinction).
   The defect is that nothing in the signed statement *says* whether a proof
   existed. **Design fork**: keep the separation but make the signed statement
   carry proof status, or couple mint to a passing three-machine test.
6. **Elision.** `mint_root`'s `if cr in by_root` drops missing components;
   `rehydrate` in the same file refuses loudly for the same condition.
   **Forced fix**: refuse, like rehydrate.

## The rest of the catalog, by code reading (not yet battery-run)

- **`RETICULI_JAILED` bypass** — confirmed: the inherited-jail check precedes
  the `require` refusal, so an externally set env var suppresses jail creation
  even under `require`. The inherited path is load-bearing (self-hosted checks
  re-exec into the jail), so the fix must distinguish "our jail set this" from
  "the environment claims it."
- **`auto` → `none` fallback** — confirmed and documented; a hostile record's
  gates run unjailed on platforms without a jail. Honest ledger, real risk.
- **bwrap read-binds `/`** — confirmed: a jailed gate can read host files and
  copy them into its own record output; the secret exfiltrates at export.
  Same class on darwin (seatbelt profile allows default + denies write/net).
- **No resource limits on gates** — confirmed: no timeout, no output caps,
  whole-file hashing; sandbox denial (loops, bombs, giant files) is open.
- **Cost `None`-passes** — confirmed and *documented as intentional*
  ("reported, not failed"); consequence: stripping a ledger converts an
  unfavorable comparison into unmeasured. Cost stays residue; any statement
  built on it needs accounting scope.
- **Manifest metadata (name/components) unauthenticated** — confirmed;
  partially deliberate (components are provenance outside the claim). The
  mint packet already binds `components` — fixing #4 authenticates ancestry
  *for solid records*. The displayed manifest `name` can silently disagree
  with the recipe's (which is in the root).
- **Same-root component ambiguity** — real design gap: component links pin
  claim roots, but a mint freezes one *realization*; two same-root
  realizations are indistinguishable to `mint_root`'s resolver. Liquid
  identity follows claim roots; solid identity must follow mints. The solid
  DAG needs component-mint pins, not just component-claim pins.

## The philosophical strata (correctly outside the battery)

The review's deepest points are not implementation defects and cannot be
fixed by carving; they are the trust ladder's territory, and the repo should
say so more sharply than it does:

- **The checker is not the predicate.** `python3 checker.py` is interpreted
  by an implicit environment (interpreter, imports, PATH, libc, platform).
  Two machines with one root can denote two predicates. The root is the
  *textual specification* of a claim under an interpretation boundary that
  must be explicitly declared, not assumed.
- **Checker adequacy is not provable.** Vacuous, weak, or Goodhart-satisfiable
  checks pass their own gates. The irreducible human act is **adoption of the
  predicate** — "these checks are an acceptable operational definition of my
  claim" — not acceptance of a green VERIFIED.
- **Independence is graded** (content / process / machine / toolchain /
  vendor / epistemic) and none of it is currently witnessed. Producers
  deliberately run unjailed; an M3 producer can find M1 on the same host.
- **Adaptive attacks**: iterate-until-pass changes what "it passed" means for
  stochastic gates; discarded-redo selection hides the attempt distribution.
  Attempt history is epistemically relevant residue.

The review's proposed statement of what a Reticuli proof establishes — an
explicitly identified predicate, under an explicitly identified execution
boundary, independently satisfied, with authorization referring to the exact
predicate and realization reviewed — is adoptable nearly verbatim as the
guide's honesty contract.

## Status

Measured 2026-09-04. Fixes not yet applied — each is its own deliberate
re-mint with specimen validation (the battery above is the specimen set).

## Carve executed (2026-09-04): 6/6 flip to WALL

All four forced fixes and both fork decisions carved in one deliberate
re-mint; the battery re-run refuses every attack, controls intact.

- **Equivalence is the root set** — `three_machine` now requires one root
  across all three machines; the doctored-M2 clause lives in the kernel claim.
- **Attestations pin the realization** — `attest.check` compares the signed
  output hashes to the disk; drift refuses, exact restoration re-earns. Clause
  in exchange.
- **The packet is bound** — `mint_check` re-hashes the stored review packet
  against the signed digest; forged or missing refuses, and the record demotes
  from solid. Clause in exchange.
- **The fold refuses elision** — `mint_root` raises on a declared component
  missing from the registry, exactly as `rehydrate` always did. Clause in
  exchange.
- **Fork 1 — solid is a verifiable authorization.** `kernel.phase` = solid iff
  `kernel.minted()` holds: an intact signature (`ssh-keygen -Y
  check-novalidate`) over a statement naming the sealed root, whose packet
  digest binds the stored packet, whose realization digest still describes the
  bytes on disk. An injected `proof`, unsigned-but-coherent mint material, and
  post-mint drift all leave the record liquid; the exact frozen bytes restored
  make it solid again — measured in the kernel clause with an ephemeral key.
  `freeze_dry` now *records the proof* (result key `proven`, residue on the
  manifest) and never flips phase; registry reporting (records/pull/anatomy/
  deps) follows `kernel.phase`, never the manifest bit. Signer *identity* and
  cross-component chain remain `attest.mint_check`'s (exchange).
- **Fork 2 — the ceremony carries proof status.** The review packet includes
  the recorded `proof` (or null) and the signed statement carries
  `proven: bool` — bound by the packet digest, surfaced by `mint --check` —
  so an authorization can never be mistaken for a three-machine proof.

Localization: kernel-core `3da9a0d9…` → `669636b2…` and exchange
`844d6f8d…` → `5e6aa4d0…` (the two rungs whose claims changed); authoring
through vessel and the whole root `cc1a10e7…` held. Bench suite 48-pass,
byte-copy rehearsal satisfied/audited on all three machines at the new
claims, stub refused at the genesis gate. The guide now states the solid
semantics, the drift rule, and the adversarial honesty contract (what a
proof establishes — and the five things it does not say).
