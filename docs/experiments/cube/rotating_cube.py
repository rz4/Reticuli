import numpy as np
def rotation_matrix_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1., 0, 0], [0, c, -s], [0, s, c]])
def rotation_matrix_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1., 0], [-s, 0, c]])
def rotation_matrix_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])
