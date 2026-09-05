# External specimen — packing and rehydrating tomli (cost prediction BEFORE the run)

The first **non-self** rehydration. Every run so far was Reticuli reproducing
Reticuli — self-referential, the honest limit in this README's "Known limits."
This packs a real outside project ([tomli](https://github.com/hukkin/tomli), the
pure-Python TOML parser) and asks a live model to regrow it from its tests alone.

## The pack

`ret pack tomli --produce "src/tomli/*.py" --seed "tests/**/*" --gate
"PYTHONPATH=src python3 -m pytest -q tests && printf ok > PASS" --output PASS`

- **Claim (984 seeds):** the whole test suite — 17 unit tests + 744 valid/invalid
  TOML↔JSON compliance pairs. This *is* the spec.
- **Free (4 produce files):** the parser — `__init__.py`, `_parser.py` (799 lines),
  `_re.py` (119), `_types.py` — ~936 lines total.
- **Root: `a09be2e6…`** = hash(recipe · the 984 test seeds · the PASS verdict).
  The parser bytes are excluded; the tests are the identity.
- Validated as a real record: `verify` fresh, `audit` earned (the suite
  reproduces jailed under seatbelt).

Because the root excludes the free parser, **landing ⇔ the regrown parser passes
the entire suite jailed** (then it seals at the same `a09be2e6`). A failing
parser never seals — clean binary outcome.

## The bet

- **Settings:** sonnet, one agentic producer session (no components, one flat
  record), `RETICULI_AGENT_BUDGET=20`.
- **Does it land? ~55%.** TOML is intricate (multiline-string trimming, dotted
  keys, arrays of tables, datetime offsets, integer rules) and 744 compliance
  cases are strict — but the producer iterates (runs pytest, sees failures,
  fixes), the 744 cases give rich feedback, and sonnet knows TOML well (tomli is
  surely in its training). The knowledge cuts both ways: it may reconstruct a
  correct parser fast, or Goodhart the tests with a subtly-wrong one the 744
  cases happen not to catch (unlikely — the suite is comprehensive).
- **Cost: ~\$12** (range \$6–20), **~200k tokens, 15–30 calls** (parser-scale
  iteration, workshop-like). **Wall clock: 20–60 min.**
- **The fracture prediction:** if it lands, the regrown parser is byte-different
  from real tomli — a different valid point in tomli's basin — and I'll measure
  how different (line count, structure). That difference is tomli's free water;
  what every passing parser must share is its thermodynamically resistant core.
- **Biggest way I'm wrong:** a cluster of edge-case compliance files it can't
  satisfy under budget → no landing (the basin is reachable in principle but not
  by this producer under \$20), or it burns the budget mid-parser (a \$20 death).

## The point

This is the external-validity test the whole program was building toward: does
the basin-compiler thesis — *identity is the spec, the implementation is free* —
hold for code Reticuli was **not** co-designed with? A landing says a stranger's
library reproduces from its tests under an independent model. A miss says either
its tests under-specify it (basin too wide) or its behavior is harder to hit than
its own suite implies — both real findings about real software.

Actuals and the score go below after the run.
