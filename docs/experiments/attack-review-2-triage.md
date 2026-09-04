# Adversarial review, round two — measured triage

The reviewer's second pass, after round one closed (M2-root, attest drift,
packet binding, elision, fake-solid). Same discipline: every attack **run with
controls** against `main` before being believed. LANDS = the tool does the
unsafe thing / accepts the bad record. Battery: a scratch harness over
`kernel`/`attest`, self-planted fake secrets only, never a real credential.

## Scorecard: 6/6 land

| # | attack | measured result | class |
|---|---|---|---|
| 1 | **`prove M1 M1 M1`** | LANDS — `three_machine(m1,m1,m1)` returns `satisfied=true`; no distinctness reported | concrete |
| 2 | **recipe path escape** | LANDS — `claim()` read `../vault/secret.txt` into the root (a file outside the record) | concrete |
| 3a | **gate reads inherited secret** | LANDS — a jailed gate read `$FAKE_INHERITED_SECRET` from the inherited env and wrote it into its room | hardening |
| 3b | **`RETICULI_JAILED` spoof** | LANDS — with the var preset, `jail()` returns `("inherited", unwrapped cmd)`; no jail applied | hardening |
| 4 | **no execution limits** | LANDS — a `sleep 3` gate ran to completion; no `timeout` in `realize`/`_jailed` | concrete |
| 5 | **forged proof → signed `proven`** | LANDS — a hand-written manifest `proof` yields a signed statement with `proven=true`; no M2/M3 existed | semantic |
| 6 | **any key → solid** | LANDS — minting with an arbitrary untrusted key makes `phase()==solid` (check-novalidate) | semantic |

## Three concrete bugs (forced fixes — unambiguous)

1. **Distinctness (#1).** `three_machine` never requires M1/M2/M3 to be
   distinct paths. Content alone cannot prove independence, but the tool can
   refuse identical paths (and same-inode / same-realpath), and report
   independence as *unestablished* rather than silently implying it. Cheap,
   correct, honest.
2. **Path confinement (#2).** Seed and output names flow into
   `os.path.join(d, value)` / `_copy()` with no "must remain under the record
   root" check — so a hostile recipe reads or writes outside the room *before*
   the gate sandbox is even relevant (confirmed on the read path; the write
   path is the same class). Fix: one canonical boundary validator every recipe
   path passes through — reject absolute paths, `..` escapes, and out-of-root
   symlink targets — at the kernel boundary, once.
3. **Resource bounds (#4).** Gate `subprocess.run()` has no timeout, and no
   output/memory/process ceiling. A record can hang or exhaust the verifier
   without breaking any invariant. Fix: a wall-clock timeout at minimum
   (declarable, with a default), and output truncation; memory/proc caps where
   the platform affords them.

## Two hardening items (a design shape, not a one-liner)

3a. **Quarantine is write-isolated, not secret-isolated.** bwrap read-binds
`/`, seatbelt `(allow default)` allows reads, and the gate inherits
`os.environ` — so a hostile gate can read host files and inherited credentials
and write them into its permitted room, to exfiltrate later at export. Fix
direction: gates start with a **scrubbed environment** and a filesystem
holding only the room plus the runtime files they actually need. *Caveat that
needs a decision:* the self-host **workshop** gate runs `pytest`, which needs
the interpreter, the package, and the lower layers — so "only the room" is too
tight; the minimization has to enumerate what an honest gate legitimately
needs, or self-hosting breaks.

3b. **`RETICULI_JAILED` is trusted as evidence.** The inherited-jail branch
fires on the mere presence of the env var, so a parent environment that sets
it disables the jail (and precedes the `require` refusal). This is the same
tension flagged in round one: the inherited path is load-bearing (the kernel
check re-execs into the host jail and sets it deliberately), so the fix must
distinguish *"our own realize/_rejail set this"* from *"the ambient
environment claims it"* — e.g. an unforgeable token we mint per-run rather than
a fixed string, or refusing to honor it unless we are the ones who set it.

## Two semantic decisions (the architecture — the user's call)

5. **`proven` is `bool(packet["proof"])`, and the proof is unverifiable
   residue.** `freeze_dry` writes a `proof` onto the manifest; anyone can write
   one by hand; `mint` copies `bool(proof)` into the signed statement as
   `proven`. So a forged manifest proof becomes a *signed* `proven=true`. The
   signature is honest about what it covers (the reviewer signed that
   assertion) but the assertion is not locally re-verifiable — M2 and M3 are
   gone by mint time. **Reviewer's fix:** rename `proven` → `proof_recorded`
   unless the proof travels in a verifiable form.
6. **"Solid" via any key.** `minted()` uses `check-novalidate`, so *any* intact
   signature — any key, no allow-list — flips `phase()` to solid. Coherent if
   solid means *cryptographically frozen*; incoherent if solid is meant to be
   the *trusted-human authorization* boundary we have been building toward.

**The reviewer's synthesis (and it is the right frame):** proof and
authorization have become two independent facts —
`{unproven, proven} × {unauthorized, authorized}` — and should stay a 2×2
lattice, not be collapsed back into one liquid/solid axis. "It reproduced" and
"a human accepts it" are different claims; the design *discovered* their
independence and should keep it.

## What NOT to solve

**The environment-interpretation problem.** `python3 check.py` denotes
Python + libraries + OS + arch + env; the gate inherits the host runtime. The
root identifies the *declared predicate*, not the universe that interprets it.
Recursively sealing reality would destroy the system's simplicity. The right
move is to *state the interpretation boundary precisely* in the guide (already
begun: the quarantine backend is on the ledger, the honesty contract names the
execution boundary) — not to try to hash it.

## Status

Measured 2026-09-04. Nothing carved — this triage is the specimen set and the
decision memo. The three concrete fixes are unambiguous; #3 needs a
minimization scope; #5/#6 are the (possibly final) architectural decision
about the proof/authorization lattice.
