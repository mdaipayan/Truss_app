import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from core_solver import TrussSystem, Node, Member
import datetime
import os
from visualizer import draw_undeformed_geometry, draw_results_fbd

st.set_page_config(page_title="Professional Truss Suite", layout="wide")
st.title("🏗️ Professional Truss Analysis Developed by D Mandal")

# Persistent figure initialization
fig = go.Figure()
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Input Data")
    
    # ---------------------------------------------------------
    # NEW PEDAGOGICAL FEATURE: Load Benchmark Data Button
    # ---------------------------------------------------------
    st.info("💡 **First time here?** Load the benchmark 9-member Pratt truss to see how data is formatted.")
    if st.button("📚 Load 9-Member Pratt Truss Benchmark"):
        # Pre-fill Nodes (X, Y, Restrain_X, Restrain_Y)
        st.session_state['nodes_data'] = pd.DataFrame([
            [0.0, 0.0, 1, 1],  # Node 1: Origin, Pin Support
            [3.0, 0.0, 0, 0],  # Node 2: Bottom Mid
            [6.0, 0.0, 0, 1],  # Node 3: Bottom Right, Roller Support
            [0.0, 3.0, 0, 0],  # Node 4: Top Left
            [3.0, 3.0, 0, 0],  # Node 5: Top Mid
            [6.0, 3.0, 0, 0]   # Node 6: Top Right
        ], columns=["X", "Y", "Restrain_X", "Restrain_Y"])
        
        # Pre-fill Members (Node_I, Node_J, Area, E)
        st.session_state['members_data'] = pd.DataFrame([
            [1, 2, 0.01, 2e11],  # M1: Bottom Chord Left
            [2, 3, 0.01, 2e11],  # M2: Bottom Chord Right
            [4, 5, 0.01, 2e11],  # M3: Top Chord Left
            [5, 6, 0.01, 2e11],  # M4: Top Chord Right
            [1, 4, 0.01, 2e11],  # M5: End Vertical Left
            [3, 6, 0.01, 2e11],  # M6: End Vertical Right
            [2, 5, 0.01, 2e11],  # M7: Central Vertical
            [2, 4, 0.01, 2e11],  # M8: Left Diagonal
            [2, 6, 0.01, 2e11]   # M9: Right Diagonal
        ], columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"])
        
        # Pre-fill Loads (Node_ID, Force_X, Force_Y)
        st.session_state['loads_data'] = pd.DataFrame([
            [5, 0.0, -100000.0], # 100 kN downward at Node 5
            [4, 10000.0, 0.0]    # 10 kN horizontal at Node 4
        ], columns=["Node_ID", "Force_X (N)", "Force_Y (N)"])
        
        # Clear any previous solved states to reset the view
        if 'solved_truss' in st.session_state:
            del st.session_state['solved_truss']

    # Initialize empty dataframes in session_state if they don't exist yet
    if 'nodes_data' not in st.session_state:
        st.session_state['nodes_data'] = pd.DataFrame(columns=["X", "Y", "Restrain_X", "Restrain_Y"])
        st.session_state['members_data'] = pd.DataFrame(columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"])
        st.session_state['loads_data'] = pd.DataFrame(columns=["Node_ID", "Force_X (N)", "Force_Y (N)"])

    with st.expander("📘 Guide: How to enter Support Conditions"):
        st.markdown("""
        ### **Understanding Support Conditions (Boundary Conditions)**
        For a truss to be stable and not float away into space, it must be attached to the ground. In structural analysis, we call these **Boundary Conditions**. 
        
        In this software, you define supports using binary logic (0 or 1) for the X (horizontal) and Y (vertical) directions:
        * **`0` = Free to move:** The joint can translate in this direction. No reaction force is generated.
        * **`1` = Restrained (Locked):** The joint is locked and cannot move in this direction. A reaction force will develop here to keep it in place.

        #### **How to fill the Input Table:**
        
        **1. Free Node (Standard Truss Joint)**
        * **What it is:** A normal joint connecting members in the air.
        * **Input:** `Restrain_X = 0`, `Restrain_Y = 0`
        * **Result:** The node can move freely under load.

        **2. Pin Support (Hinged Support)**
        * **What it is:** Think of a bolted hinge. The node cannot move left, right, up, or down. It is completely locked in place.
        * **Input:** `Restrain_X = 1`, `Restrain_Y = 1`
        * **Result:** Generates both horizontal ($R_x$) and vertical ($R_y$) reaction forces.

        **3. Roller Support (Horizontal Surface)**
        * **What it is:** Think of a skateboard on a flat floor. It is free to roll left and right, but the floor stops it from moving up and down.
        * **Input:** `Restrain_X = 0`, `Restrain_Y = 1`
        * **Result:** Generates only a vertical reaction force ($R_y$).

        **4. Roller Support (Vertical Surface)**
        * **What it is:** A roller pushed against a wall. It can slide up and down the wall freely, but cannot move left or right through the wall.
        * **Input:** `Restrain_X = 1`, `Restrain_Y = 0`
        * **Result:** Generates only a horizontal reaction force ($R_x$).
        
        *Note: To ensure your truss is stable, you generally need at least three total restraints (for example, one Pin and one Roller) that are not all parallel.*
        """)
    
    st.subheader("Nodes")
    node_df = st.data_editor(st.session_state['nodes_data'], num_rows="dynamic", key="nodes")

    # --- Guide for Members ---
    with st.expander("📘 Guide: How to connect Members & set Properties"):
        st.markdown(r"""
        ### **Defining Truss Members**
        A truss is made of straight members connected at joints (nodes). Each member needs to know where it starts, where it ends, how thick it is, and what material it is made of.
        
        #### **How to fill the Input Table:**
        
        **1. Connectivity (Node_I and Node_J)**
        * **What it is:** The starting and ending nodes of the member.
        * **Input:** Enter the integer ID of the nodes (e.g., `1` and `2`). 
        * *Note:* For static truss analysis, the order does not matter (connecting Node 1 to 2 is the same as connecting Node 2 to 1).

        **2. Cross-Sectional Area (Area sq.m)**
        * **What it is:** The physical thickness of the member, represented by its cross-sectional area ($A$).
        * **Input:** Enter the value strictly in **square meters ($m^2$)**. 
        * *Example:* If your member area is $100 \text{ cm}^2$, you must enter `0.01`.

        **3. Young's Modulus (E N/sq.m)**
        * **What it is:** The stiffness of the material ($E$), which dictates how much it stretches under force.
        * **Input:** Enter the value in **Pascals ($N/m^2$)**.
        * *Pro-Tip (Scientific Notation):* Structural values are often huge. For standard steel ($200 \text{ GPa}$ or $200,000,000,000 \text{ Pa}$), you can simply type `2e11`. Python will understand this perfectly!
        """)
    
    st.subheader("Members")
    member_df = st.data_editor(st.session_state['members_data'], num_rows="dynamic", key="members")

    # --- Guide for Loads ---
    with st.expander("📘 Guide: How to apply External Loads"):
        st.markdown(r"""
        ### **Applying Nodal Loads**
        In standard truss analysis, external forces can only be applied directly to the joints (nodes), not to the middle of the members. 
        
        This software uses the standard **Cartesian Sign Convention**.

        #### **How to fill the Input Table:**
        
        **1. Target Node (Node_ID)**
        * **Input:** Enter the integer ID of the node where the force is pushing or pulling.

        **2. Horizontal Force (Force_X)**
        * **Input:** Enter the force magnitude in **Newtons ($N$)**.
        * **Positive (`+`):** Force acts to the **Right** $\rightarrow$
        * **Negative (`-`):** Force acts to the **Left** $\leftarrow$
        * *Example:* For a $10 \text{ kN}$ wind load blowing to the right, enter `10000`.

        **3. Vertical Force (Force_Y)**
        * **Input:** Enter the force magnitude in **Newtons ($N$)**.
        * **Positive (`+`):** Force acts **Upward** $\uparrow$
        * **Negative (`-`):** Force acts **Downward** $\downarrow$ (like gravity or dead load).
        * *Example:* For a $100 \text{ kN}$ downward weight, you must enter `-100000`.
        """)
        
    st.subheader("Nodal Loads")
    load_df = st.data_editor(st.session_state['loads_data'], num_rows="dynamic", key="loads")
    
    if st.button("Calculate Results"):
        try:
            ts = TrussSystem()
            for i, row in node_df.iterrows():
                ts.nodes.append(Node(i+1, float(row['X']), float(row['Y']), int(row['Restrain_X']), int(row['Restrain_Y'])))
            for i, row in member_df.iterrows():
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                ts.members.append(Member(i+1, ts.nodes[ni], ts.nodes[nj], float(row['E (N/sq.m)']), float(row['Area(sq.m)'])))
            for i, row in load_df.iterrows():
                node_id = int(row['Node_ID'])
                ts.loads[2*node_id-2] = float(row['Force_X (N)'])
                ts.loads[2*node_id-1] = float(row['Force_Y (N)'])
            
            ts.solve()
            st.session_state['solved_truss'] = ts
            st.success("Analysis Complete!")
        except Exception as e:
            st.error(f"Error: {e}")

    # Export Results Section
    if 'solved_truss' in st.session_state:
        st.header("3. Export Results")
        from report_gen import generate_report
        
        ts_solved = st.session_state['solved_truss']
        
        if st.button("🚀 Prepare Professional Report"):
            with st.spinner("Generating Professional Report..."):
                # Use the figure from session state
                current_fig = st.session_state.get('current_fig', fig)
                
                # Logic Fix: generate_report now handles Kaleido saving internally
                generate_report(ts_solved, fig=current_fig)
                
                # Logic Fix: Verify file existence before opening to avoid FileNotFoundError
                if os.path.exists("Analysis_Report.docx"):
                    with open("Analysis_Report.docx", "rb") as f:
                        st.download_button(
                            label="📥 Download Word Report",
                            data=f,
                            file_name=f"Mandal_Truss_Analysis_{datetime.date.today()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                else:
                    st.error("Report generation failed. Please check environment permissions.")
 
with col2:
    st.header("2. Model Visualization")
    
    tab1, tab2 = st.tabs(["🏗️ Undeformed Geometry", "📊 Structural Forces (Results)"])

    # ---------------------------------------------------------
    # TAB 1: BASE MODEL
    # ---------------------------------------------------------
    with tab1:
        # Call the external visualization function
        fig_base, node_errors, member_errors, load_errors = draw_undeformed_geometry(node_df, member_df, load_df)
        
        # Display Pedagogical Warnings for any detected typing errors
        if node_errors:
            st.warning(f"⚠️ **Geometry Warning:** Invalid data at Node row(s): {', '.join(node_errors)}. Please ensure coordinates are numbers.")
        if member_errors:
            st.warning(f"⚠️ **Connectivity Warning:** Cannot draw {', '.join(member_errors)}. Ensure Node IDs exist and are numbers.")
        if load_errors:
            st.warning(f"⚠️ **Loads Warning:** Invalid data at Loads table row(s): {', '.join(load_errors)}.")

        # Render the chart
        st.plotly_chart(fig_base, use_container_width=True)

    # ---------------------------------------------------------
    # TAB 2: RESULTS (Free Body Diagram)
    # ---------------------------------------------------------
    with tab2:
        if 'solved_truss' in st.session_state:
            ts = st.session_state['solved_truss']
            
            # Call the external visualization function
            fig_res = draw_results_fbd(ts)
            
            # Save the beautiful chart for the word report and render it
            st.session_state['current_fig'] = fig_res 
            st.plotly_chart(fig_res, use_container_width=True)
        else:
            st.info("👈 Input loads and click 'Calculate Results' to view the force diagram.")

# ---------------------------------------------------------
# NEW SECTION: THE "GLASS BOX" PEDAGOGICAL EXPLORER
# ---------------------------------------------------------
if 'solved_truss' in st.session_state:
    st.markdown("---")
    st.header("🎓 Educational Glass-Box: Intermediate Matrix Steps")
    st.info("Explore the internal matrix formations of the Direct Stiffness Method. Compare the theoretical formulas with the numerical matrices generated for your specific truss.")
    
    ts = st.session_state['solved_truss']
    
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.subheader("1. Element Stiffness Matrices ($k$)")
        
        # Display the theory
        st.markdown("**Theoretical Formulation:**")
        st.latex(r"""
        k = \frac{EA}{L} \begin{bmatrix} 
        c^2 & cs & -c^2 & -cs \\ 
        cs & s^2 & -cs & -s^2 \\ 
        -c^2 & -cs & c^2 & cs \\ 
        -cs & -s^2 & cs & s^2 
        \end{bmatrix}
        """)
        st.markdown(r"Where $c = \cos(\theta) = \frac{\Delta x}{L}$ and $s = \sin(\theta) = \frac{\Delta y}{L}$.")
        
        # --- THE FIX: Safety check for empty member lists ---
        if ts.members: 
            mbr_opts = [f"Member {m.id}" for m in ts.members]
            sel_mbr = st.selectbox("Select Member to view its calculated 4x4 matrix:", mbr_opts)
            
            if sel_mbr: # Only run this if a member is actually selected!
                idx = int(sel_mbr.split(" ")[1]) - 1
                if ts.members[idx].k_global_matrix is not None:
                    df_k = pd.DataFrame(ts.members[idx].k_global_matrix)
                    st.dataframe(df_k.style.format("{:.2e}"))
                else:
                    st.error("Matrix not found. Please check your member inputs.")
        else:
            st.warning("⚠️ No members found. Please define your members in the Input Table and click Calculate.")
        
    with g_col2:
        st.subheader("2. Global Assembly & Partitioning")
        
        # Display the theory
        st.markdown("**Matrix Partitioning:**")
        st.latex(r"""
        \begin{bmatrix} F_f \\ F_s \end{bmatrix} = 
        \begin{bmatrix} K_{ff} & K_{fs} \\ K_{sf} & K_{ss} \end{bmatrix} 
        \begin{bmatrix} U_f \\ U_s \end{bmatrix}
        """)
        st.markdown(r"The $2n \times 2n$ global stiffness matrix is partitioned into free ($f$) and restrained ($s$) degrees of freedom.")
        
        # Display the numerical global matrix
        with st.expander("View Full Unpartitioned Global Matrix ($K_{global}$)"):
            df_K = pd.DataFrame(ts.K_global)
            st.dataframe(df_K.style.format("{:.2e}"))
            
        # Display the reduced system theory and numerical output
        with st.expander("View Reduced System ($K_{ff} \cdot U_f = F_f$)"):
            st.markdown("**Solving for Unknown Displacements:**")
            st.markdown("Since displacements at rigid supports are zero ($U_s = 0$), the system reduces to:")
            st.latex(r"F_f = K_{ff} U_f \implies U_f = K_{ff}^{-1} F_f")
            
            st.write("**Reduced Stiffness Matrix ($K_{ff}$):**")
            df_Kff = pd.DataFrame(ts.K_reduced)
            st.dataframe(df_Kff.style.format("{:.2e}"))
            
            st.write("**Active Force Vector ($F_f$):**")
            st.write(ts.F_reduced)




