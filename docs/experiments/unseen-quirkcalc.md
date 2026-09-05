# Unseen specimen — quirkcalc (cost prediction BEFORE the run)

The independence test tomli couldn't be. tomli is public and in the model's
training, so its rehydration is "reconstruct OR recall." This specimen is a
small library **authored fresh for this experiment** — `quirkcalc`, an integer
expression evaluator whose operator set, precedence, and associativity are
**invented and exist nowhere but its test file.** The producer (a separate
sonnet session) sees only the tests. It cannot recall behavior that did not
exist an hour ago, so **a landing is genuine reconstruction from the spec.**

## The specimen

`evaluate(expr)` over `+ - * / ~ ? %` and parens on non-negative integers, with
deliberately non-standard rules, all pinned by 59 cases in `test_calc.py`:

- `~` = digit-join (`12 ~ 34 → 1234`), binds **tightest**.
- `?` = max, `%` = floor-average `(a+b)//2`, both **below** `* /` in precedence.
- `-` and `/` are **right-associative** (`10 - 3 - 2 → 9`, not 5;
  `100 / 5 / 2 → 50`, not 10).
- `/` truncates toward zero (`(0-7)/2 → -3`); div-by-zero and digit-join of a
  negative right operand raise `CalcError`.

Packed clean: 1 produce (`calc.py`, ~130 lines, free), 1 seed (`test_calc.py`,
the claim), root **`190ab1b6`**, `audit` earned. Reference impl passes 59/59.
Landing ⇔ the regrown implementation passes all 59 jailed → seals at `190ab1b6`.

## The bet

- **Settings:** sonnet, one agentic producer, `RETICULI_AGENT_BUDGET=15`.
- **Lands? ~65%.** The *shape* (an expression evaluator) is familiar, so it's
  not impossible; the *semantics* are unrecallable, so it must read the tests.
  Agentic iteration against 59 precise asserts is the engine — blind, it would
  assume a standard calculator and fail; iterating, it should converge. The two
  places it will fight its own priors hardest: **right-associative `-` and `/`**
  (deeply counterintuitive) and the **invented precedence order** (`? %` below
  `* /`). If the tests pin those unambiguously (they do), it can get there.
- **Cost: ~\$4** (range \$2–9), **~60k tokens, 5–15 calls**, 5–20 min.
- **Biggest way it fails:** it can't shake the standard-calculator prior under
  budget (recall actively misleading — the interesting failure), or my 59 cases
  leave a rule under-determined (a cage gap — a finding about my spec, not the
  model).

## After the run: the Goodhart check

If it lands, I'll **differential-fuzz** the regrown `calc.py` against my
reference on random expressions. Passing 59 tests is not the same as *being*
quirkcalc — if the fuzz finds a disagreement, the cage had a gap and the model
Goodharted it. If they agree across thousands of random inputs, the
reconstruction is genuine and the cage was tight. That is the real payoff: not
just "it passed," but "an independent model rebuilt invented behavior it could
not have seen, and it's actually correct."

Actuals and score below after the run.

## Actuals (2026-09-05)

**Landed — invented behavior reconstructed from its spec alone, in one call.**
The producer regrew `calc.py` (123 lines vs my 130, byte-different) and sealed at
the committed root `190ab1b6`, in **1 call, \$0.50, 163s**. It did not just fit
the cases — its docstring correctly *names every invented rule*: "`-` is
right-associative," "`/` truncates toward zero, right-associative," "`~` decimal
concatenation," "`?`/`%` max and floored-average below `*`/`/`." A model that had
never seen these operators reconstructed the whole spec from 59 examples.

## The Goodhart check — and what it found

Differential fuzz vs my reference on **20,000 random expressions: 19,978 agree
(99.89%)**, zero crashes. The 22 disagreements are all one shape and one region:
**digit-join `~` on a negative left operand** (`(0-5) ~ 3` → my reference `-53`,
the regrown raises `CalcError`). My 59 tests **never pinned that case** — my
reference's `-53` is a string-concat accident I never wrote a test for; the
regrown made a different, equally-spec-consistent choice (raise). Both satisfy
all 59 tests. They diverge *only where the spec is silent.*

## Score — the independence claim, earned

- **Lands: predicted ~65%, LANDED** — and far cheaper (\$0.50 vs \$4, 1 call vs
  5–15). I over-taxed iteration again; reading the tests was nearly enough.
- **Genuine reconstruction, not recall.** The behavior did not exist before this
  run; the producer saw only the tests; it rebuilt the spec correctly, 99.89%
  identical to the reference across 20k random inputs and correctly documented.
  This is the independence tomli could not establish (tomli is public/in-training)
  — here it is earned on code that provably was not in the model's training.
- **The basin's width, measured to the input.** The 0.11% is not a failure and
  not Goodhart — it is precisely the region my spec left unspecified. The fuzz
  located the exact boundary between "the spec pins it" and "the spec is silent,
  and honest implementations may differ." That boundary *is* the free water.
- **Lesson (mine, again):** the cage is only as tight as the spec. I under-tested
  negative-left `~`; the instrument found the gap. Add one test there and the
  cage closes — the fracture-map loop (fuzz → new case → tighter basin) in
  miniature.

**Takeaway:** an independent model reconstructed an invented library from its
tests alone, correct wherever the tests spoke, for fifty cents — and the
differential fuzz measured, to the exact input class, where the spec stopped
speaking. That is the reach, demonstrated with independence and with honesty
about its edge.
