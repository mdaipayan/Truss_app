# Professional Truss Suite (2D)
**A Commercial-Grade Structural Analysis Tool**

Developed by **Mr. D Mandal**, Assistant Professor, Department of Civil Engineering, KITS Ramtek.

---

## 🛠️ Software Overview
This application provides a comprehensive environment for the linear static analysis of 2D trusses using the **Direct Stiffness Method (DSM)**. It is designed for both academic purposes and professional engineering documentation.

## 📐 Engineering Methodology
The core engine utilizes the Direct Stiffness Method to solve for nodal displacements and internal member forces.

1. **Element Stiffness Matrix**: For each member, a local stiffness matrix is generated and transformed into global coordinates using the transformation matrix:
   $$k_{global} = \frac{EA}{L} \begin{bmatrix} c^2 & cs & -c^2 & -cs \\ cs & s^2 & -cs & -s^2 \\ -c^2 & -cs & c^2 & cs \\ -cs & -s^2 & cs & s^2 \end{bmatrix}$$
   *(where $c = \cos(\theta)$ and $s = \sin(\theta)$)*

2. **Global Assembly**: Individual member matrices are assembled into a global stiffness matrix ($K_{global}$).

3. **Boundary Conditions**: Supports are handled by partitioning the matrix and solving for free Degrees of Freedom (DOF).

4. **Internal Forces**: Axial forces are calculated from the derived displacements, with positive values indicating **Compression** and negative values indicating **Tension**.

## ✨ Key Features
* **Automated Force Nature Detection**: Clearly distinguishes between Tensile and Compressive members.
* **Parallel Visualization**: Force labels are automatically aligned parallel to members for professional clarity.
* **Professional Reporting**: Generates a complete `.docx` report including:
    * Software & Developer Metadata
    * Truss Model Visualization Image
    * Nodal Displacement & Support Reaction Tables
    * Member Force & Material Property Tables

## 🚀 How to Run
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run app.py`

---
*Disclaimer: This software is intended for educational and preliminary design verification. Always verify results with manual calculations for critical structural designs.*
