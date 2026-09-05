---
name: reticuli-pack
description: Use to turn a codebase — your own project or an external one — into a Reticuli claim record and regenerate its implementation from its tests/spec (rehydrate). For reproducing a project from its spec alone, or measuring how much of it is genuine claim versus free implementation (its basin width). This is the experiment machine.
---

# Packing and rehydrating a codebase

`pack` seals a project directory as a record by deciding what is **claim** (the
spec — seeds + gate, hashed into the root) and what is **free** (the
implementation — produce globs, excluded from the root). Rehydrating regrows the
free part from the claim alone; if a byte-different implementation lands the same
root, the identity was the spec, not the bytes.

> If `ret` is not on PATH, use `python3 -m reticuli`. Work on external code in a
> scratch directory — never copy a foreign project into the Reticuli repo.

## Pack

```
ret pack <name> \
  --produce "src/**/*.py" \        # the implementation — free water
  --seed    "tests/**/*" \         # the spec/tests — the claim, hashed
  --gate    "PYTHONPATH=src python3 -m pytest -q tests && printf ok > PASS" \
  --output  PASS \
  -C <project-dir>
```

- The gate must **name its `--output`** (the `&& printf ok > PASS`), be
  deterministic, and be offline — the jail denies the network.
- Confirm it is a real record: `ret verify .` (fresh) and `ret audit .` (earned —
  the gate reproduces jailed). If audit fails, the spec isn't hermetic yet.

## Rehydrate (regrow the implementation from the claim)

```
ret realize <record> --producer "<a model/command blind to the original impl>" --into M3
```

Add `--recursive` for a layered record (components). For a live model producer,
set `RETICULI_AGENT_BUDGET` (usd cap per session). Then judge it like any record
(see reticuli-verify): build M2 with `ret export`/`ret import`, then
`ret prove <record> M2 M3`.

`ret tree .` / `ret records .` show a record's anatomy and the registry.

## What you learn (the point)

- **Lands, byte-different** → the spec *is* the identity; diff M3 against the
  original to measure the free water (the basin width).
- **Won't land** → either the tests under-specify the behavior (basin too wide —
  a passing-but-wrong redo, the Goodhart case) or the behavior is tangled in the
  environment (the "checker is not the predicate" problem). Both are real
  findings about the codebase.
- Whatever the redo *cannot* vary and still pass is the resistant core — the part
  worth attesting.

Worked examples and cost predictions live under `docs/experiments/`. Depth:
`docs/guide.md`.
