import numpy as np

class Node:
    def __init__(self, id, x, y, rx=0, ry=0):
        self.id = id
        self.x = x; self.y = y
        self.rx = rx; self.ry = ry
        self.ux = 0.0; self.uy = 0.0

class Member:
    def __init__(self, id, node_i, node_j, E, A):
        self.id = id
        self.node_i = node_i
        self.node_j = node_j
        self.E = E
        self.A = A
        self.force = 0.0
        self.k_global_matrix = None # NEW: Store element stiffness matrix

    @property
    def length(self):
        return np.sqrt((self.node_j.x - self.node_i.x)**2 + (self.node_j.y - self.node_i.y)**2)

    def get_k_global(self):
        L = self.length
        c = (self.node_j.x - self.node_i.x) / L
        s = (self.node_j.y - self.node_i.y) / L
        k_local = (self.E * self.A / L) * np.array([
            [c*c, c*s, -c*c, -c*s],
            [c*s, s*s, -c*s, -s*s],
            [-c*c, -c*s, c*c, c*s],
            [-c*s, -s*s, c*s, s*s]
        ])
        self.k_global_matrix = k_local # NEW: Save it for the UI
        return k_local

    def calculate_force(self):
        L = self.length
        c = (self.node_j.x - self.node_i.x) / L
        s = (self.node_j.y - self.node_i.y) / L
        T = np.array([-c, -s, c, s])
        u_global = np.array([self.node_i.ux, self.node_i.uy, self.node_j.ux, self.node_j.uy])
        self.force = (self.E * self.A / L) * np.dot(T, u_global)
        return self.force

class TrussSystem:
    def __init__(self):
        self.nodes = []
        self.members = []
        self.loads = {}
        # NEW: Storage for Glass-Box visualization
        self.K_global = None 
        self.K_reduced = None
        self.F_reduced = None
        self.free_dofs = []

    def solve(self):
        n_dof = 2 * len(self.nodes)
        K_global = np.zeros((n_dof, n_dof))
        F_global = np.zeros(n_dof)

        for dof, force in self.loads.items():
            F_global[dof] = force

        for mbr in self.members:
            k = mbr.get_k_global()
            dofs = [2*mbr.node_i.id-2, 2*mbr.node_i.id-1, 2*mbr.node_j.id-2, 2*mbr.node_j.id-1]
            for i in range(4):
                for j in range(4):
                    K_global[dofs[i], dofs[j]] += k[i, j]

        self.K_global = K_global # NEW: Store Global Matrix

        free_dofs = [2*n.id-2 for n in self.nodes if n.rx == 0] + [2*n.id-1 for n in self.nodes if n.ry == 0]
        free_dofs.sort()
        self.free_dofs = free_dofs # NEW: Store partitioned indices
        
        K_reduced = K_global[np.ix_(free_dofs, free_dofs)]
        F_reduced = F_global[free_dofs]
        
        self.K_reduced = K_reduced # NEW: Store Reduced Matrix
        self.F_reduced = F_reduced
        
        U_reduced = np.linalg.solve(K_reduced, F_reduced)
        
        for i, dof in enumerate(free_dofs):
            node_idx = dof // 2
            if dof % 2 == 0: self.nodes[node_idx].ux = U_reduced[i]
            else: self.nodes[node_idx].uy = U_reduced[i]
        
        U_all = np.zeros(n_dof) 
        for node in self.nodes:
            U_all[2*node.id-2] = node.ux
            U_all[2*node.id-1] = node.uy
        
        Reactions = np.dot(K_global, U_all) - F_global 
        for node in self.nodes:
            node.rx_val = Reactions[2*node.id-2]
            node.ry_val = Reactions[2*node.id-1]
        
        return "Solved"
        
