# The guide

The long form. The [README](../README.md) is the 60-second contact layer — a
free output of the repo's own self-record, gated by
[`docs_check.py`](../docs_check.py); this guide is where the depth lives.

## The one idea: the root *is* the claim

A record's identity is

```
root = hash( recipe  +  dry seeds  +  pinned verdicts )
```

and it **excludes the free outputs** — the implementation. So two valid
realizations of one claim share a root, and the three-machine test collapses to
**root equality**:

```
M1  a claim              root = hash(recipe · seeds · pinned)
M2  a reuse              carries M1's outputs byte-for-byte, produces nothing
M3  an independent redo  re-produced from the recipe by any producer
valid  ⇔  roots equal  ∧  every machine's gates re-run clean (audit)
```

The **basin of attraction** is exactly the preimage of the root: every
implementation that passes the same checks hashes to the same claim. `free`
outputs are the water; `exact`/`validated` verdicts are the shape it takes.

A full session, and what `ret prove` prints:

```bash
ret init                                   # git-native: ignores history, marks bytes binary
ret hooks                                  # wire Claude Code: prompts/writes/reads/runs -> the trace
# ... write a checker.py and some code (the agent's work is traced) ...
ret run "python checker.py"                # author a gate (produces VERIFIED)
ret condense --accept VERIFIED --into rec  # draft a record and certify it cold
ret realize rec --producer "$YOUR_MODEL" --into M3   # an independent redo
ret prove rec M2 M3                        # the invariant
```

```toml
[prove]
satisfied = true
integrity = true
reuse = true
equivalence = true
cost = true

[cost]
unit = "calls"
c1 = 1                         # what the original paid
c3 = 1                         # what the redo paid
ratio = 1.0
tolerance = 2.0

   machine  root
0  M1       c124ba320206…
1  M2       c124ba320206…      # three implementations, one root
2  M3       c124ba320206…
```

See [`docs/experiments/cube`](experiments/cube/): three genuinely different
rotating-cube implementations (≈0.1 code similarity) all certify against one
fixed checker.

## The agent handshake

`ret hooks` wires Claude Code (and compatible harnesses) to the session:
every prompt, file write/read, and command the agent runs lands in the trace
as it happens — no ceremony, no wrapper. `ret hook` is the receiving end,
called by the harness with a JSON payload on stdin; it is silent, never blocks
the agent, and is a no-op outside a session, so the wiring can live in a
committed `.claude/settings.json` without side effects elsewhere. Once wired,
`ret status` shows the session filling in and `ret condense` is one command
away — the loop the trace was designed for, closed.

## The lifecycle

A record moves through phases of matter:

- **vapor** — a live session; a trace, nothing sealed.
- **liquid** — condensed and sealed; a claim you can verify and share.
- **solid** — freeze-dried: it survived the three-machine test; portable.

Files are **dry** (given seeds, carried unchanged) or **wet** (produced). A dry
seed is the archetype of a component: *`solid` is a record's view of itself;
`dry` is a dependent's view of that same record.*

## Git-native

A record's identity is byte-deterministic, so it commits like a lockfile:

- `ret init` gitignores the volatile history (`vapor.jsonl`, per-record
  ledgers) and writes a `.gitattributes` so git never mangles sealed bytes
  across platforms.
- Re-condensing the same session produces **no diff**; two people condensing
  one session get identical records.
- `git clone` a repo and `ret verify` its records from the committed bytes
  alone.

## The cost ledger

Cost is **residue of the event, never part of the claim** — it stays out of the
root. `ret realize` accounts every step to a local ledger
(`.reticuli/ledger.jsonl`): one line per oracle call (calls, wall seconds, and
tokens/usd when the producer reports them back through `$RETICULI_USAGE`), one
per gate, one per component-supplied reuse. `ret condense` accounts the traced
session: one call per prompt, the trace's wall-clock span.

`ret prove` completes the three-machine test with the comparable-cost check:
C3/C1 in the strongest unit both machines measured (usd > tokens > calls >
seconds), within the claim's declared tolerance (`[record] tolerance`, default
2.0 — i.e. 0.5 ≤ C3/C1 ≤ 2.0). An unmeasured machine is reported, not failed:
cost gates `satisfied` only when both ledgers exist. Ledgers are volatile
history — gitignored by `ret init`, excluded from `ret export`; identity
travels, events don't.

## Soundness: earned, not carried

Root equality is *identity*, not evidence — the root deliberately excludes the
free outputs, so a directory can carry M1's recipe, seeds, and verdict bytes
while its free bytes no longer satisfy the gate at all. `ret verify` will still
say fresh (it proves the identity holds); it will not catch this. That is what
`ret audit` is for: it rebuilds a scratch room from the record's recipe, seeds,
and produce outputs — **no verdicts carried in** — re-runs every gate jailed,
and requires each pinned output to reproduce the record's bytes exactly.
`ret prove` audits all three machines, so a fabricated M3 that shares the root
neither proves nor mints, and `ret attest` refuses to notarize one. (This
closes the carried-verdict forgery demonstrated by the project's first external
review.) What audit cannot establish is *independence* — that M3's bytes were
genuinely produced rather than copied from M1 is a provenance property, not a
content property; that is attestation's and, eventually, witnessed execution's
job.

## Quarantine

A record's gates are not your shell. Realizing (or condensing, or packing) runs
every gate in the platform's jail — `sandbox-exec` on macOS, `bwrap` on Linux
where present — with writes confined to the record's room and the network
denied. **Producers are never jailed**: you chose that command; a pulled
record's gates you did not. The ledger records what happened to each gate
(`"quarantine": "seatbelt" | "bubblewrap" | "inherited" | "none" | "off"`) —
jails don't nest, so a gate spawned inside a jail inherits the outer one.
`RETICULI_QUARANTINE=require` refuses to run gates without a jail; `off` opts
out; the default `auto` uses one when the platform provides it and says so
either way. The jail protects *you* from a record; speaking to *others* is
attestation's job, below.

## Attestation

The converse of quarantine: a keyholder's signed statement that *this*
realization verified fresh on their machine — the root, every output's hash,
the gates' quarantine record, the cost. `ret verify` alone never re-runs gates,
so trust otherwise means redoing; an attestation lets a verifier trust a
realization they didn't redo, anchored to a key instead.

```bash
ret attest M3 --key ~/.ssh/id_ed25519 --as you@lab.gov   # sign (ssh-keygen -Y)
ret attest M3 --check --signers allowed_signers          # verify identities
```

The statement is an [in-toto v1 Statement](https://in-toto.io) (foreign
supply-chain tooling can read it), signed with the SSH key you already have —
no key ceremony, same mechanism as git's SSH commit signing. Attestations are
residue *about* the claim: they live in `.reticuli/attest/`, commit and travel
with the record (`ret export` carries them), and never enter the root. `attest`
refuses to sign a broken record; `--check` refuses a tampered statement, and
without a signers file reports signatures as `intact` (the bytes are covered;
the signer is your problem). What remains open beyond this is witnessed
execution — proving *where* a gate ran, not just who vouches for it.

## Output

Every command prints exactly one of three shapes — a **TOML** fact sheet (one
entity), a **table** (rows), or a **tree** (a DAG) — with `--json` underneath.

## Self-hosting

Reticuli is a **basin-compiler that compiles itself** — in eight rungs, ordered
by interface volatility: the deeper the layer, the more stable its contract;
the outer layers face other parties — agents, humans, first contact — and
churn. `ret pack` declares a project as a record: its code the *free* outputs,
its check the *seed*, gated by running the check. Eight records make up the repo,
each carrying everything below it and layering its own stratum on top, sealed
by [`scripts/selfrecord.py`](../scripts/selfrecord.py):

| rung | own stratum (free) | seed (the check) | claims |
|---|---|---|---|
| **kernel-core** | `reticuli/{__init__,kernel}.py` | [`kernel_check.py`](../kernel_check.py) | the invariant → `KERNEL_OK` |
| **exchange** | `+ {registry,transfer,attest}.py` | [`exchange_check.py`](../exchange_check.py) | records meet records, and other parties → `EXCHANGE_OK` |
| **authoring** | `+ {render,condense,feedback,pack}.py` | [`authoring_check.py`](../authoring_check.py) | sessions become records → `AUTHORING_OK` |
| **agents** | `+ hooks.py` | [`agents_check.py`](../agents_check.py) | the agent handshake → `AGENTS_OK` |
| **surface** | `+ {cli,__main__}.py` | [`surface_check.py`](../surface_check.py) | the human handshake → `SURFACE_OK` |
| **workshop** | `+ scripts/*.py, tests/*.py` | [`workshop_check.py`](../workshop_check.py) | the bench: suite passes AND has teeth (a killed `seal` must fail it) → `WORKSHOP_OK` |
| **vessel** | `+ pyproject, CI, git skin` | [`vessel_check.py`](../vessel_check.py) | the skin it ships in; LICENSE and logo pinned as seeds → `VESSEL_OK` |
| **reticuli** (documentation) | `+ README.md, docs/guide.md` | [`docs_check.py`](../docs_check.py) | the hand-off: a minute for contact, depth for engineers and agents, every verb and env var documented, no lies → `VERIFIED` |

Each rung obtains the layers beneath it from its predecessor as `from` produce
steps — free code it *layers on*, not bytes it pins. Even the README is free
water: its word budget and honesty are the claim. So `ret verify .` holds,
`ret deps .` draws the chain, and:

```bash
ret realize . --recursive --producer <model> --into M3
```

rehydrates **leaf-first**: it regrows the kernel from `kernel_check.py`,
threads it up through exchange, authoring, agents, and the surface, writes a
fresh README against `docs_check.py`, and — because all of it is free and the
root is the claim — **lands on the same roots, rung by rung.** Each rung pays
its own ledger, so a recursive redo yields a **per-layer cost envelope**: what
the invariant costs to regrow vs. what the volatile handshakes cost. Today's
roots, inner to outer: `81622000…`, `26a1f7a0…`, `f1168e37…`, `b3d17a3e…`,
`9213b976…`, workshop `efc35bfc…`, vessel `59845d94…`, whole `4a8625e0…`.
`ret tree .` draws the whole anatomy —
each rung's seed (the claim), its free stratum, what its component supplies,
and its pinned verdict, contact to leaf.

Three properties, all tested:

- **Editing the implementation keeps the root** — the code (and the README) is
  free water.
- **Editing a check changes that layer's root** — the check *is* the claim.
- **Each layer is its own basin** — any conformant kernel gives one
  `kernel-core` root; any conformant toolchain over it gives one whole root.

The manifest is pure `{name, root}` (+ component links), no free-output hashes,
so a self-hosted record stays byte-stable under code edits and commits clean.
Re-run `scripts/selfrecord.py` when files change (it's a lockfile).

### Rehydrated by a live model

`<model>` above can be a real one.
[`scripts/producer_claude.py`](../scripts/producer_claude.py) drives the redo
with the `claude` CLI — one text call per file, no tools, no reference in the
room: the model reconstructs each file *blind* from the check and has to land
in the basin.

```bash
# run from the repo root; producers run with the clean room as cwd, so the
# script path must be absolute ($PWD resolves before realize hands it off)
ret realize . --recursive \
  --producer "python3 $PWD/scripts/producer_claude.py" --into M3
```

There are two producer *modes*, measuring two different questions.
[`producer_claude.py`](../scripts/producer_claude.py) is **oneshot** — one blind
call per file, no tools, no ability to run the gate: "can the model land in the
basin from the contract *alone*." [`producer_claude_agentic.py`](../scripts/producer_claude_agentic.py)
is **agentic** — one autonomous session in the room, with tools, that may run the
gate, see it fail, and fix until it passes or a dollar budget
(`RETICULI_AGENT_BUDGET`) is spent: "can an agent land it given the ability to
test, and at what cost." Oneshot is cheaper and honest about raw capability;
agentic lands more and turns the reflection profile into a *repair-cost* map. The
room holds only the check and the already-free lower layers — no reference — so
the agent iterating against the gate is honest "make the tests pass," and
realize's jailed gate stays the authoritative verdict.

[`scripts/producer_openai.py`](../scripts/producer_openai.py) is the same
oneshot contract for OpenAI models. [`scripts/sweep.py`](../scripts/sweep.py) is
the reproducible runner for the whole grid — controls plus {haiku, sonnet, opus}
× {oneshot, agentic} — over [`scripts/probe.py`](../scripts/probe.py), which
isolates each layer and lands a cell only when the redo hits the committed root
*and* passes `audit`. Every row is stamped with the `claim_root` it was measured
against (never mix data across a re-mint), one sweep runs at a time (a lock), and
each landed specimen is archived as a re-auditable record. The protocol and its
honesty rules live in [`docs/experiments/`](experiments/).

It works — and the redo's ledger accounts what the model actually cost: the
producer reports real token/usd usage back through `$RETICULI_USAGE`, one line
per blind call. In one such run (sonnet-5), given only the checks, a live model
regrew the whole repo — **every one of the 10 modules byte-different from the
committed code** (991 lines vs 1130; `kernel.py` 352 vs 206, `cli.py` 160 vs
285) — and the chain landed on the *same roots* (`a1fc505a`, `30968ae8`, the
claim as it then stood — the checks have since grown the cost, quarantine, and
attestation clauses, re-minting the roots above). A different kernel and a
different toolchain, one claim. Run it again and the model writes different
code again; the roots don't move. That is the three-machine test with an
independent producer: the basin is real, not a copy.

### Composition, in general

`kernel-core → whole` is one instance of a general facility: a record can
depend on other records. A dry seed that content-matches a component's output
links them as *pinned data*; a `from` produce step links a component's output
as *free code*. `ret realize --recursive` rehydrates the whole DAG bottom-up
either way — the claim reproduces from the leaves, not just one layer.

## The verbs

| phase | verb | |
|---|---|---|
| vapor | `init` · `hooks` · `hook` · `run` · `status` · `tree` | set up · wire the agent · receive one agent event (stdin) · record a command · where am I · two lenses: a session's dry/wet, a record's anatomy |
| liquid | `condense` · `verify` · `audit` · `show` · `pack` · `records` · `deps` · `pull` · `export` · `import` · `attest` | seal · does the identity hold · do the verdicts reproduce · print the recipe · self-record · the drawer · the DAG · depend on a record · deterministic tar out · unpack and verify back · sign it for others |
| solid | `realize` · `realize --recursive` · `prove` | an independent redo · redo the whole component DAG · the three-machine test |

Records compose: a dry seed that matches a registry record's output links the
two (content-addressed). `ret pull` brings a component in as seeds; `ret deps`
draws the DAG; `ret realize --recursive` rehydrates it bottom-up. `solid` is a
record's view of itself; `dry` is a dependent's view of the same record.

## The environment contract

The variables a driver — human or agent — needs, all optional:

- `RETICULI_QUARANTINE` — `auto` (default: jail gates when the platform has
  one) · `require` (refuse without a jail) · `off`.
- `RETICULI_JAILED` — set *by* the toolchain in a jailed gate's environment:
  "you are already inside a jail — inherit, never re-apply." A conformant
  kernel honors it; the kernel check enforces it.
- `RETICULI_USAGE` — a file path handed to producers; write `{"tokens": n,
  "usd": x}` there and the realization's ledger accounts real oracle cost.
- `RETICULI_MODEL` — which model the bundled producers call
  (`producer_claude.py`, `producer_claude_agentic.py`, `producer_openai.py`).
- `RETICULI_AGENT_BUDGET` — the agentic producer's per-layer dollar cap: it
  may run the gate and iterate until it passes or the budget is spent.

## Design notes

- [`notes/basin.md`](notes/basin.md) — the basin of attraction, and self-hosting.
- [`notes/impedance.md`](notes/impedance.md) — the record as an impedance-matching problem:
  the spec, the load, the center of the Smith chart, and the minimal-cost probe.
- [`notes/landscape.md`](notes/landscape.md) — prior art and impact: what exists, what
  doesn't, and the limits that will decide it.
- [`three_machine_problem_white_paper.pdf`](three_machine_problem_white_paper.pdf)
  — the three-machine problem, stated tool-agnostically: seed design, oracle,
  residue, and the comparable-cost standard this repo implements.

Reticuli is a **basin-compiler**: it compiles diverse implementations onto one
certified claim. Pointed at its own repo, it compiles *itself* — a record whose
recipe regrows the code that passes its own tests.
