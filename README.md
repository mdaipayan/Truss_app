# 🏗️ Professional Truss Suite (2D)
**A Pedagogical & Commercial-Grade Structural Analysis Tool**

Developed by **Mr. D Mandal**, Assistant Professor, Department of Civil Engineering, KITS Ramtek.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red.svg)
![License](https://img.shields.io/badge/License-GPLv3-green.svg)

---

## 📖 Software Overview
The **Professional Truss Suite** is an interactive, web-based environment for the linear static analysis of 2D trusses using the **Direct Stiffness Method (DSM)**. 

Unlike commercial "black-box" software (like SAP2000 or STAAD.Pro) that hides the underlying mathematics, this application is designed as a **"Glass-Box" educational tool**. It explicitly bridges the gap between finite element theory and computational execution, allowing students to observe the formulation of local and global stiffness matrices in real-time.

## ✨ Key Features
* 🎓 **Educational "Glass-Box" Engine:** View step-by-step mathematical formulations including the $4 \times 4$ element stiffness matrices ($k$), the fully assembled unpartitioned global matrix ($K_{global}$), and the reduced partitioned system ($K_{ff} \cdot U_f = F_f$).
* 📊 **Dynamic Free-Body Diagrams (FBD):** Renders high-fidelity, interactive Plotly graphics displaying undeformed geometry, dynamically scaled load arrows, and separated horizontal/vertical support reaction vectors ($R_x$, $R_y$).
* 🔄 **Real-Time Unit Scaling:** Seamlessly toggle the visual output between Newtons (N), Kilonewtons (kN), and Meganewtons (MN) without altering the base SI solver engine.
* 📝 **1-Click Professional Reporting:** Automatically generates a comprehensive `.docx` calculation report containing software metadata, embedded high-resolution graphics, nodal displacements, and categorized member forces.
* 🛡️ **Mathematical Bulletproofing:** Includes strict physics validation (intercepts zero-length members, negative materials) and pre-solve condition number checks to identify structurally unstable mechanisms.

## 📐 Engineering Methodology
The core solver relies on standard matrix structural analysis:
1. **Local Stiffness Formulation**: Calculates $k_{local}$ using standard trigonometric transformations ($c = \cos\theta, s = \sin\theta$).
2. **Global Assembly**: Vectorized mapping of local DOFs to assemble the $2n \times 2n$ Global Stiffness Matrix.
3. **Boundary Conditions**: Partitions the matrix into free and restrained DOFs to solve for unknown displacements.
4. **Internal Forces**: Extracts member axial forces, automatically tagging them as **Tension** (Positive/Blue) or **Compression** (Negative/Red).

## 🚀 Installation & Local Setup

### Prerequisites
* Python 3.9 or newer.

### Instructions
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/mdaipayan/Truss_app.git](https://github.com/mdaipayan/Truss_app.git)
   cd Truss_app
