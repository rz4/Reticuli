# The basin: a rotating cube

A fixed checker (`checker.py`) asserts the *mathematical invariants* of a rotation
basis; three different implementations all pass it and land on one root.

```bash
# seal M1 from the reference implementation
mkdir m1 && cp checker.py rotating_cube.py m1/ && cd m1
python checker.py                      # -> VERIFIED
cat > reticuli.toml <<'TOML'
[record]
name = "cube"
inputs = ["checker.py"]

[[step]]
kind = "produce"
output = "rotating_cube.py"
request = "a rotating cube exposing rotation_matrix_x/y/z"
class = "free"

[[step]]
kind = "gate"
output = "VERIFIED"
run = "python checker.py"
class = "validated"
TOML
ret verify . || ret status .           # (seal via the kernel, then verify)

# a redo with a different implementation lands on the same root
ret realize . --producer "cp ../rotating_cube_alt.py rotating_cube.py" --into ../m3
ret prove . ../m2 ../m3
```

`rotating_cube.py`, `rotating_cube_alt.py`, `rotating_cube_alt2.py` are three
independent implementations (≈0.1 code similarity). Requires `numpy` for the
checker.

## The Goodhart exhibit

This example is kept for a second reason: its checker is *deliberately weak*. It
asserts the rotation invariants but does not pin every behavior, so an identity
matrix — three functions that rotate nothing — also passes:

```python
def rotation_matrix_x(t): return np.eye(3)   # ... y, z the same
```

That is not a bug in Reticuli; it is the whole point restated as a warning. A
claim is exactly as strong as its check. Root equality certifies *satisfies the
same gate*, never *is correct* — a weak gate admits a weak (or hostile)
realization into the basin. Reticuli relocates correctness pressure into the
claim boundary and makes it explicit; it cannot repair an incomplete one. The
remedy is to strengthen the checker (e.g. assert `R(θ)·v ≠ v` for θ≠0,
orthogonality, `det = 1`, composition) — which moves the claim, as it should.

## Status: residue — and the documented Goodhart exhibit

This was an experiment, and it stays one (demoted from the claimed examples).
The three implementations share ≈0.1 code similarity yet land on one root —
the basin, concretely. But the checker is **deliberately weak, and known to
be**: it asserts orthogonality-style invariants without asserting that the
angle parameter *rotates*, so an implementation returning the identity matrix
for every θ passes (verified 2026-09-02). A weak gate proves a weak claim —
the basin admits do-nothing members. Kept unfixed as the canonical exhibit of
why claim strength, not tooling, is the load-bearing discipline.
