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

## Round three — the loop converges

v3 (75 tests) pinned the third gap in *both* orderings (`~` tighter than `*`/`/`
whether `~` is on the left or the right — v2 had only pinned it on the left,
which is the asymmetry Claude v2 fell into). Both vendors re-ran; both landed at
root `df6311f3`. The full three-round convergence, each vendor's fresh draw
fuzzed against the reference over 20,000 random expressions:

| round | tests | claude | openai |
|---|---|---|---|
| v1 | 59 | 99.89% | 96.12% |
| v2 | 69 | 98.06% | 100.00% |
| v3 | 75 | **100.00%** | **100.00%** |

Zero residual disagreements for either vendor at v3. Sixteen tests, added in two
rounds strictly in response to fuzz counterexamples, drove two **independent**
reconstructions to exact agreement with the reference everywhere the fuzz probes.
The non-monotonic dip at v2/claude is the signature of the method, not a flaw:
each round is a fresh draw, so closing two gaps can expose a third, and the loop
runs until the draws stop diverging.

## What converged, and what "converged" honestly means

- **The CEGIS loop terminated (empirically).** fuzz → pin → re-fuzz, three
  rounds, ended with both vendors at 100% over 20k random inputs. For a grammar
  this small the spec is now, to the resolution of the fuzz, complete.
- **"100% over 20k random exprs" is strong evidence, not proof.** The fuzz is a
  sampler; a rarer region could still hide. One did earlier — a `/0`-evaluation-
  order edge (`15 / 0` inside a `?`/max branch) showed at ~1-in-60k in round two
  and did not surface in the v3 sample. Convergence here means "no divergence
  found," which is the honest ceiling of differential testing. Proof would need
  a formal spec (the gate-as-proof-checker rung on the reach ladder).
- **The reference is the canonical implementation** (authored with the language),
  so "agrees with reference" = "implements quirkcalc as defined." Two vendors now
  do, from the tests alone.

The whole exhibit, in one line: an invented language, reconstructed by two
independent vendors from its tests, was driven to cross-vendor behavioral
identity by three rounds of differential-fuzz-guided test authoring — the cage
tightened until the basin, on everything measured, collapsed to a point.

## Status

Measured 2026-09-05. Loop converged (both vendors 100% over 20k at v3, root
`df6311f3`); the one known rarer edge (`/0` ordering) remains below the fuzz's
resolution and is noted, not closed. Specimen versions live in scratch; this is
the residue.
