"""The fixed check — the basin's map. Any rotating_cube exposing the interface
is projected onto one canonical verdict, or rejected. Never regenerated."""
import numpy as np
from rotating_cube import rotation_matrix_x, rotation_matrix_y, rotation_matrix_z

ok = True
for R in (rotation_matrix_x, rotation_matrix_y, rotation_matrix_z):
    M = R(0.7)
    ok = ok and np.allclose(R(0.0), np.eye(3))          # identity at 0
    ok = ok and np.allclose(M @ M.T, np.eye(3))         # orthogonal
    ok = ok and np.isclose(np.linalg.det(M), 1.0)       # proper rotation
    ok = ok and np.allclose(R(0.3) @ R(0.4), R(0.7))    # additive composition
assert ok, "not a valid rotation basis"
open("VERIFIED", "w").write("rotation-correct\n")        # the attractor
