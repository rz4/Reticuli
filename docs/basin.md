# The basin of attraction

A certified record is a **basin of attraction**: a fixed check (the *map*) pulls
many implementations (the *free water*) onto one canonical verdict (the
*attractor* — the root). The check must be a **dry seed**, stable across
realizations; if it's regenerated alongside the thing it checks, every redo
brings its own verdict and nothing converges.

Because `root = hash(recipe + seeds + pinned verdicts)` excludes the free
outputs, the basin is **literally the preimage of the root**. `ret prove` doesn't
compare outputs — it checks that three roots are equal.

## Self-hosting

Point Reticuli at its own repo and it becomes a **basin-compiler that compiles
itself**: a record whose recipe *produces* the code (free) gated by the test
suite (the check). `ret realize .` regrows a fresh implementation; if it passes
the tests, it lands on the same root — the repo, rehydrated from its own
`.reticuli/`. Grown rung by rung (kernel → authoring → cli → whole), the repo's
`.reticuli/` becomes a deterministic, git-committed genome; `src/` is one
phenotype in the basin.
