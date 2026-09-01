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

## The verbs

| phase | verb | |
|---|---|---|
| vapor | `init` · `run` · `status` | set up · record a command · where am I |
| liquid | `condense` · `verify` · `show` | seal · does it hold · print the recipe |
| solid | `realize` · `prove` | an independent redo · the three-machine test |

## Design notes

- [`docs/basin.md`](docs/basin.md) — the basin of attraction, and self-hosting.

Reticuli is a **basin-compiler**: it compiles diverse implementations onto one
certified claim. Pointed at its own repo, it compiles *itself* — a record whose
recipe regrows the code that passes its own tests.
