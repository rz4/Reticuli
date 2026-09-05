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

## Decisions (2026-09-04)

- **State model:** keep the single liquid/solid axis; **solid** = *authorized
  AND proof_recorded* (couple the two facts back, one word).
- **Authorized means a trusted signer:** the top rung requires the signature to
  verify against an allow-list identity (verifier-relative); an unknown key is
  *frozen/signed*, never *authorized*.
- **Scope:** the concrete fixes now (round A); the design pair next (round B).

## Round A carved (2026-09-04): #1, #2, #4 → WALL

Three complete fixes, all in the kernel claim (so only the kernel-core root
moved), each rejecting its battery specimen with controls intact:

- **Distinctness (#1).** `three_machine` refuses aliased paths (by `realpath`,
  catching symlink and `.`/`..` aliases) and reports
  `independence = "unestablished"` — content cannot prove M3 was not copied.
  `prove M1 M1 M1` now raises.
- **Path confinement (#2).** One boundary, `kernel._safe(root, name)`, that
  every recipe-declared path (seed, output) crosses in claim/realize/audit/
  attest — absolute, `..`, and out-of-root symlink targets are refused before
  any gate runs. `claim()` on a `../` or `/etc/...` seed now raises.
- **Resource bounds (#4).** `_run_bounded` gives every gate a wall-clock
  ceiling (`[record] gate_timeout`, capped by `RETICULI_GATE_TIMEOUT`, default
  300s) and kills the whole process group on expiry — a timeout is a failed
  verdict (returncode 124), not a hang. A `sleep` gate under a 1s ceiling is
  killed.

Localization: kernel-core `669636b2…` → `f9b01054…`; exchange and every rung
above, plus the whole root `cc1a10e7…`, unchanged. Bench 48-pass; byte-copy
three-machine rehearsal satisfied/audited at the new claim.

## Round B (next): #3a, #3b, #5, #6

- **#3b moved here from round A.** A correct fix is *not* a one-liner: an
  unforgeable-token scheme defeats only the naive spoof (a bare
  `RETICULI_JAILED`), because an attacker who controls the environment can also
  create a matching token file — and threading a token through the kernel
  check's `_rejail()` is required or self-hosting breaks. The real fix is the
  same environment redesign as #3a (a scrubbed gate environment + an
  inheritance signal outside the record's/attacker's control), so #3b belongs
  with #3a. Both remain LANDS until then, by design.
- **#3a env/fs secret isolation:** scrub the gate environment, minimize the
  visible filesystem — bounded by what the self-host workshop gate legitimately
  needs (interpreter, package, lower layers).
- **#5 proof_recorded:** rename `proven` → `proof_recorded` (the manifest proof
  is unverifiable residue; the word should say so).
- **#6 solid = authorized(trusted) AND proof_recorded:** `phase()`/`minted()`
  must require the authorization to verify against a trust anchor, and solid
  must require both a recorded proof and a trusted authorization — per the
  decisions above.

## Round B carved (2026-09-04): all six → WALL

The architectural pass, per the decisions above. The six-attack battery now
flips **6/6 to WALL** with controls intact.

- **#3a env secret-isolation.** A gate runs with a **scrubbed environment** —
  a small host allowlist (PATH, locale) + a room-local HOME/TMPDIR, never your
  inherited secrets. A gate that read `$FAKE_INHERITED_SECRET` and wrote it to
  its room now reads nothing. Producers are not scrubbed (a producer is your
  command). *Residual, documented:* the sandbox is write-isolated, not fully
  read-isolated — a gate can still read host files it has permission to; the
  network is denied so a read cannot leave except through the room. Full
  read-minimization is deferred (a larger profile change).
- **#3b unspoofable inheritance.** The inherited-jail signal is now an
  **unforgeable per-run token** — `_jailed` writes it to a file and names it in
  the (scrubbed) child env; `jail()` inherits only when the env token matches
  the file. A bare `RETICULI_JAILED` names no file and is ignored, and a record's
  gate can't inject one (the gate env is scrubbed). `kernel_check._rejail` mints
  the token the same way, so self-hosting under the jail still nests correctly.
- **#5 proof_recorded.** `proven` is renamed **`proof_recorded`** everywhere
  (result, mint statement, mint_check row, CLI) — the manifest proof is
  unverifiable residue, and the name now says "a proof was recorded," not "this
  is proven."
- **#6 solid = authorized(trusted) AND proven.** `kernel.minted()`/`phase()` now
  require a signature that verifies against a **trust anchor** (`RETICULI_SIGNERS`
  or `~/.config/reticuli/allowed_signers`; `ssh-keygen -Y verify`, not
  `check-novalidate`) over a packet that binds by digest, on undrifted bytes,
  **and** whose packet records a proof. An unknown key, a missing anchor, or a
  record with no recorded proof is liquid *to you*. Solid is verifier-relative
  by construction — solid *to you*, against *your* signers.

**Bug found and fixed in passing:** `ssh-keygen -Y sign` prompts to overwrite an
existing `.sig` and, with no tty, leaves the **stale** signature in place — so a
re-attest or re-mint silently kept the old signature over new bytes (it only
"passed" when the new statement landed in the same clock-second as the old, an
identical-bytes fluke). `attest` now removes the stale signature before signing.
Surfaced by round B's re-mint path; the exchange gate's ceremony clause
exercises re-mint as its regression.

Localization: kernel-core `f9b01054…` → `e03676b7…` and exchange
`844d6f8d…`→`5e6aa4d0…`→`39546fe6…` (both claims changed); authoring through
vessel and the whole root `cc1a10e7…` held. Bench 48-pass, ruff clean,
byte-copy three-machine rehearsal satisfied/audited at the new claims, stub
refused at the genesis. The guide states the scrubbed environment, the
verifier-relative solid, and the one remaining jail limit (host-file reads).

## #3b walked back (2026-09-04): the token broke self-hosting; bare-env restored

The fourth live rehydration ([rehydration-4-census.md](rehydration-4-census.md))
died at the genesis: round B's #3b token used a **second env-var name**
(`_JAIL_REF`) that is free water, and a regenerated kernel named it
`RETICULI_JAIL_REF` while the committed bootstrapping kernel sets
`RETICULI_JAIL_TOKEN` — so the in-room kernel didn't recognize the outer jail and
re-applied one (`sandbox_apply: Operation not permitted`). The token narrowed the
kernel basin along a non-separating dimension (a name), violating the divergence
rule, and made the self-hosted jail handshake fail under independent
regeneration.

Per the user's decision, **#3b reverted to bare-env inheritance**: `jail()`
inherits on the presence of the single, well-known `RETICULI_JAILED`; the token
file and the second name are gone; `kernel_check._rejail` sets the bare signal,
so the check no longer *teaches* a producer to build a token. **#3a's env-scrub
is kept** — it is behavior-separating and bootstrap-robust, and it already blocks
the real threat (a record's gate injecting the signal, now scrubbed). The
residual is the outer-environment footgun (a wrapper exporting `RETICULI_JAILED`),
documented in the guide, not a record-borne attack. Net: **#3b is a documented
limit again, not a wall — the trade the user chose, buying back self-hosting.**

Localization: kernel-core `e03676b7…` → `2ec592de…`; exchange (`39546fe6…`) and
all rungs above, plus the whole root `cc1a10e7…`, unchanged.

## Status

Rounds one and two carved (2026-09-04), with #3b subsequently reverted after a
live rehydration proved its token narrowed the basin. Every *concrete* attack
the reviews named is a wall except #3b, which is now a documented footgun (the
env-scrub keeps its real teeth). What else remains is genuinely outside the
hashes (checker adequacy, epistemic independence, host-file read-isolation),
named in the guide's honesty contract. The live instrument's lesson: a hardening
clause is only real if it survives an independent regeneration — the basin, not
just the committed bytes, is what must hold.
