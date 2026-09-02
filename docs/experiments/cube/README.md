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
independent implementations. Requires `numpy` for the checker.
