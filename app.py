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

st.sidebar.header("⚙️ Display Settings")
st.sidebar.info("The solver engine always calculates using base SI units (Newtons, meters). Use this setting to scale the visual output on the diagrams.")

force_display = st.sidebar.selectbox(
    "Force Display Unit", 
    options=["Newtons (N)", "Kilonewtons (kN)", "Meganewtons (MN)"], 
    index=1
)

unit_map = {
    "Newtons (N)": (1.0, "N"), 
    "Kilonewtons (kN)": (1000.0, "kN"), 
    "Meganewtons (MN)": (1000000.0, "MN")
}
current_scale, current_unit = unit_map[force_display]

fig = go.Figure()

def clear_results():
    if 'solved_truss' in st.session_state:
        del st.session_state['solved_truss']
    # Clear generated report state if inputs change
    if 'report_data' in st.session_state:
        del st.session_state['report_data']

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Input Data")
    
    st.info("💡 **First time here?** Load the benchmark 9-member Pratt truss to see how data is formatted.")
    if st.button("📚 Load 9-Member Pratt Truss Benchmark"):
        st.session_state['nodes_data'] = pd.DataFrame([
            [0.0, 0.0, 1, 1], [3.0, 0.0, 0, 0], [6.0, 0.0, 0, 1], 
            [0.0, 3.0, 0, 0], [3.0, 3.0, 0, 0], [6.0, 3.0, 0, 0]
        ], columns=["X", "Y", "Restrain_X", "Restrain_Y"])
        
        st.session_state['members_data'] = pd.DataFrame([
            [1, 2, 0.01, 2e11], [2, 3, 0.01, 2e11], [4, 5, 0.01, 2e11], 
            [5, 6, 0.01, 2e11], [1, 4, 0.01, 2e11], [3, 6, 0.01, 2e11], 
            [2, 5, 0.01, 2e11], [2, 4, 0.01, 2e11], [2, 6, 0.01, 2e11]   
        ], columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"])
        
        st.session_state['loads_data'] = pd.DataFrame([
            [5, 0.0, -100000.0], [4, 10000.0, 0.0]    
        ], columns=["Node_ID", "Force_X (N)", "Force_Y (N)"])
        
        clear_results()
        for key in ['nodes', 'members', 'loads']:
            if key in st.session_state:
                del st.session_state[key]

    if 'nodes_data' not in st.session_state:
        st.session_state['nodes_data'] = pd.DataFrame(columns=["X", "Y", "Restrain_X", "Restrain_Y"])
        st.session_state['members_data'] = pd.DataFrame(columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"])
        st.session_state['loads_data'] = pd.DataFrame(columns=["Node_ID", "Force_X (N)", "Force_Y (N)"])

    with st.expander("📘 Guide: How to enter Support Conditions"):
        st.markdown("""
        ### **Understanding Support Conditions**
        * **`0` = Free to move**
        * **`1` = Restrained (Locked)**
        """)
    st.subheader("Nodes")
    node_df = st.data_editor(st.session_state['nodes_data'], num_rows="dynamic", key="nodes", on_change=clear_results)

    with st.expander("📘 Guide: How to connect Members & set Properties"):
        st.markdown(r"""
        ### **Defining Truss Members**
        * **Connectivity:** Enter integer IDs of the start and end nodes.
        * **Properties:** Enter Area in $m^2$ and Modulus in $N/m^2$ (e.g., `2e11`).
        """)
    st.subheader("Members")
    member_df = st.data_editor(st.session_state['members_data'], num_rows="dynamic", key="members", on_change=clear_results )

    with st.expander("📘 Guide: How to apply External Loads"):
        st.markdown(r"""
        ### **Applying Nodal Loads**
        * **Positive (`+`):** Right $\rightarrow$ / Upward $\uparrow$
        * **Negative (`-`):** Left $\leftarrow$ / Downward $\downarrow$
        """)
    st.subheader("Nodal Loads")
    load_df = st.data_editor(st.session_state['loads_data'], num_rows="dynamic", key="loads", on_change=clear_results )
    
    if st.button("Calculate Results"):
        try:
            ts = TrussSystem()
            node_map = {}
            valid_node_count = 0
            
            # 1. Parse Nodes with Mapping
            for i, row in node_df.iterrows():
                if pd.isna(row.get('X')) or pd.isna(row.get('Y')): continue
                valid_node_count += 1
                rx = int(row.get('Restrain_X', 0)) if not pd.isna(row.get('Restrain_X')) else 0
                ry = int(row.get('Restrain_Y', 0)) if not pd.isna(row.get('Restrain_Y')) else 0
                
                n = Node(valid_node_count, float(row['X']), float(row['Y']), rx, ry)
                n.user_id = i + 1 
                ts.nodes.append(n)
                node_map[i + 1] = n 
                
            # 2. Parse Members via Mapping
            for i, row in member_df.iterrows():
                if pd.isna(row.get('Node_I')) or pd.isna(row.get('Node_J')): continue
                ni_val = int(row['Node_I'])
                nj_val = int(row['Node_J'])
                
                if ni_val not in node_map or nj_val not in node_map:
                    raise ValueError(f"Member M{i+1} references an empty or invalid Node ID.")
                    
                E = float(row.get('E (N/sq.m)', 2e11)) if not pd.isna(row.get('E (N/sq.m)')) else 2e11
                A = float(row.get('Area(sq.m)', 0.01)) if not pd.isna(row.get('Area(sq.m)')) else 0.01
                ts.members.append(Member(i+1, node_map[ni_val], node_map[nj_val], E, A))
                
            # 3. Parse Loads via Mapping
            for i, row in load_df.iterrows():
                if pd.isna(row.get('Node_ID')): continue
                node_id_val = int(row['Node_ID'])
                
                if node_id_val not in node_map:
                    raise ValueError(f"Load at row {i+1} references an empty or invalid Node ID.")
                    
                target_node = node_map[node_id_val]
                fx = float(row.get('Force_X (N)', 0)) if not pd.isna(row.get('Force_X (N)')) else 0.0
                fy = float(row.get('Force_Y (N)', 0)) if not pd.isna(row.get('Force_Y (N)')) else 0.0
                
                dof_x, dof_y = 2 * target_node.id - 2, 2 * target_node.id - 1
                
                ts.loads[dof_x] = ts.loads.get(dof_x, 0.0) + fx
                ts.loads[dof_y] = ts.loads.get(dof_y, 0.0) + fy
            
            if not ts.nodes or not ts.members:
                raise ValueError("Incomplete model: Please define at least two valid nodes and one valid member.")
                
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
                current_res_fig = st.session_state.get('current_fig', fig)
                current_base_fig = st.session_state.get('base_fig', None)
                
                report_file = generate_report(ts_solved, fig_base=current_base_fig, fig_res=current_res_fig, scale_factor=current_scale, unit_label=current_unit)
                
                if os.path.exists(report_file):
                    with open(report_file, "rb") as f:
                        st.session_state['report_data'] = f.read() 
                    os.remove(report_file) 
                else:
                    st.error("Report generation failed.")
                    
        if 'report_data' in st.session_state:
            st.download_button(
                label="📥 Download Word Report",
                data=st.session_state['report_data'],
                file_name=f"Mandal_Truss_Analysis_{datetime.date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

with col2:
    st.header("2. Model Visualization")
    tab1, tab2 = st.tabs(["🏗️ Undeformed Geometry", "📊 Structural Forces (Results)"])

    with tab1:
        if node_df.empty:
            st.info("👈 Start adding nodes in the Input Table (or click 'Load Benchmark Data') to build your geometry canvas.")
        else:
            fig_base, node_errors, member_errors, load_errors = draw_undeformed_geometry(node_df, member_df, load_df, scale_factor=current_scale, unit_label=current_unit)
            
            if node_errors: st.warning(f"⚠️ **Geometry Warning:** Invalid data at Node row(s): {', '.join(node_errors)}.")
            if member_errors: st.warning(f"⚠️ **Connectivity Warning:** Cannot draw {', '.join(member_errors)}.")
            if load_errors: st.warning(f"⚠️ **Loads Warning:** Invalid data at Loads table row(s): {', '.join(load_errors)}.")

            st.session_state['base_fig'] = fig_base 
            if not fig_base.data:
                st.info("📝 Add valid X and Y coordinates to the table to see your nodes appear here.")
            else:
                st.plotly_chart(fig_base, use_container_width=True)

    with tab2:
        if 'solved_truss' in st.session_state:
            ts = st.session_state['solved_truss']
            fig_res = draw_results_fbd(ts, scale_factor=current_scale, unit_label=current_unit)
            st.session_state['current_fig'] = fig_res 
            st.plotly_chart(fig_res, use_container_width=True)
        else:
            st.info("👈 Input loads and click 'Calculate Results' to view the force diagram.")

# ---------------------------------------------------------
# NEW SECTION: THE "GLASS BOX" PEDAGOGICAL EXPLORER
# ---------------------------------------------------------
if 'solved_truss' in st.session_state:
    st.markdown("---")
    st.header("🎓 Educational Glass-Box: Complete DSM Intermediate Steps")
    st.info("Explore the internal mathematics of the Direct Stiffness Method. This section exposes every variable, matrix, and vector calculated by the backend solver.")
    
    ts = st.session_state['solved_truss']
    
    gb_tab1, gb_tab2, gb_tab3 = st.tabs(["📐 1. Kinematics & Stiffness", "🧩 2. Global Assembly", "🚀 3. Displacements & Internal Forces"])
    
    # ------------------ TAB 1 ------------------
    with gb_tab1:
        st.subheader("Local Element Formulation")
        if ts.members: 
            mbr_opts = [f"Member {m.id}" for m in ts.members]
            sel_mbr = st.selectbox("Select Member to inspect kinematics and stiffness:", mbr_opts, key="gb_tab1")
            
            if sel_mbr and isinstance(sel_mbr, str) and " " in sel_mbr:
                selected_id = int(sel_mbr.split(" ")[1])
                m = next((m for m in ts.members if m.id == selected_id), None)
                
                if m and m.k_global_matrix is not None:
                    colA, colB = st.columns(2)
                    with colA:
                        st.markdown("**Member Kinematics (Trigonometry)**")
                        st.write(f"- **Length ($L$):** `{m.L:.4f} m`")
                        st.write(f"- **Dir. Cosine ($c = \\cos\\theta$):** `{m.c:.4f}`")
                        st.write(f"- **Dir. Sine ($s = \\sin\\theta$):** `{m.s:.4f}`")
                        
                        st.markdown("**Transformation Vector ($T$):**")
                        st.latex(r"T = \begin{bmatrix} -c & -s & c & s \end{bmatrix}")
                        st.dataframe(pd.DataFrame([m.T_vector], columns=["-c", "-s", "c", "s"]).style.format("{:.4f}"))
                    
                    with colB:
                        st.markdown("**Local Stiffness Matrix ($k_{global}$)**")
                        st.latex(r"k = \frac{EA}{L} \begin{bmatrix} c^2 & cs & -c^2 & -cs \\ cs & s^2 & -cs & -s^2 \\ -c^2 & -cs & c^2 & cs \\ -cs & -s^2 & cs & s^2 \end{bmatrix}")
                        df_k = pd.DataFrame(m.k_global_matrix)
                        st.dataframe(df_k.style.format("{:.2e}"))
                else:
                    st.error("Matrix not found.")
        else:
            st.warning("⚠️ No members found.")
            
    # ------------------ TAB 2 ------------------
    with gb_tab2:
        st.subheader("System Partitioning & Assembly")
        colC, colD = st.columns(2)
        
        with colC:
            st.markdown("**Degree of Freedom (DOF) Mapping**")
            st.write(f"- **Free DOFs ($f$):** `{ts.free_dofs}`")
            st.write(f"- **Restrained DOFs ($s$):** `{[i for i in range(2*len(ts.nodes)) if i not in ts.free_dofs]}`")
            
            st.markdown("**Active Load Vector ($F_f$)**")
            st.dataframe(pd.DataFrame(ts.F_reduced, columns=["Force"]).style.format("{:.2e}"))

        with colD:
            st.markdown("**Matrix Partitioning Theory:**")
            st.latex(r"\begin{bmatrix} F_f \\ F_s \end{bmatrix} = \begin{bmatrix} K_{ff} & K_{fs} \\ K_{sf} & K_{ss} \end{bmatrix} \begin{bmatrix} U_f \\ U_s \end{bmatrix}")
            
            with st.expander("View Full Unpartitioned Global Matrix ($K_{global}$)", expanded=True):
                st.dataframe(pd.DataFrame(ts.K_global).style.format("{:.2e}"))
                
            with st.expander("View Reduced Stiffness Matrix ($K_{ff}$)", expanded=False):
                st.dataframe(pd.DataFrame(ts.K_reduced).style.format("{:.2e}"))
                
    # ------------------ TAB 3 ------------------
    with gb_tab3:
        st.subheader("Solving the System & Extracting Forces")
        colE, colF = st.columns(2)
        
        with colE:
            st.markdown("**1. Global Displacement Vector ($U_{global}$)**")
            st.latex(r"U_f = K_{ff}^{-1} F_f \implies \text{Stitch with } U_s = 0")
            if hasattr(ts, 'U_global') and ts.U_global is not None:
                st.dataframe(pd.DataFrame(ts.U_global, columns=["Displacement (m)"]).style.format("{:.6e}"))
            else:
                st.info("Update core_solver.py to calculate U_global.")
                
        with colF:
            st.markdown("**2. Internal Force Extraction**")
            if ts.members:
                sel_mbr_force = st.selectbox("Select Member to view Force Extraction:", mbr_opts, key="gb_tab3")
                if sel_mbr_force and isinstance(sel_mbr_force, str) and " " in sel_mbr_force:
                    selected_id = int(sel_mbr_force.split(" ")[1])
                    m = next((m for m in ts.members if m.id == selected_id), None)
                    if m and hasattr(m, 'u_local') and m.u_local is not None:
                        st.latex(r"F_{axial} = \frac{EA}{L} \cdot (T \cdot u_{local})")
                        
                        st.markdown("**Local Displacements ($u_{local}$):**")
                        st.dataframe(pd.DataFrame([m.u_local], columns=["uix", "uiy", "ujx", "ujy"]).style.format("{:.6e}"))
                        
                        st.success(f"**Calculated Axial Force:** {m.internal_force:.2f} N")
                    else:
                        st.info("Calculate results first to view kinematics.")






