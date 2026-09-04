# The guide

The long form. The [README](../README.md) is the 60-second contact layer — a
free output of the repo's own self-record, gated by
[`checks/docs_check.py`](../checks/docs_check.py); this guide is where the depth lives.

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

## What a root promises (and what it doesn't)

`root = hash(recipe + seeds + verdicts)` pins the **claim** — these bytes
satisfy these checks — and deliberately not the implementation. Off the checks'
support, behavior is unconstrained; that width is the basin, and it is the
point. So a realization can pass every gate, match the root, and `audit` clean,
yet still carry behavior the checks never exercise. (Demonstrated: a mutant
kernel that imports the network and writes a beacon on `seal` lands the exact
root and audits clean — root-match and audit do not see it.)

Trust in a record therefore climbs a ladder, each rung a different question:

1. **root match** — the same claim (identity).
2. **audit** — the verdicts are earned by these bytes, not carried (no
   fabrication).
3. **attestation** — a named keyholder ran this realization and signed the
   statement (*who* — transport provenance).
4. **solid mint** — these exact bytes, frozen and ceremony-signed (*what*).

A record on disk is **liquid**: it gives you rungs 1–3, never 4 — the free
implementation is unpinned by construction. Pull a record from someone you can
name and rely on their attestation; pull from a stranger and you must read the
code or wait for a solid — the root alone was never a claim about the bytes.
Where a property cleanly separates every honest realization from a class of
payloads, it is promoted to a check instead of left to trust: the kernel's
**stdlib-only, no-network** rule is the first such clause — every honest kernel
satisfies it, a phone-home payload cannot. Where no property separates the two,
no gate can help and the ladder is the honest answer.

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

| rung | own stratum (free) | seed (the check, under `checks/`) | claims |
|---|---|---|---|
| **kernel-core** | `reticuli/{__init__,kernel}.py` | `kernel_check.py` | the invariant → `KERNEL_OK` |
| **exchange** | `+ {registry,transfer,attest}.py` | `exchange_check.py` | records meet records, and other parties → `EXCHANGE_OK` |
| **authoring** | `+ {render,condense,feedback,pack}.py` | `authoring_check.py` | sessions become records → `AUTHORING_OK` |
| **agents** | `+ hooks.py` | `agents_check.py` | the agent handshake → `AGENTS_OK` |
| **surface** | `+ {cli,__main__}.py` | `surface_check.py` | the human handshake → `SURFACE_OK` |
| **workshop** | `+ scripts/*.py, tests/*.py` | `workshop_check.py` | the bench: suite passes AND has teeth (a killed `seal` must fail it) → `WORKSHOP_OK` |
| **vessel** | `+ pyproject, CI, git skin` | `vessel_check.py` | the skin it ships in; LICENSE and logo pinned as seeds → `VESSEL_OK` |
| **reticuli** (documentation) | `+ README.md, docs/guide.md` | [`docs_check.py`](../checks/docs_check.py) | the hand-off: a minute for contact, depth for engineers and agents, every verb and env var documented, no lies → `VERIFIED` |

`tests/` is where knowledge is *discovered* (free water, any bytes that pass);
`checks/` is where it is *ratified* (dry seeds, identity). Promotion is
physical: move a test's knowledge across that boundary and re-mint — the
directory line is the type system.

Each rung obtains the layers beneath it from its predecessor as `from` produce
steps — free code it *layers on*, not bytes it pins. Even the README is free
water: its word budget and honesty are the claim. So `ret verify .` holds,
`ret tree .` draws the chain, and:

```bash
ret realize . --recursive --producer <model> --into M3
```

rehydrates **leaf-first**: it regrows the kernel from `checks/kernel_check.py`,
threads it up through exchange, authoring, agents, and the surface, writes a
fresh README against `checks/docs_check.py`, and — because all of it is free and the
root is the claim — **lands on the same roots, rung by rung.** Each rung pays
its own ledger, so a recursive redo prices every layer separately: what
the invariant costs to regrow vs. what the volatile handshakes cost. Today's
roots, inner to outer: `89651ed8…`, `9ee4b5be…`, `b7610cbb…`, `c3b3e782…`,
`e88c86e4…`, workshop `5c229b2e…`, vessel `e4e7da9a…`, whole `cc1a10e7…`.
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
agentic lands more, for a measured extra cost. The room holds only the check
and the already-free lower layers — no reference — so the agent iterating
against the gate is honest "make the tests pass," and realize's jailed gate
stays the authoritative verdict.
[`scripts/producer_openai.py`](../scripts/producer_openai.py) is the same
oneshot contract for OpenAI models. Either way the redo's ledger accounts what
the model actually cost: producers report real token/usd usage back through
`$RETICULI_USAGE`, one line per call.

### Composition, in general

`kernel-core → whole` is one instance of a general facility: a record can
depend on other records. A dry seed that content-matches a component's output
links them as *pinned data*; a `from` produce step links a component's output
as *free code*. `ret realize --recursive` rehydrates the whole DAG bottom-up
either way — the claim reproduces from the leaves, not just one layer.

## The verbs

`ret --help` lists them in five process groups — read top to bottom, it *is*
the workflow, and it is the same map on both surfaces (the grouping is claimed
by the surface check; the wording is free water).

- **session** (vapor): `init` sets up the store and git skin · `hooks` wires the
  agent to the trace · `status` prints phase and freshness.
- **author** (M1, vapor → liquid): `run` records a command in the trace ·
  `condense` drafts a record from it and certifies it cold · `verify` recomputes
  the root and compares it with the sealed manifest.
- **transfer** (M2, liquid): `export` writes the record's declared content to a
  deterministic tar · `import` unpacks it and verifies from the bytes alone ·
  `audit` re-runs the gates so the verdicts are re-earned, never carried.
- **redo** (M3, liquid → solid): `realize` rebuilds the free code in a clean room
  (`--recursive` rehydrates the whole component DAG, bottom-up) · `prove` runs the
  three-machine test (`--freeze-dry` mints M1 solid on success) · `attest` signs a
  realization with `ssh-keygen -Y` (`--check` verifies the signatures).
- **compose**: `pack` seals a project directory as a self-record · `pull` brings
  a record in as a dependency · `tree` shows a session's dry/wet plus its
  drawer's dependency graph, or a sealed record's anatomy · `records` lists the
  drawer.

`ret hook` exists but is internal — the installed agent hooks invoke it to
append one trace event; you never type it. Records compose: a dry seed that
matches a registry record's output links the two (content-addressed); `solid` is
a record's view of itself, `dry` a dependent's view of the same record.

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

Reticuli is a **basin-compiler**: it compiles diverse implementations onto one
certified claim. Pointed at its own repo, it compiles *itself* — a record whose
recipe regrows the code that passes its own tests.
