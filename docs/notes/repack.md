# The seed repack: why the tight packing is the one we have

Thought residue, 2026-09-03. Answering the standing question: *is there a much
stronger division that will pack the seed as tight as possible?*

## The seed today

1057 lines across eight per-rung checks (`checks/*_check.py`), inner to outer:

    kernel-core 257 · exchange 163 · surface 156 · docs 118 · workshop 110
    · authoring 105 · agents 80 · vessel 68

Two structural facts matter more than the line count:

- **The division is already the phase stratification.** `kernel_check` is the
  *invariant* — the universal laws any Reticuli must satisfy (root = claim,
  seed-sensitivity, free-invisibility, audit earned-not-carried, cost band,
  quarantine, the jail contract, no-network). The other seven are the *product
  profile* — facts about *this* product (its modules and their behavior, its 16
  verbs in 5 sections, its concepts and env contract, its zero-build vessel, its
  import-safe tools). Assertion density falls monotonically from core to skin,
  exactly the solid→liquid→vapor support ordering.
- **There are zero shared seeds.** Each check seals only its own rung. No check
  imports another. This is *why* rung roots don't compose.

## The tempting repack, and its real cost

The obvious tightening: extract the repeated skeleton (`battery()` +
`__main__`/OK epilogue in 8/8, `mkdtemp`/`rmtree` scaffolding in ~6/8) and the
declarative constants (`CONCEPTS`, `ENV_CONTRACT`, `SECTIONS`, `SCRIPTS`, …)
into one shared invariant + profile + interpreter. Prize: roughly 9% fewer
lines and a single readable "what this product is" table.

Cost: it introduces the **first cross-rung seed**. Any check that imports a
shared harness or profile makes that file part of every rung's identity, so
editing it moves *all eight roots*. That regresses **localization** — the
property that:

- round two exploited directly: the kernel clause re-minted kernel-core alone
  (`89651ed8`, seven roots held); the workshop+vessel clauses moved only those
  two (six held);
- the **mint chain** ([[mint-chain-design]]) depends on: it freezes bottom-up,
  one rung at a time, so a disturbance localizes to the floor it entered on.

Trading a proven, load-bearing structural property for a ~9% line reduction is
a bad trade. The genuine cross-rung *fact* duplication is also smaller than it
looks: the section taxonomy appears in `surface_check` (full `--help` headers)
and `docs_check` (bare guide-group words), but those check *different surfaces*
and are not the same strings — deduping them would couple two rungs to buy
nothing.

## Decision

Do **not** centralize. The strongest division compatible with localization,
the mint chain, and soundness is the per-rung phase stratification already in
place. The rungs are bound into one identity at the **mint** (the chain over
the rung roots), not by shared liquid seeds — binding belongs at
solidification, not in the workbench.

Corollaries:
- The harness skeleton stays duplicated on purpose; ~90 lines is the price of
  eight independently re-mintable seeds. Cheaper than the coupling.
- Moving harness machinery into free package code (to dedup without a shared
  *seed*) is rejected on soundness grounds: check machinery must stay pinned,
  or a regenerated harness could weaken a check from inside the basin.
- If a single readable product profile is ever wanted for hand-off, add it as
  an **additive, single-rung, checked artifact** (a machine-readable manifest
  the docs rung seals and a clause asserts true against reality) — never as a
  shared dependency of all checks. That keeps localization while giving the
  "identity as data" view. Deferred; not currently needed.

## What "tighter" still means going forward

Not fewer lines — *less unforced width per pinned byte*. That is the carve and
round two's job (promote prose→gate where honest and payload diverge), and it
stays per-rung and localization-preserving. The seed gets tighter by closing
basin width, not by merging files.
