import numpy as np
import math

class Node:
    def __init__(self, id, x, y, rx, ry):
        self.id = id
        self.x = x
        self.y = y
        self.rx = rx  # 1 if restrained, 0 if free
        self.ry = ry
        self.ux = 0.0
        self.uy = 0.0
        self.rx_val = 0.0
        self.ry_val = 0.0

class Member:
    def __init__(self, id, node_i, node_j, E, A):
        if E <= 0:
            raise ValueError(f"Member {id} has invalid Young's Modulus (E must be > 0).")
        if A <= 0:
            raise ValueError(f"Member {id} has invalid Area (A must be > 0).")
            
        self.id = id
        self.node_i = node_i
        self.node_j = node_j
        self.E = E
        self.A = A
        self.k_global_matrix = None 
        
        # Instantly check for zero-length members
        if self.get_length() == 0:
            raise ValueError(f"Member {id} has zero length. Nodes {node_i.id} and {node_j.id} share the same coordinates.")

    def get_length(self):
        dx = self.node_j.x - self.node_i.x
        dy = self.node_j.y - self.node_i.y
        return math.sqrt(dx**2 + dy**2)


    def get_k_global(self):
        L = self.get_length()
        c = (self.node_j.x - self.node_i.x) / L
        s = (self.node_j.y - self.node_i.y) / L
        
        # Element stiffness matrix in global coordinates
        k = (self.E * self.A / L) * np.array([
            [ c**2,   c*s,   -c**2,  -c*s],
            [ c*s,    s**2,  -c*s,   -s**2],
            [-c**2,  -c*s,    c**2,   c*s],
            [-c*s,   -s**2,   c*s,    s**2]
        ])
        self.k_global_matrix = k # Store for Glass-Box exploration
        return k

    def calculate_force(self):
        L = self.get_length()
        c = (self.node_j.x - self.node_i.x) / L
        s = (self.node_j.y - self.node_i.y) / L
        
        # Transformation vector
        T = np.array([-c, -s, c, s])
        
        # Global nodal displacements for this member
        u = np.array([self.node_i.ux, self.node_i.uy, self.node_j.ux, self.node_j.uy])
        
        # Calculate final axial force
        force = (self.E * self.A / L) * np.dot(T, u)
        return force

class TrussSystem:
    def __init__(self):
        self.nodes = []
        self.members = []
        self.loads = {}  # format -> dof_index: force_value
        self.K_global = None
        self.K_reduced = None
        self.F_reduced = None

    def solve(self):
        n_dof = 2 * len(self.nodes)
        K_global = np.zeros((n_dof, n_dof))
        F_global = np.zeros(n_dof)

        # 1. Populate Global Force Vector
        for dof, force in self.loads.items():
            F_global[dof] = force

        # 2. Vectorized Global Matrix Assembly (Fix for Critique 2)
        for mbr in self.members:
            k = mbr.get_k_global()
            dofs = [2*mbr.node_i.id-2, 2*mbr.node_i.id-1, 2*mbr.node_j.id-2, 2*mbr.node_j.id-1]
            
            # NumPy's advanced indexing to inject the 4x4 into the Global Matrix instantly
            K_global[np.ix_(dofs, dofs)] += k

        self.K_global = K_global # Store Global Matrix for Glass-Box

        # 3. Boundary Condition Partitioning
        free_dofs = []
        for n in self.nodes:
            if n.rx == 0: free_dofs.append(2*n.id-2)
            if n.ry == 0: free_dofs.append(2*n.id-1)
        free_dofs.sort()
        self.free_dofs = free_dofs 
        
        K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F_global[free_dofs]
        
        self.K_reduced = K_reduced # Store Reduced Matrix for Glass-Box
        self.F_reduced = F_reduced
        
        # 4. Pre-Solve Stability Check (Fix for Critique 3)
        if K_reduced.size == 0:
            raise ValueError("No free degrees of freedom. The structure is completely locked.")
            
        # Check the condition number to detect rigid-body motion or unstable mechanisms
        cond_num = np.linalg.cond(K_reduced)
        if cond_num > 1e12: 
            raise ValueError("Structural Instability Detected! The stiffness matrix is singular. Please check your boundary conditions and ensure the truss is fully restrained against moving or spinning.")
            
        try:
            # Solve for Displacements (U = K^-1 * F)
            U_reduced = np.linalg.solve(K_reduced, F_reduced)
        except np.linalg.LinAlgError:
            raise ValueError("Structural Instability Detected! The stiffness matrix is singular. Please check your boundary conditions.")
        
        # Map reduced displacements back to the global node objects
        for i, dof in enumerate(free_dofs):
            node_idx = dof // 2
            if dof % 2 == 0: 
                self.nodes[node_idx].ux = U_reduced[i]
            else: 
                self.nodes[node_idx].uy = U_reduced[i]
        
        # 5. Calculate Support Reactions: R = K*U - F
        U_all = np.zeros(n_dof) 
        for node in self.nodes:
            U_all[2*node.id-2] = node.ux
            U_all[2*node.id-1] = node.uy
        
        Reactions = np.dot(K_global, U_all) - F_global 
        for node in self.nodes:
            node.rx_val = Reactions[2*node.id-2]
            node.ry_val = Reactions[2*node.id-1]
        
        return "Solved"

