# Reticuli

**Sealed, reproducible records of model-assisted work. The invariant is the
three-machine test.**

Reticuli turns informal, model-assisted work into a *claim you can re-derive* —
and version-control like a lockfile. A record is valid iff an independent **redo**
lands on the same claim. That's the whole thing; everything else is ergonomics.

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
M2  a byte-reuse (copy)  verifies from its own bytes, produces nothing
M3  an independent redo  re-produced from the recipe by any producer
valid  ⇔  root(M1) == root(M2) == root(M3)
```

The **basin of attraction** is exactly the preimage of the root: every
implementation that passes the same checks hashes to the same claim. `free`
outputs are the water; `exact`/`validated` verdicts are the shape it takes.

## Quickstart

```bash
pip install -e .

# a session
ret init                                   # git-native: ignores history, marks bytes binary
# ... write a checker.py and some code (the agent's work is traced) ...
ret run "python checker.py"                # author a gate (produces VERIFIED)
ret condense --accept VERIFIED --into rec  # draft a record and certify it cold

# an independent redo, by any producer
ret realize rec --producer "$YOUR_MODEL" --into M3

# the invariant
ret prove rec M2 M3
```

```toml
[prove]
satisfied = true
integrity = true
reuse = true
equivalence = true

   machine  root
0  M1       c124ba320206…
1  M2       c124ba320206…      # three implementations, one root
2  M3       c124ba320206…
```

See [`examples/cube`](examples/cube): three genuinely different rotating-cube
implementations (≈0.1 code similarity) all certify against one fixed checker.

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

- `ret init` gitignores the volatile history (`vapor.jsonl`, per-record ledgers)
  and writes a `.gitattributes` so git never mangles sealed bytes across
  platforms.
- Re-condensing the same session produces **no diff**; two people condensing one
  session get identical records.
- `git clone` a repo and `ret verify` its records from the committed bytes alone.

## Output

Every command prints exactly one of three shapes — a **TOML** fact sheet (one
entity), a **table** (rows), or a **tree** (a DAG) — with `--json` underneath.

## Self-hosting

Reticuli is a **basin-compiler that compiles itself** — and it does so in two
layers. `ret pack` declares a project as a record: its code the *free* outputs,
its check the *seed*, gated by running the check. Two records make up the repo,
sealed by [`scripts/selfrecord.py`](scripts/selfrecord.py):

| record | free code | seed (the check) | gate |
|---|---|---|---|
| **kernel-core** | `reticuli/{__init__,kernel}.py` | [`kernel_check.py`](kernel_check.py) | the kernel invariant → `KERNEL_OK` |
| **reticuli** (whole) | the rest of `reticuli/*.py`, **+ kernel-core's kernel** | [`whole_check.py`](whole_check.py) | the toolchain over that kernel → `VERIFIED` |

The whole record obtains its kernel from `kernel-core` as a `from` produce step —
free code it *layers on*, not bytes it pins. So `ret verify .` holds, and:

```bash
ret realize . --recursive --producer <model> --into M3
```

rehydrates **kernel-first**: it regrows `kernel-core` from `kernel_check.py`,
threads that fresh kernel up, regrows the toolchain over it, runs `whole_check.py`,
and — because all the code is free and the root is the claim — **lands on the same
whole root.** The repo rehydrates to its own claim, bottom-up. A redo with a
*different* kernel and a *different* toolchain still lands on the same two roots.

Three properties, all tested:

- **Editing the implementation keeps the root** — the code is free water.
- **Editing a check changes that layer's root** — the check *is* the claim.
- **Each layer is its own basin** — any conformant kernel gives one `kernel-core`
  root; any conformant toolchain over it gives one whole root.

The manifest is pure `{name, root}` (+ component links), no free-output hashes, so
a self-hosted record stays byte-stable under code edits and commits clean. Re-run
`scripts/selfrecord.py` when files change (it's a lockfile).

### Composition, in general

`kernel-core → whole` is one instance of a general facility: a record can depend
on other records. A dry seed that content-matches a component's output links them
as *pinned data*; a `from` produce step links a component's output as *free code*.
`ret realize --recursive` rehydrates the whole DAG bottom-up either way — the
claim reproduces from the leaves, not just one layer.

## The verbs

| phase | verb | |
|---|---|---|
| vapor | `init` · `run` · `status` | set up · record a command · where am I |
| liquid | `condense` · `verify` · `show` · `pack` · `records` · `deps` · `pull` | seal · does it hold · print the recipe · self-record · the drawer · the DAG · depend on a record |
| solid | `realize` · `realize --recursive` · `prove` | an independent redo · redo the whole component DAG · the three-machine test |

Records compose: a dry seed that matches a registry record's output links the
two (content-addressed). `ret pull` brings a component in as seeds; `ret deps`
draws the DAG; `ret realize --recursive` rehydrates it bottom-up. `solid` is a
record's view of itself; `dry` is a dependent's view of the same record.

## Design notes

- [`docs/basin.md`](docs/basin.md) — the basin of attraction, and self-hosting.

Reticuli is a **basin-compiler**: it compiles diverse implementations onto one
certified claim. Pointed at its own repo, it compiles *itself* — a record whose
recipe regrows the code that passes its own tests.
