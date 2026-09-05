# Third live rehydration — the jail-seam reopened at the workshop

The first live run against the **hardened claims** (the attack-review carve).
Result: **the two hardened rungs landed live; the run then failed at workshop
— not on the carve, but on the jail-seam trap, reproduced in the wild on free
test water.** Prediction score: [rehydration-3-prediction.md](rehydration-3-prediction.md).

## What landed (5/8 sealed at the exact committed roots)

| rung | sealed at committed root? | cost |
|---|---|---|
| kernel-core | **yes** — the whole `minted()` ceremony | \$1.56 / 54k |
| exchange | **yes** — drift, packet binding, elision, proven | \$3.90 / 120k |
| authoring | yes | \$1.48 / 46k |
| agents | yes | \$0.52 / 11k |
| surface | yes | \$1.58 / 44k |
| workshop | **produced, then FAILED the jailed gate** | \$6.74 / 110k |
| vessel | unreached (workshop blocked the chain) | — |
| reticuli | unreached | — |

**Total: \$15.78, 388k tokens** — the run-2 whole-repo price, spent on 5.x
rungs instead of 8, because workshop iterated to the budget's edge against a
gate it could not see it was failing.

**The headline: both hardened rungs landed live.** A fresh sonnet, given only
the carved kernel and exchange checks, reinvented the mint ceremony (intact
signature over a root-naming statement, packet-digest binding, realization
drift demotion, all-three-roots equivalence, proven≠solid) and the exchange
walls — and sealed both at the exact committed roots. The carve cost zero
basin width: the holes closed without pushing the basin out of reach.

## Why workshop failed: the jail-seam, precisely located

The workshop clause requires the regrown pytest suite to pass. It does —
**unjailed**. The authoritative gate runs it **jailed** (seatbelt), and there
two tests fail:

```
FAILED tests/test_quarantine.py::test_jail_backend_is_a_real_platform_choice_or_none
FAILED tests/test_quarantine.py::test_jailed_command_cannot_write_outside_its_cwd
  assert backend == "seatbelt"
  E  assert 'inherited' == 'seatbelt'
```

The producer *understood jail-nesting* — it wrote a test that sets
`RETICULI_JAILED` and correctly expects `"inherited"`. But it guarded its
other quarantine assertions on **platform**:

```python
if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
    pytest.skip(...)
assert backend == "seatbelt"        # true only when NOT already jailed
```

Our committed suite guards on the **ambient jail state** instead:

```python
BACKEND = kernel.jail("true", tmp)[1]              # what the env actually gives
@pytest.mark.skipif(BACKEND in ("none", "inherited"), ...)
```

So under the jailed gate our tests skip and the producer's assert fails — the
whole difference is *platform check vs runtime-environment check*, and it is
**free water** (the exact test bytes are unpinned; our realization proves the
claim is satisfiable jailed: `3 passed, 2 skipped`).

The root cause is the documented [jail-seam finding](README.md): **the
producer's test environment ≠ the verdict environment.** The agentic
producer's Bash tool runs unjailed, so `RETICULI_JAILED` is never set during
its iterate-until-pass loop; the ambient-jail case it needed to guard never
arose in front of it. Last time the seam was in the *kernel check* and the fix
was `_rejail()` (the check re-execs into the host jail so producer-env =
verdict-env). The workshop's pytest suite has **no equivalent re-jail**, so
the seam reopened one rung out — this time on the free test suite, not the
claim.

## The carve is orthogonal to the failure

Workshop's claim was **byte-unchanged** by the attack-review carve. This
failure would have happened against the pre-carve claims too; it is not a cost
or reachability regression introduced by the hardening. The hardening landed
(kernel + exchange); the trip was on old, unchanged ground.

## The decision this surfaces (a carve candidate, the user's call)

The jail-seam at workshop is realization debt the net detected. Two ways to
pay it into the claim, if we choose to:

1. **Make workshop's producer iterate jailed** — give the workshop check a
   `_rejail()` like the kernel's, so the producer's `python3 -m pytest` during
   iteration runs in the same jail the verdict uses. Closes the seam at its
   source (producer-env = verdict-env) for the whole suite, not just quarantine
   tests. Heavier: the producer's tool sandbox and our jail would nest.
2. **State the contract in the check** — the workshop clause already owns
   "the suite must pass"; it could additionally assert that the suite is
   *ambient-jail-tolerant* (no test hard-asserts a backend that inheritance
   would change), the way the kernel check states its execution contract in
   prose the producer reads. Lighter; teaches rather than sandboxes.

Neither is a claim *hole* (no payload rides through — an over-strict test only
ever fails honest producers, never admits a bad one), so this is hardening for
*reproducibility*, not security. It is exactly the "realization debt →
convergence" loop the README describes, and it is the user's decision whether
to carve it now or bank it as a known limit.

## Carve executed (2026-09-04): the workshop re-jails

Option 1 from the decision above, chosen after the round-B revert made a
bare-env re-jail bootstrap-safe. `checks/workshop_check.py` now carries a
`_rejail()` mirroring the kernel check's: when the host has a jail and we are
not already inside one, it re-execs the whole check under a real sandbox with
the single well-known `RETICULI_JAILED` set. The producer's own gate-run
(`python3 checks/workshop_check.py`, previously unjailed) is thereby made equal
to the verdict's environment — the suite runs jailed during iteration, so a
jail-fragile suite fails *in front of the producer*, not only at the final gate.

Discipline held:

- **The specimen is rejected for exactly its reason.** Run 3's regrown
  `test_quarantine.py` (hard-asserts `backend == "seatbelt"`) passes UNJAILED
  (5/5 — why the producer shipped it) and FAILS via the jailed workshop check
  (`exit 1`, the suite returns nonzero because the ambient backend is
  "inherited"). Our committed jail-tolerant suite passes both ways.
- **Localization**: only the workshop root moved (`5c229b2e…` → `27e30a1b…`);
  every other rung and the whole root `cc1a10e7…` unchanged.
- **Rehearsal**: byte-copy three-machine `satisfied`/`audited` at the new claim;
  bench 48-pass; ruff clean.

The seam that killed run 3 is now a wall — the workshop basin requires a
jail-tolerant suite, enforced by running the verdict's environment during
iteration. Note it is still one ambient dependency (pytest) and a
capability-bounded claim, exactly as the header says.

## Status

Measured 2026-09-04, seam carved the same day. Both hardened rungs landed live;
the workshop jail-seam that blocked completion is closed and specimen-validated.
