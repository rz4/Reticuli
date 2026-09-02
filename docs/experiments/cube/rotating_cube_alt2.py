import numpy as np
def _c(t): return np.cos(t)
def _s(t): return np.sin(t)
def rotation_matrix_x(a): return np.array([[1.,0,0],[0,_c(a),-_s(a)],[0,_s(a),_c(a)]])
def rotation_matrix_y(a): return np.array([[_c(a),0,_s(a)],[0,1.,0],[-_s(a),0,_c(a)]])
def rotation_matrix_z(a): return np.array([[_c(a),-_s(a),0],[_s(a),_c(a),0],[0,0,1.]])
