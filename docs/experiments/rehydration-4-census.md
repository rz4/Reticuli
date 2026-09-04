# Fourth live rehydration — the instrument catches a basin regression

The first live run against the **round-B hardened claims**. Result: it **failed
at the genesis** — and the failure is a real, important finding, not a repeat of
run 3's workshop seam. Live rehydration caught a basin-narrowing regression that
byte-copy controls and the committed self-test both miss by construction.
Prediction score: [rehydration-4-prediction.md](rehydration-4-prediction.md).

## What happened

The run died at the very first rung, `kernel-core`, with:

```
ret: redo failed at KERNEL_OK: sandbox-exec: sandbox_apply: Operation not permitted
```

The producer regenerated a fine kernel — **$1.55 / 57k tokens, 2 calls** (run 3
was \$1.56) — and then the gate failed to run at all. `sandbox_apply: Operation
not permitted` on darwin means a `sandbox-exec` was applied **inside** an
existing one: a jail nested, which the OS forbids.

## Root cause: round B's #3b token added an un-narrated cross-boundary handshake

The jail-inheritance signal introduced in round B uses **two** environment
variables:

- committed kernel: `_JAILED = "RETICULI_JAILED"`, `_JAIL_REF = "RETICULI_JAIL_TOKEN"`
- regenerated kernel (written blind from the check): `_JAILED = "RETICULI_JAILED"`,
  `_JAIL_REF = "RETICULI_JAIL_REF"`

The top-level `ret realize` runs the **committed** kernel. Its `_jailed` jails
the kernel gate and sets `RETICULI_JAIL_TOKEN=<path>` in the child environment.
Inside the gate, `kernel_check._rejail()` calls the **regenerated**
`kernel._inside_our_jail()`, which reads `os.environ.get("RETICULI_JAIL_REF")`
→ `None` (the committed side set `RETICULI_JAIL_TOKEN`, not `RETICULI_JAIL_REF`)
→ concludes "not jailed" → re-execs under `sandbox-exec` → nests → dies.

The token-path env-var **name is free water** — two honest kernels named it
differently, both sensibly. But the handshake requires the *bootstrapping*
kernel and the *regenerated* kernel to agree on that name, and nothing narrates
or enforces it.

## Why the controls didn't catch it (and the live run did)

- **Byte-copy three-machine** copies the committed kernel into the room, so both
  sides use `RETICULI_JAIL_TOKEN` — the names always agree, the handshake always
  works. Green.
- **The committed self-test** (`ret verify`, `selfrecord.py`, the round-B
  rehearsal) likewise runs the committed kernel on both sides. Green.
- **Only a live regeneration**, where the producer freely re-chooses the second
  env-var name, exposes the coupling. This is exactly what the instrument is for:
  a hidden claim the deterministic controls cannot see, surfaced by an
  independent redo.

## It violates the project's own divergence rule

The carving discipline: *promote a property to a claim only where it separates
every honest realization from a class of payloads.* Round B's #3b token failed
this test without our noticing — the `_JAIL_REF` **name** does not separate an
honest kernel from a malicious one; it only separates kernels that happened to
pick the same string. The token narrowed the basin along a dimension that costs
capability nothing to vary, excluding an honest realization. That is a
basin-width regression, and the honesty of the whole system is that we treat it
as one.

By contrast, #3a (the env scrub) is behavior-separating and bootstrap-robust: it
depends on no shared free-choice name, and it blocks the real threat (a record's
gate reading inherited secrets). The problem is specifically the #3b token.

## Prediction scorecard

- **"kernel-core and exchange land at their committed roots" — WRONG (kernel-core
  failed; exchange unreached).** But the *reason* is a regression I introduced,
  not the complexity I feared.
- **Cost instinct — RIGHT.** I predicted the narrated ceremony would regenerate
  cheaply despite its size; kernel-core came in at \$1.55 (I bet \$3.5), right at
  run 3's price. The producer built a fine kernel; it fell out of the basin on
  the handshake, not on cost or capability.
- **Predicted death rung — WRONG.** I put ~55% on the workshop jail-seam; the run
  died six rungs earlier and never reached workshop. I listed "kernel thrashes on
  the trusted-signer ceremony" as the kernel risk — but the ceremony wasn't the
  problem; the jail token was, and I did not list it as a risk at all.
- **Budget deaths: 0 — correct** (a gate failure, not a budget death).

**Takeaway:** the strongest result the live instrument has produced. It caught a
hidden, un-narrated claim that made the kernel basin too narrow to self-host
under live regeneration — invisible to every deterministic control — and it did
so at the genesis, for \$1.55. The fix decision (make the inheritance signal
bootstrap-robust, most simply by reverting #3b's token to the single narrated
`RETICULI_JAILED` signal and keeping #3a's scrub) is the next step.

## Status

Measured 2026-09-04. M3 left as produced. The committed repo still self-hosts
via byte-copy (both sides committed), so nothing is broken *in place* — the
regression is a basin narrowing that only live regeneration reveals.
