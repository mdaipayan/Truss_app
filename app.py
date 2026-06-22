import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from core_solver import TrussSystem, Node, Member
import datetime
import os
from feedback_store import FEEDBACK_FILE, save_feedback
from visualizer import draw_undeformed_geometry, draw_results_fbd
import visitor_log

st.set_page_config(page_title="2D Truss Suite", layout="wide")

# Record this visit once per browser session (anonymous; safe no-op if the
# Google Sheet credentials are not configured).
visitor_log.log_visit()

st.title("🏗️ 2D Truss Analysis Developed by D Mandal")


def fmt(df, pattern):
    """Display a numeric DataFrame with a format pattern.

    Uses the pandas Styler when jinja2 is available (nicer alignment); falls
    back to plain string formatting otherwise so the app never crashes on a
    missing optional dependency.
    """
    try:
        return df.style.format(pattern)
    except (AttributeError, ImportError, ModuleNotFoundError):
        def _f(v):
            try:
                return pattern.format(v)
            except (ValueError, TypeError):
                return v
        # .map is the modern element-wise API (pandas >= 2.1); fall back to
        # .applymap on older versions.
        elementwise = getattr(df, "map", None) or df.applymap
        return elementwise(_f)

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

# --- Private admin panel: visitor statistics (password protected) ----------
with st.sidebar.expander("🔐 Admin"):
    _admin_pw = st.text_input("Admin password", type="password", key="admin_pw")
    if _admin_pw:
        if _admin_pw == visitor_log._secret_get("admin_password"):
            _records = visitor_log.get_visit_records()
            if _records is None:
                st.warning("Visitor logging is not configured yet. See VISITOR_TRACKING_SETUP.md.")
            elif len(_records) == 0:
                st.info("No visits recorded yet.")
            else:
                _vdf = pd.DataFrame(_records)
                _c1, _c2 = st.columns(2)
                _c1.metric("Total visits", len(_vdf))
                if "session_id" in _vdf.columns:
                    _c2.metric("Unique sessions", _vdf["session_id"].nunique())
                st.dataframe(_vdf, use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download visitor log (CSV)",
                    data=_vdf.to_csv(index=False),
                    file_name="visitor_log.csv",
                    mime="text/csv",
                )
        else:
            st.error("Incorrect password.")

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
        
        # Benchmark load case (reproduces Table 2 of Mandal, 2026, CAEE):
        #   Node 5: 300 kN downward (Fy = -300000 N)  |  Node 4: 10 kN horizontal (Fx = +10000 N)
        st.session_state['loads_data'] = pd.DataFrame([
            [5, 0.0, -300000.0], [4, 10000.0, 0.0]    
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
        include_report_calculations = st.checkbox(
            "Include full DSM formulas and matrix calculations",
            value=False,
            help="Adds local stiffness matrices, transformation transpose matrices, global stiffness matrices, and displacement calculations to the PDF report.",
        )
        
        if st.button("🚀 Prepare Professional Report"):
            with st.spinner("Generating Professional Report..."):
                current_res_fig = st.session_state.get('current_fig', fig)
                current_base_fig = st.session_state.get('base_fig', None)
                
                report_file = generate_report(
                    ts_solved,
                    fig_base=current_base_fig,
                    fig_res=current_res_fig,
                    scale_factor=current_scale,
                    unit_label=current_unit,
                    include_calculations=include_report_calculations,
                )
                
                if os.path.exists(report_file):
                    with open(report_file, "rb") as f:
                        st.session_state['report_data'] = f.read() 
                    os.remove(report_file) 
                else:
                    st.error("Report generation failed.")
                    
        if 'report_data' in st.session_state:
            st.download_button(
                label="📥 Download PDF Report",
                data=st.session_state['report_data'],
                file_name=f"Mandal_Truss_Analysis_{datetime.date.today()}.pdf",
                mime="application/pdf"
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
# RESULTS SUMMARY & EQUILIBRIUM CHECK (student-facing)
# ---------------------------------------------------------
if 'solved_truss' in st.session_state:
    ts = st.session_state['solved_truss']
    st.markdown("---")
    st.header("📋 Results Summary")

    # --- Global equilibrium check: applied loads + reactions should sum to ~0 ---
    applied_fx = sum(v for d, v in ts.loads.items() if d % 2 == 0)
    applied_fy = sum(v for d, v in ts.loads.items() if d % 2 == 1)
    react_fx = sum(n.rx_val for n in ts.nodes)
    react_fy = sum(n.ry_val for n in ts.nodes)
    res_x = applied_fx + react_fx
    res_y = applied_fy + react_fy
    ref = max(abs(applied_fx), abs(applied_fy), abs(react_fx), abs(react_fy), 1.0)
    ok_eq = abs(res_x) < 1e-6 * ref + 1e-9 and abs(res_y) < 1e-6 * ref + 1e-9

    st.caption("Static equilibrium verification — the sum of all applied loads and support reactions must be zero.")
    e1, e2, e3 = st.columns(3)
    e1.metric(f"Σ Fx residual ({current_unit})", f"{res_x / current_scale:.3e}")
    e2.metric(f"Σ Fy residual ({current_unit})", f"{res_y / current_scale:.3e}")
    with e3:
        if ok_eq:
            st.success("✓ Equilibrium satisfied (Σ F ≈ 0)")
        else:
            st.warning("⚠️ Non-zero residual — recheck the model.")

    r_tab1, r_tab2, r_tab3 = st.tabs(["🔧 Member Forces", "📍 Nodal Displacements", "🟢 Support Reactions"])

    with r_tab1:
        _forces = [m.internal_force for m in ts.members]
        _maxf = max((abs(v) for v in _forces), default=0.0)
        _tol = max(1e-6, 1e-4 * _maxf)
        _mrows = []
        for m in ts.members:
            f = m.internal_force
            nature = "Zero-Force" if abs(f) < _tol else ("Compression" if f < 0 else "Tension")
            _mrows.append({
                "Member": f"M{m.id}",
                "Connectivity": f"{m.node_i.id} → {m.node_j.id}",
                "Length (m)": round(m.L, 4),
                f"Axial Force ({current_unit})": round(f / current_scale, 4),
                "Nature": nature,
            })
        st.dataframe(pd.DataFrame(_mrows), use_container_width=True, hide_index=True)
        st.caption("Sign convention: positive = Tension, negative = Compression.")

    with r_tab2:
        _drows = [{"Node": n.id, "Ux (m)": f"{n.ux:.6e}", "Uy (m)": f"{n.uy:.6e}"} for n in ts.nodes]
        st.dataframe(pd.DataFrame(_drows), use_container_width=True, hide_index=True)

    with r_tab3:
        _rrows = []
        for n in ts.nodes:
            if n.rx or n.ry:
                _rrows.append({
                    "Node": n.id,
                    f"Rx ({current_unit})": round(n.rx_val / current_scale, 4) if n.rx else "—",
                    f"Ry ({current_unit})": round(n.ry_val / current_scale, 4) if n.ry else "—",
                })
        if _rrows:
            st.dataframe(pd.DataFrame(_rrows), use_container_width=True, hide_index=True)
        else:
            st.info("No support reactions (no restrained nodes defined).")

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
        st.subheader("From Local to Global Element Stiffness")
        st.caption("The element stiffness is first written in the member's own (local) axis, then rotated into global X–Y coordinates via the transformation matrix.")
        if ts.members:
            mbr_opts = [f"Member {m.id}" for m in ts.members]
            sel_mbr = st.selectbox("Select Member to inspect kinematics and stiffness:", mbr_opts, key="gb_tab1")

            if sel_mbr and isinstance(sel_mbr, str) and " " in sel_mbr:
                selected_id = int(sel_mbr.split(" ")[1])
                m = next((m for m in ts.members if m.id == selected_id), None)

                if m and m.k_global_matrix is not None:
                    c, s, L = m.c, m.s, m.L
                    ea_l = m.E * m.A / L

                    # Step 1 — Kinematics
                    st.markdown("##### Step 1 · Member Kinematics (Trigonometry)")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Length L (m)", f"{L:.4f}")
                    k2.metric("c = cos θ", f"{c:.4f}")
                    k3.metric("s = sin θ", f"{s:.4f}")
                    k4.metric("EA/L (N/m)", f"{ea_l:.3e}")

                    st.markdown("---")
                    colA, colB = st.columns(2)

                    # Step 2 — Local stiffness matrix (element axis: axial only)
                    with colA:
                        st.markdown("##### Step 2 · Local Stiffness Matrix $k_{local}$")
                        st.caption("In the member's own axis the bar carries axial force only (2 DOF).")
                        st.latex(r"k_{local} = \frac{EA}{L} \begin{bmatrix} 1 & -1 \\ -1 & 1 \end{bmatrix}")
                        k_local = (ea_l) * np.array([[1.0, -1.0], [-1.0, 1.0]])
                        st.dataframe(fmt(pd.DataFrame(k_local, index=["i", "j"], columns=["i", "j"]), "{:.2e}"))

                        st.markdown("##### Step 3 · Transformation Matrix $T$")
                        st.caption("Maps the 2 local axial DOF to the 4 global (x, y) DOF.")
                        st.latex(r"T = \begin{bmatrix} c & s & 0 & 0 \\ 0 & 0 & c & s \end{bmatrix}")
                        T_mat = np.array([[c, s, 0.0, 0.0], [0.0, 0.0, c, s]])
                        st.dataframe(fmt(pd.DataFrame(T_mat, index=["i", "j"], columns=["uix", "uiy", "ujx", "ujy"]), "{:.4f}"))

                    # Step 4 — Global element stiffness via congruence transform
                    with colB:
                        st.markdown("##### Step 4 · Global Stiffness Matrix $k_{global}$")
                        st.caption("Rotate the local matrix into global axes.")
                        st.latex(r"k_{global} = T^{\mathsf{T}}\, k_{local}\, T = \frac{EA}{L}\begin{bmatrix} c^2 & cs & -c^2 & -cs \\ cs & s^2 & -cs & -s^2 \\ -c^2 & -cs & c^2 & cs \\ -cs & -s^2 & cs & s^2 \end{bmatrix}")
                        k_from_T = T_mat.T @ k_local @ T_mat
                        df_k = pd.DataFrame(k_from_T, index=["uix", "uiy", "ujx", "ujy"], columns=["uix", "uiy", "ujx", "ujy"])
                        st.dataframe(fmt(df_k, "{:.2e}"))
                        # Confirm this matches what the solver actually assembled.
                        if np.allclose(k_from_T, m.k_global_matrix):
                            st.success("✓ Matches the matrix the solver assembled into $K_{global}$.")
                        else:
                            st.warning("Mismatch with solver matrix — check inputs.")

                    st.info("Note: the **force-recovery vector** $T_f = [-c,\\ -s,\\ c,\\ s]$ used later to extract axial force (Tab 3) is related but distinct from the transformation matrix $T$ above.")
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
            st.caption("Each global DOF belongs to one node and one direction. Indices are 0-based: DOF 0 = Node 1 (x), DOF 1 = Node 1 (y), and so on.")
            _free_set = set(ts.free_dofs)
            _dofrows = [{
                "DOF": d,
                "Node": d // 2 + 1,
                "Direction": "x (horizontal)" if d % 2 == 0 else "y (vertical)",
                "Status": "Free" if d in _free_set else "Restrained",
            } for d in range(2 * len(ts.nodes))]
            st.dataframe(pd.DataFrame(_dofrows), use_container_width=True, hide_index=True)

            st.markdown("**Active Load Vector ($F_f$)** — applied forces at the free DOFs")
            _ffrows = [{
                "DOF": d,
                "Node": d // 2 + 1,
                "Direction": "x" if d % 2 == 0 else "y",
                f"Force ({current_unit})": round(float(ts.F_reduced[i]) / current_scale, 4),
            } for i, d in enumerate(ts.free_dofs)]
            st.dataframe(pd.DataFrame(_ffrows), use_container_width=True, hide_index=True)

        with colD:
            st.markdown("**Matrix Partitioning Theory:**")
            st.latex(r"\begin{bmatrix} F_f \\ F_s \end{bmatrix} = \begin{bmatrix} K_{ff} & K_{fs} \\ K_{sf} & K_{ss} \end{bmatrix} \begin{bmatrix} U_f \\ U_s \end{bmatrix}")
            
            with st.expander("View Full Unpartitioned Global Matrix ($K_{global}$)", expanded=True):
                st.dataframe(fmt(pd.DataFrame(ts.K_global), "{:.2e}"))
                
            with st.expander("View Reduced Stiffness Matrix ($K_{ff}$)", expanded=False):
                st.dataframe(fmt(pd.DataFrame(ts.K_reduced), "{:.2e}"))
                
    # ------------------ TAB 3 ------------------
    with gb_tab3:
        st.subheader("Solving the System & Extracting Forces")
        colE, colF = st.columns(2)
        
        with colE:
            st.markdown("**1. Global Displacement Vector ($U_{global}$)**")
            st.latex(r"U_f = K_{ff}^{-1} F_f \implies \text{Stitch with } U_s = 0")
            if hasattr(ts, 'U_global') and ts.U_global is not None:
                st.dataframe(fmt(pd.DataFrame(ts.U_global, columns=["Displacement (m)"]), "{:.6e}"))
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
                        st.dataframe(fmt(pd.DataFrame([m.u_local], columns=["uix", "uiy", "ujx", "ujy"]), "{:.6e}"))
                        
                        st.success(f"**Calculated Axial Force:** {m.internal_force:.2f} N")
                    else:
                        st.info("Calculate results first to view kinematics.")

st.markdown("---")
st.header("💬 User Feedback")
st.caption("Share a quick note to help improve the Professional Truss Suite. Feedback is saved to the server-side feedback.csv file next to the app.")

with st.form("user_feedback_form", clear_on_submit=True):
    feedback_rating = st.slider("Overall rating", min_value=1, max_value=5, value=5)
    feedback_category = st.selectbox(
        "Feedback category",
        ["General", "Bug report", "Report quality", "Feature request", "Usability"],
    )
    feedback_comments = st.text_area("Comments", placeholder="Write your feedback here...")
    feedback_submitted = st.form_submit_button("Submit Feedback")

if feedback_submitted:
    if feedback_comments.strip():
        try:
            saved_feedback_path = save_feedback(feedback_rating, feedback_category, feedback_comments)
            st.success(f"Thank you! Your feedback has been saved to {saved_feedback_path.name}.")
            st.caption(f"Server path: {saved_feedback_path}")
        except OSError as e:
            st.error(f"Unable to save feedback: {e}")
    else:
        st.warning("Please enter a short comment before submitting feedback.")

if FEEDBACK_FILE.exists():
    with FEEDBACK_FILE.open("rb") as feedback_csv:
        st.download_button(
            label="Download feedback CSV",
            data=feedback_csv,
            file_name="feedback.csv",
            mime="text/csv",
        )
