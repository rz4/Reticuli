# Tightening the cage — the CEGIS loop, and why convergence isn't monotonic

Follow-up to [cross-vendor-openai.md](cross-vendor-openai.md). The cross-vendor
fuzz found two regions the quirkcalc spec left unspecified (`?` precedence vs
`+`/`-`; negative-left digit-join). This round adds ten tests pinning both, then
**re-runs both vendors** against the tightened spec (`quirkcalc` v2, root
`8bfd3ecb`, 69 tests, reference passes all).

## Result: the targeted gaps closed for both; one vendor fully converged, one didn't

Both producers landed at `8bfd3ecb` (passing all 69 tests, three-machine proven).
Differential fuzz vs the reference, 20,000 random expressions, before vs after:

| implementation | agreement | Δ |
|---|---|---|
| Claude v1 → v2 | 99.89% → **98.06%** | **worse** (388 disagreements) |
| OpenAI v1 → v2 | 96.12% → **100.00%** | fully converged |

The two **targeted** regions are closed for *both* vendors (verified directly):
`51 + 0 ? 3 → 54`, `2 ? 9 - 1 → 8`, `(0-5) ~ 3 → -53`, `(0-136) ~ 6 → -1366` all
now match the reference. The tightening did exactly what it was meant to on the
regions it aimed at.

## Why Claude got *worse*: a fresh draw is a new point in the basin

Claude v2 is not Claude v1 patched — it is an **independent reconstruction** of a
*different* spec. It closed the two pinned gaps and its fresh draw wandered into a
**third** unspecified region the fuzz then exposed (888 cases):

```
5 * 92 ~ 5   →  reference 4625   claude_v2 4605
```

`4625 = 5 * (92~5)` (`~` binds tighter than `*`); `4605 = (5*92) ~ 5` (`~`
looser). But Claude v2 *also* passes the spec's `2 ~ 3 * 4 → 92`, which needs `~`
tighter. **No single precedence table produces both** — so Claude v2's parser is
internally inconsistent: it fit the tested operator combinations without
implementing the uniform rule. My 69 tests pin `~` to the left of `*` but never
`*` to the left of `~`; that asymmetry is the hole, and Claude v2's fresh draw
fell in it while OpenAI's did not.

## The findings

- **Tightening is not monotonic per vendor.** Each rehydration is a fresh draw
  from the basin, so closing gaps A and B does not guarantee the next draw is
  closer everywhere — it can expose gap C. Convergence is a property of the
  *spec's completeness*, approached asymptotically through the CEGIS loop
  (fuzz → pin → re-fuzz → new counterexample), not a one-shot "now it's 100%."
- **The fuzz is load-bearing, not decoration.** Claude v2 passes all 69 tests
  and passes the three-machine test — by every in-band signal it is a perfect
  quirkcalc. Only the differential fuzz reveals it is internally inconsistent on
  an unpinned precedence pairing. Passing the cage is not being the animal; the
  fuzz is what tells them apart.
- **More draws map more of the cage.** v1 exposed two gaps; v2, with two fresh
  draws against the tightened spec, exposed a third (`*` left of `~`) and a
  fourth (a `/0`-ordering edge: `('e','v') x1`). Each vendor, each run, probes
  different silence. The gap map is the union over draws — and it is not
  finished; the next test to add is `("5 * 92 ~ 5", 4625)`.

## The honest shape of it

This is what "the cage is only as tight as the spec" looks like in motion.
Two rounds have closed three-or-four regions and revealed that quirkcalc's tiny
grammar still has unpinned corners. That is not a failure of the model or the
method — it is the method *working*: an independent reconstruction plus a
differential fuzz is a machine for finding the behaviors a test suite forgot to
specify, and it keeps finding them until the spec is complete. For a real
codebase, "complete" is the horizon you move toward, not a place you arrive.

## Status

Measured 2026-09-05. Targeted gaps closed for both vendors; the loop continues
(next counterexample identified). Specimen and its versions live in scratch; this
is the residue.
