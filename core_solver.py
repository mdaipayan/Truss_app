import numpy as np
import math
from typing import List, Dict, Optional

class Node:
    def __init__(self, id: int, x: float, y: float, rx: int, ry: int):
        self.id = id
        self.x = x
        self.y = y
        self.rx = rx  
        self.ry = ry
        self.ux: float = 0.0
        self.uy: float = 0.0
        self.rx_val: float = 0.0
        self.ry_val: float = 0.0

class Member:
    def __init__(self, id: int, node_i: Node, node_j: Node, E: float, A: float):
        if E <= 0: raise ValueError(f"Member {id} has invalid Young's Modulus (E > 0).")
        if A <= 0: raise ValueError(f"Member {id} has invalid Area (A > 0).")
            
        self.id = id
        self.node_i = node_i
        self.node_j = node_j
        self.E = E
        self.A = A
        self.k_global_matrix: Optional[np.ndarray] = None 
        
        # --- NEW: Store intermediate Kinematics for the Glass Box ---
        self.L: float = 0.0
        self.c: float = 0.0
        self.s: float = 0.0
        self.T_vector: Optional[np.ndarray] = None
        self.u_local: Optional[np.ndarray] = None
        self.internal_force: float = 0.0
        
        if self.get_length() == 0:
            raise ValueError(f"Member {id} has zero length.")

    def get_length(self) -> float:
        dx = self.node_j.x - self.node_i.x
        dy = self.node_j.y - self.node_i.y
        return math.sqrt(dx**2 + dy**2)

    def get_k_global(self) -> np.ndarray:
        self.L = self.get_length()
        self.c = (self.node_j.x - self.node_i.x) / self.L
        self.s = (self.node_j.y - self.node_i.y) / self.L
        
        k = (self.E * self.A / self.L) * np.array([
            [ self.c**2,   self.c*self.s,   -self.c**2,  -self.c*self.s],
            [ self.c*self.s,    self.s**2,  -self.c*self.s,   -self.s**2],
            [-self.c**2,  -self.c*self.s,    self.c**2,   self.c*self.s],
            [-self.c*self.s,   -self.s**2,   self.c*self.s,    self.s**2]
        ])
        self.k_global_matrix = k 
        return k

    def calculate_force(self) -> float:
        # Calculate and STORE intermediate variables for the UI
        self.L = self.get_length()
        self.c = (self.node_j.x - self.node_i.x) / self.L
        self.s = (self.node_j.y - self.node_i.y) / self.L
        
        self.T_vector = np.array([-self.c, -self.s, self.c, self.s])
        self.u_local = np.array([self.node_i.ux, self.node_i.uy, self.node_j.ux, self.node_j.uy])
        
        force = (self.E * self.A / self.L) * np.dot(self.T_vector, self.u_local)
        self.internal_force = float(force)
        return self.internal_force

class TrussSystem:
    def __init__(self):
        self.nodes: List[Node] = []
        self.members: List[Member] = []
        self.loads: Dict[int, float] = {}  
        self.K_global: Optional[np.ndarray] = None
        self.K_reduced: Optional[np.ndarray] = None
        self.F_reduced: Optional[np.ndarray] = None
        self.U_global: Optional[np.ndarray] = None # NEW: Store final displacement vector
        self.free_dofs: List[int] = []

    def solve(self) -> str:
        n_dof = 2 * len(self.nodes)
        K_global = np.zeros((n_dof, n_dof))
        F_global = np.zeros(n_dof)

        for dof, force in self.loads.items():
            F_global[dof] = force

        for mbr in self.members:
            k = mbr.get_k_global()
            dofs = [2*mbr.node_i.id-2, 2*mbr.node_i.id-1, 2*mbr.node_j.id-2, 2*mbr.node_j.id-1]
            K_global[np.ix_(dofs, dofs)] += k

        self.K_global = K_global 

        free_dofs = []
        for n in self.nodes:
            if n.rx == 0: free_dofs.append(2*n.id-2)
            if n.ry == 0: free_dofs.append(2*n.id-1)
        free_dofs.sort()
        self.free_dofs = free_dofs 
        
        K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F_global[free_dofs]
        
        self.K_reduced = K_reduced 
        self.F_reduced = F_reduced
        
        if K_reduced.size == 0:
            raise ValueError("No free degrees of freedom.")
            
        cond_num = np.linalg.cond(K_reduced)
        if cond_num > 1e12: 
            raise ValueError("Structural Instability Detected! The stiffness matrix is singular.")
            
        try:
            U_reduced = np.linalg.solve(K_reduced, F_reduced)
        except np.linalg.LinAlgError:
            raise ValueError("Structural Instability Detected! The stiffness matrix is singular.")
        
        for i, dof in enumerate(free_dofs):
            node_idx = dof // 2
            if dof % 2 == 0: self.nodes[node_idx].ux = U_reduced[i]
            else: self.nodes[node_idx].uy = U_reduced[i]
        
        U_all = np.zeros(n_dof) 
        for node in self.nodes:
            U_all[2*node.id-2] = node.ux
            U_all[2*node.id-1] = node.uy
            
        self.U_global = U_all # Store for Glass Box
        
        Reactions = np.dot(K_global, U_all) - F_global 
        for node in self.nodes:
            node.rx_val = float(Reactions[2*node.id-2])
            node.ry_val = float(Reactions[2*node.id-1])
            
        # --- NEW: Pre-calculate all member kinematics & forces for Glass Box ---
        for mbr in self.members:
            mbr.calculate_force()
        
        return "Solved"
