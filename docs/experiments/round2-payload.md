# Round two, payload 1: the phone-home kernel

The census measured *natural* drift — what an honest producer does differently
when the spec is silent. Round two measures *adversarial* capacity: can a
crafted realization pass every gate, land the exact root, and still carry
behavior the checks never exercised? This is the first payload — aimed at the
deepest, sharpest stratum, the kernel — and it doubles as the negative control
for the free clause it motivated.

## The payload

The committed `reticuli/kernel.py`, byte-for-byte, plus two lines: `import
urllib.request` (an egress channel) and, inside `seal`, a write of a
`beacon.txt` marker on every seal. Free code — the kernel-core rung's seed is
`kernel_check.py`, and `kernel.py` is a free `produce` step. Specimen:
`specimens/round2/kernel-phonehome.py.txt`.

## Measured (the payload kernel executed live, not merely inspected)

1. **Root-invisible.** The honest kernel and the payload kernel seal the same
   fixture to the *same root* — `root = hash(recipe + seeds + verdicts)` never
   sees free bytes. That freedom is the basin; it is also the attack surface.
2. **Audit-clean.** `audit` re-runs the gates and the pinned verdicts
   reproduce — the payload behaves correctly on everything tested, so the deep
   check passes too. Rungs 1 and 2 of the trust ladder (root match, audit) do
   not see it.
3. **The side effect fires.** The beacon is written on `seal` — a real
   behavioral divergence on a documented operation, invisible to identity.
4. **The free clause separates them.** A static import check over the kernel
   stratum: every honest kernel we hold imports no network module; the payload
   imports `urllib`. Honest → admitted, payload → rejected. Zero honest width
   spent (the divergence rule), one egress channel closed.

## What it proves, and what it does not

It confirms the trust model the ladder documents: a **liquid** root is a claim
about the checks, never about the implementation, and neither root-match nor
audit closes the payload class. The free clause narrows the easy channel in
the deepest stratum — it does **not** seal it (`subprocess` remains, and a
determined payload can shell out; the guide says so). The honest answers to
the residual are the higher rungs — **attestation** (trust a named signer) and
the **solid mint** (frozen, ceremony-signed bytes, per the mint chain).

## Standing (round two is not finished)

This is payload 1 of the program. Remaining: a workshop-stratum payload (a
benign side effect on a documented op, where `subprocess`/network are
legitimate so the free clause does not apply — the hard case), a vessel-stratum
payload, and the reviewer's independent attempt against the frozen export. Each
survivor that no property separates from the honest corpus is a payload the
ladder must answer rather than a clause — that distinction is the experiment's
actual output.
