# The landscape: prior art and impact

*A survey as of September 2026. Landscape claims rot; re-check before citing.*

Nothing found does what Reticuli does, but it sits at the intersection of three
mature fields, each of which owns a piece of it. The move that appears genuinely
novel is the identity construction: `root = hash(recipe + checks + verdicts)`
with the implementation *excluded*, so validator-equivalence collapses into hash
equality and "independent re-realization" becomes a mechanically checkable
predicate — **claim-addressed computation** (a term owed to the project's first
external review): content-addressing the invariant an artifact must satisfy
instead of the artifact's particular bytes. Nothing found content-addresses the
*acceptance conditions* as the artifact's identity. Identity is deliberately
weaker than evidence: root equality alone can be carried, which is why prove
audits (re-runs) the gates, and why independence itself remains a provenance
property for attestation and witnessing, not hashing.

## Neighbors

**Byte-identity and provenance — mature, booming, and inverted from Reticuli.**
Git, [Software Heritage SWHIDs](https://en.wikipedia.org/wiki/SoftWare_Hash_IDentifier),
reproducible-builds, and Nix/Guix bind identity to bytes. The supply-chain stack
— [SLSA + in-toto attestations](https://slsa.dev/spec/v1.1/faq), sigstore,
GitHub artifact attestations (default-on for public repos through 2026), and
attested-build research like [Kettle](https://arxiv.org/pdf/2605.08363) — binds
*events* to bytes: "these bytes came from this process on this machine."
Reticuli answers the complementary question: "what claim do these bytes satisfy,
and can anyone re-derive it without them?" SLSA's own FAQ defines "verified
reproducible" as independent build platforms corroborating a build — the closest
protocol ancestor (alongside Wheeler's diverse double-compiling) — but it
demands equivalent *outputs*, where Reticuli deliberately lets outputs diverge.
Unison is the mirror image: it content-addresses normalized implementations;
Reticuli content-addresses everything *but* the implementation.

**Spec-driven development — culturally closest, missing the invariant.** By
2026 a full movement ([GitHub Spec Kit, AWS Kiro, BMAD, and SDD modes in every
major coding agent](https://www.augmentcode.com/tools/best-spec-driven-development-tools))
is built on "the spec is the source of truth; regenerate the code." That is
Reticuli's worldview, but SDD has no identity layer: no hash, no equality test,
no certification protocol, no answer to "did the regeneration land on the same
thing?" Reticuli is what SDD becomes if you make its central slogan
*falsifiable*. That is both the opportunity (a huge adjacent audience that
already believes the premise) and the sharpest prior-art risk (that ecosystem
will eventually want exactly this lockfile).

**Scientific reproducibility — where the three-machine test already has a
name.** The mapping onto [ACM's artifact badges](https://www.acm.org/publications/policies/artifact-review-and-badging-current)
is almost exact: M2 is "Results Reproduced" (independent party, author's
artifacts), M3 is "Results Replicated" (independent party, *without* the
author's artifacts), and ACM even requires agreement "within a tolerance deemed
acceptable" — the declared-tolerance clause. Those badges are awarded today by
human committees reading READMEs; nothing mechanizes them, and Replicated is
rarely attempted because it is expensive. A live-model M3 is, in ACM
vocabulary, *automated replication*.

Opposite attack, same problem: [Thinking Machines' work on defeating LLM
inference nondeterminism](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
makes the oracle deterministic. Reticuli's bet is the inverse and likely the
more durable one: let the oracle vary, pin the claim.

## Impact, if it lands

Near-term: agent work becomes *cacheable, portable residue* — review shifts
from reading diffs to auditing gates; "regenerate under a better model" becomes
a routine operation with an invariant to certify against; dependencies can be
pulled as claims rather than bytes. For science: the root is a citable identity
for a computational result, and the three-machine test is a mechanizable
artifact badge. For capability claims, the white paper's framing is the deep
one: a falsifiable standard that replaces demo-as-evidence with
residue-as-evidence.

## The limits that will decide it

- **The basin is exactly as meaningful as the check.** Root equality certifies
  *claim*-equivalence, not semantic safety; an underspecified gate admits a
  backdoored implementation into the same basin as an honest one. As
  supply-chain infrastructure this is an identity layer, not a trust guarantee —
  strength scales with validator strength, and the hard human work relocates to
  writing claim-grade checkers (arguably the point).
- **Gate execution is jailed and key-attested, not witnessed.** Gates run
  quarantined (seatbelt/bwrap: writes confined to the room, network denied,
  the ledger records the jail), and a realization can carry `ssh-keygen -Y`
  signed in-toto statements (`ret attest`) so a verifier can trust a redo they
  didn't run, anchored to allowed signers. What remains open is *witnessed*
  execution — a signature says who vouches, not where the gate actually ran;
  TEE/transparency-log composition (Kettle-style, sigstore) is the remaining
  hardening, and would make the ecosystems complementary rather than
  competing.
- **The cost ledger is honest accounting, not adversarially robust.** Producers
  self-report tokens; call-counting is coarse.

Every live-model rehydration that lands in the basin is evidence for the "check
is the claim" thesis that none of the neighbors above can produce — each run
measures whether the checks are a *sufficient genome* for the claim they seal.

## Sources

- [ACM Artifact Review & Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current)
- [SLSA FAQ](https://slsa.dev/spec/v1.1/faq) · [SLSA provenance model](https://slsa.dev/spec/v0.1/provenance)
- [Kettle: attested builds for verifiable software provenance](https://arxiv.org/pdf/2605.08363)
- [Spec-driven development tools, 2026](https://www.augmentcode.com/tools/best-spec-driven-development-tools) · [SDD guide](https://www.thebcms.com/blog/spec-driven-development/)
- [Thinking Machines: Defeating Nondeterminism in LLM Inference](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
- [SoftWare Hash IDentifier (SWHID)](https://en.wikipedia.org/wiki/SoftWare_Hash_IDentifier)
