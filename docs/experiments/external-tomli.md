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

## Actuals (2026-09-05)

**It landed — a from-scratch parser passes tomli's full suite, proven.** The
live model regrew the parser and sealed; the regrown implementation is
byte-different in 3 of 4 files (`_parser.py` 743 lines vs the original 799,
`_re.py` 107 vs 119, `__init__.py` 10 vs 8); only `_types.py` (bare type
aliases) came back identical. Cost: **\$5.72, 85k tokens, 4 calls, ~14 min.**

**A pack-hygiene bug of mine, and its correction (a finding in itself).** My
first pack accidentally sealed 5 `.pyc` bytecode files as seeds — I ran the
baseline gate before packing and `--seed "tests/**/*"` swept in
`tests/__pycache__/*.pyc`. Bytecode embeds compile metadata, so it moves on
recompile: the original pack (`a09be2e6`) and the rehydration (`6ba40e29`)
differed **only** in those 5 files; every real seed (test code + 744 compliance
pairs) was byte-identical, and the producer never touched a test. I re-packed
cleanly (`--seed "tests/**/*.py" "*.toml" "*.json"`, 977 seeds, root
`1710ef24`), byte-copied the already-regrown parser into a clean realize, and
`ret prove` is **satisfied / integrity / reuse / equivalence / audited** — the
regrown parser lands the clean root. Lesson, in the project's own terms: I put
non-deterministic non-claim bytes into the claim; a claim must seal the spec,
not build artifacts.

## Score

- **Lands: predicted ~55%, LANDED** — and more easily than feared: **4 calls,
  \$5.72** vs a \$12 / 15–30-call bet. I over-taxed iteration.
- **No Goodhart.** The 744-case compliance suite is a *tight* cage — the regrown
  parser passes all of it, no evidence of slipping between the bars. This is the
  good outcome: tomli's tests genuinely pin tomli.
- **The fracture:** the parser is free water (a leaner 743-line reimplementation
  in the basin), the type aliases are resistant core, and the 977 tests are the
  identity. A stranger's library reproduces from its spec under an independent
  model.

## The honest caveat (epistemic independence)

tomli is a widely-used, public library almost certainly in the model's training
data — so this is "a model that knows TOML regrows a passing parser from the
tests," not a blind reconstruction. The claim it validates is real (a
byte-different implementation satisfies the spec and shares the root), but the
*independence* is weaker than the three-machine test can see — exactly the limit
the guide's honesty contract names. The sharper next specimen is an obscure or
private codebase the model has not seen.
