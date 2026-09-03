# The mint chain: freezing on a schedule, bottom-first

Thought residue from the carve's theory round (2026-09-03). Design agreed,
implementation deliberately deferred to the human-boundary step; the mint
stays held until the repo is annealed to flight stage.

## The observation that forced it

Rung roots do not compose. When the surface check changed in isolation, only
the surface root moved — the whole-repo root held. Each root is a per-node
content address; the links between rungs carry exact roots but live in
manifest metadata, outside every hash. So the top root cannot testify to
anything beneath it (attested linkage, enforced at check time by audit), and
— worse — free bytes are invisible to every root, so an upper layer can ship
a mutant realization of a lower layer and move nothing at all. That is the
workshop-payload attack, confirmed empirically: a poisoned producer landed
the same root.

## The three-way picture

- **git**: everything is always frozen. Any byte ripples to the commit —
  total detection, no liquid phase. Git cannot tell a claim edit from an
  honest refactor; every change churns identity. The basin was invented to
  avoid exactly this.
- **Reticuli today**: only claims ever freeze. Free bytes flow under stable
  roots — that is the feature — but there is no solid phase for bytes, so a
  chosen realization cannot be pinned and payloads pass silently.
- **The mint chain**: claims freeze in liquid; bytes freeze at the mint;
  freezing proceeds bottom-up and the bottom freezes hardest.

## The structure

A fold from the kernel upward, not a flat hash over the eight roots:

    m_kernel = H( r_kernel ‖ D_kernel )
    m_i      = H( r_i ‖ D_i ‖ m_below )        for each rung above
    sign( m_whole )                             at the ceremony

where `r_i` is the rung's claim root (unchanged, liquid mechanics untouched)
and `D_i` is the rung's **realization digest** — the bytes of its own
stratum, free water included. The boundary taxonomy already assigns every
file to exactly one owning rung, so the partition exists. A solid is one
chosen crystal out of the basin, frozen byte for byte.

## Properties

1. **Big-endian identity.** The kernel mint is the genesis and the most
   significant digit; nothing above can move it. Zero Kelvin at the bottom.
2. **Upward-only ripple with localization.** A disturbance at height k
   shifts every mint from k upward and none below. The lowest hot
   thermometer names the floor where energy entered — tamper-evidence *and*
   tamper-localization.
3. **The payload gap closes for minted artifacts.** A swapped free file
   keeps every root (same claim) but shifts its layer's D, so the chain goes
   hot from that floor up and the signature over m_whole goes stale.
4. **Progressive annealing.** Layers mint bottom-up; "flight stage" is a
   height — how far the frost line has climbed. Lower strata can be solid
   while upper strata stay liquid workbench.
5. **Melting stays possible, never silent.** A deliberate claim edit is
   authorship: re-mint and re-sign, ceremonially gated. Thermal noise —
   drift, payloads, quiet swaps — cannot enter undetected.

Diagram: the "Merkle Spine" sheet (interactive; three binding models, four
edit experiments). The signing ceremony should sign m_whole — the chain, not
just the top root — which slots this directly into the review-packet /
claim-signing design for the human boundary.
