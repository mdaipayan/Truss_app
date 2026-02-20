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

# ---------------------------------------------------------
# GLOBAL SETTINGS (SIDEBAR)
# ---------------------------------------------------------
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
        # FIX FOR CRITIQUE 2: Force the tables to refresh their widget state
        for key in ['nodes', 'members', 'loads']:
            if key in st.session_state:
                del st.session_state[key]

    if 'nodes_data' not in st.session_state:
        st.session_state['nodes_data'] = pd.DataFrame(columns=["X", "Y", "Restrain_X", "Restrain_Y"])
        st.session_state['members_data'] = pd.DataFrame(columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"])
        st.session_state['loads_data'] = pd.DataFrame(columns=["Node_ID", "Force_X (N)", "Force_Y (N)"])

    st.subheader("Nodes")
    node_df = st.data_editor(st.session_state['nodes_data'], num_rows="dynamic", key="nodes", on_change=clear_results)

    st.subheader("Members")
    member_df = st.data_editor(st.session_state['members_data'], num_rows="dynamic", key="members", on_change=clear_results)

    st.subheader("Nodal Loads")
    load_df = st.data_editor(st.session_state['loads_data'], num_rows="dynamic", key="loads", on_change=clear_results)
    
    if st.button("Calculate Results"):
        try:
            ts = TrussSystem()
            
            # FIX FOR CRITIQUE 1: Safely parse tables, ignoring empty rows
            for i, row in node_df.iterrows():
                if pd.isna(row.get('X')) or pd.isna(row.get('Y')): continue
                rx = int(row.get('Restrain_X', 0)) if not pd.isna(row.get('Restrain_X')) else 0
                ry = int(row.get('Restrain_Y', 0)) if not pd.isna(row.get('Restrain_Y')) else 0
                ts.nodes.append(Node(i+1, float(row['X']), float(row['Y']), rx, ry))
                
            for i, row in member_df.iterrows():
                if pd.isna(row.get('Node_I')) or pd.isna(row.get('Node_J')): continue
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                if ni < 0 or nj < 0 or ni >= len(ts.nodes) or nj >= len(ts.nodes):
                    raise IndexError(f"Member at row {i+1} connects to an invalid Node ID.")
                E = float(row.get('E (N/sq.m)', 2e11)) if not pd.isna(row.get('E (N/sq.m)')) else 2e11
                A = float(row.get('Area(sq.m)', 0.01)) if not pd.isna(row.get('Area(sq.m)')) else 0.01
                ts.members.append(Member(i+1, ts.nodes[ni], ts.nodes[nj], E, A))
                
            for i, row in load_df.iterrows():
                if pd.isna(row.get('Node_ID')): continue
                node_id = int(row['Node_ID'])
                if node_id < 1 or node_id > len(ts.nodes):
                    raise IndexError(f"Load applied to invalid Node ID: {node_id}.")
                fx = float(row.get('Force_X (N)', 0)) if not pd.isna(row.get('Force_X (N)')) else 0.0
                fy = float(row.get('Force_Y (N)', 0)) if not pd.isna(row.get('Force_Y (N)')) else 0.0
                ts.loads[2*node_id-2] = fx
                ts.loads[2*node_id-1] = fy
            
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
                generate_report(ts_solved, fig_base=current_base_fig, fig_res=current_res_fig, scale_factor=current_scale, unit_label=current_unit)
                
                if os.path.exists("Analysis_Report.docx"):
                    with open("Analysis_Report.docx", "rb") as f:
                        st.download_button(
                            label="📥 Download Word Report", data=f,
                            file_name=f"Mandal_Truss_Analysis_{datetime.date.today()}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                else:
                    st.error("Report generation failed.")

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
            
            # FIX FOR CRITIQUE 3: Verify Plotly actually drew geometric data
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

if 'solved_truss' in st.session_state:
    st.markdown("---")
    st.header("🎓 Educational Glass-Box: Intermediate Matrix Steps")
    ts = st.session_state['solved_truss']
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.subheader("1. Element Stiffness Matrices ($k$)")
        st.latex(r"k = \frac{EA}{L} \begin{bmatrix} c^2 & cs & -c^2 & -cs \\ cs & s^2 & -cs & -s^2 \\ -c^2 & -cs & c^2 & cs \\ -cs & -s^2 & cs & s^2 \end{bmatrix}")
        
        if ts.members: 
            mbr_opts = [f"Member {m.id}" for m in ts.members]
            sel_mbr = st.selectbox("Select Member to view its calculated 4x4 matrix:", mbr_opts)
            
            # THE FIX FOR SCREENSHOT 1: Strict string parsing 
            if sel_mbr and isinstance(sel_mbr, str) and " " in sel_mbr:
                idx = int(sel_mbr.split(" ")[1]) - 1
                if ts.members[idx].k_global_matrix is not None:
                    df_k = pd.DataFrame(ts.members[idx].k_global_matrix)
                    st.dataframe(df_k.style.format("{:.2e}"))
                else:
                    st.error("Matrix not found.")
        else:
            st.warning("⚠️ No members found.")
        
    with g_col2:
        st.subheader("2. Global Assembly & Partitioning")
        st.latex(r"\begin{bmatrix} F_f \\ F_s \end{bmatrix} = \begin{bmatrix} K_{ff} & K_{fs} \\ K_{sf} & K_{ss} \end{bmatrix} \begin{bmatrix} U_f \\ U_s \end{bmatrix}")
        
        with st.expander("View Full Unpartitioned Global Matrix ($K_{global}$)"):
            st.dataframe(pd.DataFrame(ts.K_global).style.format("{:.2e}"))
            
        with st.expander("View Reduced System ($K_{ff} \cdot U_f = F_f$)"):
            st.latex(r"F_f = K_{ff} U_f \implies U_f = K_{ff}^{-1} F_f")
            st.write("**Reduced Stiffness Matrix ($K_{ff}$):**")
            st.dataframe(pd.DataFrame(ts.K_reduced).style.format("{:.2e}"))
            st.write("**Active Force Vector ($F_f$):**")
            st.write(ts.F_reduced)
            
