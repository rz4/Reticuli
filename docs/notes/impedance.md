# Impedance: the spec, the load, and the center of the chart

A record is an **impedance-matching problem**. The dead center of a Smith chart
is normalized impedance `1 + j0`, reflection coefficient `Γ = 0`: perfect match,
100% of the energy absorbed by the load, nothing bounced back — no echo, no
standing wave, no wasted heat. The source's intent becomes the destination's
reality with zero loss. Reticuli's **basin of attraction** is that center, for
information instead of radio waves.

| RF | Reticuli |
|---|---|
| source | the invariant claim — the checks, the dry seeds |
| load | the receiver's environment — their model, their hardware |
| reflection / loss | hallucinations, syntax errors, wasted calls, burned USD |
| tuning circuit | the cost ledger — it drives the system off the chaotic edge toward center |
| `Γ = 0`, dead center | one-shot rehydration, minimal cost, exact roots — zero reflection |

Rehydrating a spec across a latent network is matching the impedance of your
intent to the reality of someone else's machine. A sloppy spec is a mismatch:
the model bounces off the gates, burns compute, and reflects the energy back as
errors. A claim-grade spec is a conjugate match: the idea lands in the load with
nothing reflected. **You don't match by buying a bigger load — you tune the
source.** *(Framing: R. Zamora Resendiz.)*

## A two-point reading (Haiku 4.5, 2026-09-02)

The minimal-cost probe — the cheapest capable load, one blind call per file — is
a Smith-chart measurement. Two points came back:

- **kernel-core: dead center.** Haiku regrew the entire invariant from
  `kernel_check.py` alone and its kernel hashed to the *exact* committed root
  `af831de0…` — `Γ = 0` — for **$0.139** (2 calls, 20,587 tokens). The innermost
  spec travels for fourteen cents. This is the whole thesis in one number: a
  claim-grade check is a matched source, and the idea lands in the cheapest load
  with zero reflection.

- **exchange: a reflection at an unspecified seam.** The next rung bounced.
  Haiku's kernel — legal, minimal, root-exact — implements `seal(d, proof=None)`
  and stops there, because `kernel_check.py` never exercises component links.
  But the exchange layer calls `seal(app, components=links)`, and the redo
  reflected: `TypeError: seal() got an unexpected keyword argument 'components'`.

The reflection is the finding. It happened at a point where the source impedance
was **undefined** — `seal`'s component interface is used by exchange but not
pinned by the kernel's own check, so the match there was left to chance. A
stronger (pricier) load would have guessed the fuller interface and hidden the
mismatch. The cheap load exposed it. The impedance-matching fix is not a bigger
model — it is to **tune the source**: pin the seam in `kernel_check.py` so the
kernel basin is exactly the set of kernels that can carry the stack above them.
That re-mints the chain (a check moved), and the next probe measures whether the
cheapest load now reaches center on more rungs.

The visual companion is [`basin_lagrange.png`](../experiments/basin_lagrange.png): ζ¹ and ζ²
Reticuli as two wells, the spec at the saddle between them. Same center, two
languages — the gravitational L1 and the electrical `Γ = 0`.
