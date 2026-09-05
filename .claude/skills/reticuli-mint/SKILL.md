---
name: reticuli-mint
description: Use when a Reticuli record is ready to be authorized/frozen (made solid), or when checking existing authorizations. CRITICAL — an agent PREPARES and VERIFIES the ceremony only; it must NEVER sign. The mint/attest signatures are the human keyholder's act, with the human's own key. Read this skill before touching `ret mint` or `ret attest`.
---

# The mint ceremony — the human boundary

Minting is **accountable authorization after a defined ceremony**: a named
keyholder vouches that they reviewed a record and authorize freezing it. It is
the top of the trust ladder and the one act in the whole system an agent must not
perform.

## The hard rule

**NEVER run `ret mint <record> --key ...` or `ret attest <record> --key ...`.**

Signing with a key is the human's act with the human's own SSH key. An agent that
signs has forged an authorization — the exact thing the design exists to prevent.
When a record is ready, **stop and hand the signing to the human.** Do not offer
to run it "for them," do not use a throwaway key to "demonstrate," do not sign in
a scratch copy. Prepare, verify, and hand off.

> If `ret` is not on PATH, use `python3 -m reticuli`.

## What an agent MAY do

- **Assemble the review packet** (no `--key`): `ret mint <record>`. This shows
  exactly what a keyholder would authorize — the claim root, the chain (mint)
  root, the realization digest, the normalized recipe, the seed digests, the gate
  sources, the component chain, and a fresh audit. Present this for review.
- **Verify existing authorizations** (report only):
  - `ret mint <record> --check --signers <allowed_signers>` — does a trusted
    signer's authorization still hold over the recomputed chain and bound packet?
  - `ret attest <record> --check --signers <allowed_signers>` — do the
    attestations verify?
  - Without `--signers`, `--check` only reports `intact`, never `trusted`.
- **Confirm readiness first:** `ret audit <record>` earned, and the three-machine
  test satisfied (see reticuli-verify). `mint` refuses a record whose verdicts
  don't reproduce.

## Then hand off

Tell the human the exact command to run themselves, e.g.:

```
ret mint . --key ~/.ssh/id_ed25519 --as you@lab.gov
```

and stop there.

## What "solid" means (so you don't overstate)

Solid = **authorized** (a signature that verifies against the verifier's trust
anchor — an unknown key is not authorized) **AND proven** (a recorded
three-machine proof). The two are independent facts; a mint over an unproven
record is honest about being unproven. Phase is verifier-relative: a record is
solid *to you* only against *your* allowed-signers.

Depth: `docs/guide.md` (Minting; the trust ladder).
