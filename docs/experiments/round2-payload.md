# Round two: adversarial payloads, and where clauses end

The census measured *natural* drift — what an honest producer does differently
when the spec is silent. Round two measures *adversarial* capacity: can a
crafted realization pass every gate, land the exact root, audit clean, and
still carry behavior the checks never exercise? Three payloads, one per stratum
with a distinct capability profile. Each payload kernel/script was executed
live, not merely inspected.

Every payload shares the same first three properties — that is the point of the
trust ladder, now shown three times:

- **root-invisible** — `root = hash(recipe + seeds + verdicts)` never sees free
  bytes, so the payload lands the committed root exactly.
- **gate-blind** — the rung's gate does not exercise the malice (it compiles,
  parses, or runs a different code path).
- **audit-clean** where the gate is behavioral — the verdicts reproduce.

What differs between strata is **separability**: whether any static property
divides the payload from every honest realization. That is the whole result.

## Payload 1 — kernel: phone-home. SEPARABLE (clause added).

The committed `kernel.py` plus `import urllib.request` and a beacon write on
`seal`. Lands the identical root, audits clean, side effect fires. But the
kernel needs **no** dangerous capability — no honest kernel networks — so the
payload's `urllib` import separates it from the entire honest corpus.

→ Promoted to a check: `kernel_check.py` now asserts the kernel stratum is
stdlib-only and imports no network module. Zero basin width (every honest
kernel already satisfies it), one egress channel closed. Committed.

## Payload 2 — workshop: poisoned producer. INSEPARABLE at the core.

`producer_claude.py` plus one line: exfil the environment over `subprocess`,
the exact channel the producer already uses to spawn the `claude` CLI. Fires on
module load, before `main`. Measured:

- root-invisible ✓  · workshop root held byte-for-byte.
- gate-blind ✓  · `workshop_check` only `py_compile`s the scripts — it never
  imports or runs a producer, so the exfil is dormant when the gate checks it.
- **import sets IDENTICAL** ✓ · honest and poison both import exactly
  `{json, os, re, subprocess, sys, tomllib}`. The free-clause approach cannot
  fire: the capability the malice uses (`subprocess` → network) **is** the
  capability the honest producer needs.

This is the irreducible case. The producer is an autonomous agent that runs on
the user's machine with full privilege, by design. No import allowlist
separates a producer that sends the prompt to the API from one that sends the
prompt *and* the secrets, because both legitimately reach the network. Worse,
a producer can write a **backdoor into the code it generates** — output that is
itself a basin-valid realization, passing every downstream gate. No gate
catches that; it is a payload *inside* the basin.

- **Partial wall (added).** The producers were refactored to be *import-safe* —
  all work moved into `main()`, so importing a producer has no side effects — and
  `workshop_check` now asserts every tool's module body only *defines* (imports,
  constants, defs, the `__main__` guard, the `sys.path` bootstrap). A top-level
  statement that does work is rejected. This removes the import-time attack
  surface entirely: the specimen's top-level exfil call is flagged (honest tools
  admitted, `_import_offender` = None for all seven; the payload's `_sp.run(...)`
  named). It is a *partial* wall by design — it forces all behavior onto the
  invoked path; it does not vouch for what happens there. (Harness note: the full
  workshop gate cannot be exercised from a bare `cp` of the drawer — its suite
  includes `test_repo_is_a_fresh_layered_self_record`, which only holds at the
  real repo root or under a proper recursive rehydration. The clause was
  validated in isolation and integrated at the root via the re-mint.)
- **Irreducible core (ladder-owned):** exfil over the legitimate API channel,
  malice on the real (paid, keyed) execution path the gate can't run, and
  backdoors in basin-valid generated output. No property separates these from
  honest producers. The honest answers are the higher rungs — **attestation**
  (trust the named author/runner of the producer) and reading the code. The
  mint chain freezes a producer's *bytes* post-mint, but freezing a producer
  that was poisoned from the start freezes a poisoned crystal; the producer
  specifically requires trusting its author.

## Payload 3 — vessel: build hook. SEPARABLE (clause candidate).

`pyproject.toml` plus `[tool.hatch.build.hooks.custom]` pointing at a
`build_hook.py` that runs `os.system(...)` at build/install — the classic
supply-chain vector, and it fires on the very `pip install "git+https://…"`
path this project ships on. Lands the vessel root, `vessel_check` passes (it
parses `[project]`, never builds). But every honest vessel is a plain
hatchling declaration with **no** build hooks, so the payload separates.

→ Clause added: `vessel_check` asserts `build-backend == "hatchling.build"`, no
`[tool.hatch.build.hooks]`, and no `setup.py`/`setup.cfg` — rejecting both a
build-hook and a `setup.py` payload, admitting the committed vessel. Nearly free
today (the package is deliberately zero-build); the small cost is foreclosing
future build customization, which a deliberate re-mint would restore.

## The synthesis: separability tracks capability

The divergence rule partitions the strata by the capability their honest
realizations require:

| stratum | honest capability | payload capability | separable? | answer |
|---|---|---|---|---|
| kernel | none dangerous | network | **yes** | clause added (stdlib/no-network) |
| vessel | none at build | build-time code | **yes** | clause added (no build hooks / setup.py) |
| workshop | network + subprocess | the same | **partly** | import-safety wall added + ladder for the core |

Where honest realizations need no dangerous capability, a clause is free and
closes the channel. Where honest realizations need the exact capability the
malice uses, no gate can separate good from evil — and the trust ladder
(attestation, solid mint) is not a fallback, it is the *only* correct answer.
The producer stratum is irreducibly a trusted authority; trusting it is a human
act, which is precisely what the human boundary is being built to make
accountable.

## Standing

Payloads 1–3 measured; all three admissible clauses now minted — kernel
(stdlib/no-network), vessel (no build hooks / setup.py), workshop (import-safety
of the tools). The producers were made import-safe (work in `main()`) as the
prerequisite for the workshop clause. What remains is genuinely ladder-owned and
un-clausable: a producer's conduct on its invoked path, and the reviewer's
independent attempt against the frozen export. Specimens under
`specimens/round2/` (gitignored).
