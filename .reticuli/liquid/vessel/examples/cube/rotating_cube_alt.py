import numpy as np
# same mathematics, different code (dispatch through a helper): different water.
def _rot(axis, t):
    ct, st = float(np.cos(t)), float(np.sin(t))
    return {
        "x": np.array([[1., 0, 0], [0, ct, -st], [0, st, ct]]),
        "y": np.array([[ct, 0, st], [0, 1., 0], [-st, 0, ct]]),
        "z": np.array([[ct, -st, 0], [st, ct, 0], [0, 0, 1.]]),
    }[axis]
def rotation_matrix_x(a): return _rot("x", a)
def rotation_matrix_y(a): return _rot("y", a)
def rotation_matrix_z(a): return _rot("z", a)
