---
name: reticuli-record
description: Use when finishing agentic work in a repo that uses Reticuli (the `ret` CLI) and you want that work captured as a sealed, independently-verifiable record — wiring the session trace, authoring a gate, and condensing to a claim. This covers authoring a liquid record; use reticuli-verify to prove one reproduces, reticuli-mint for the human authorization step (never signed by an agent).
---

# Authoring a Reticuli record

Reticuli seals a unit of work so a stranger can reproduce and trust it. A
record's identity is `root = hash(recipe + dry seeds + pinned verdicts)` — it
**excludes the free implementation**, so any implementation that passes the same
checks shares the root. Phases of matter: **vapor** (a live session, nothing
sealed) → **liquid** (condensed and sealed, verifiable) → **solid** (a human has
authorized it — not your job; see reticuli-mint). This skill produces the liquid
record.

> If `ret` is not on PATH, use `python3 -m reticuli` instead — identical.

## The loop

1. **`ret init`** — once per repo. Gitignores the volatile history and marks
   sealed bytes binary so git never mangles them.
2. **`ret hooks`** — wire the harness (Claude Code and compatible) so every
   prompt, file read/write, and command lands in the session trace. `ret status`
   shows it filling in. (The receiving end, `ret hook`, is silent and a no-op
   outside a session, so it's safe in a committed `.claude/settings.json`.)
3. **Do the work, then author a GATE.** A gate is a command that decides
   pass/fail and **names its own output file**:
   ```
   ret run "python3 check.py && printf ok > VERIFIED"
   ```
   The `&& printf ok > VERIFIED` is not optional: condense only sees a gate whose
   command names its output. A gate that never names a file → a hollow record
   (zero gates, audit vacuously true). This is the most common mistake.
4. **`ret condense --accept VERIFIED --into rec`** — draft the record and certify
   it cold (the trace has no authority; the bytes do). `--accept` may repeat for
   several verdict files; `--name` overrides the record name.
5. **`ret verify rec`** — recompute the root from the bytes on disk; must report
   `fresh`. A git-cloned record verifies from its committed identity alone.

## Guardrails

- **The gate must be deterministic and hermetic** (offline, no clock/RNG/network
  dependence). A nondeterministic gate fails `audit` later — and an unearned
  verdict is not a claim.
- **Never hand-edit `.reticuli/manifest.json`** or a verdict file after sealing;
  that is exactly what `audit` is built to catch.
- Re-condensing the same session is byte-identical (a lockfile) — no diff.

Depth and concepts: `docs/guide.md`.
