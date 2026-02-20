import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from core_solver import TrussSystem, Node, Member
import datetime
import os

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
    
    st.subheader("Members")
    member_df = st.data_editor(st.session_state['members_data'], num_rows="dynamic", key="members")
    
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
    
    # Create two separate tabs for better pedagogical clarity
    tab1, tab2 = st.tabs(["🏗️ Undeformed Geometry", "📊 Structural Forces (Results)"])

   # ---------------------------------------------------------
    # TAB 1: BASE MODEL (Geometry, Node IDs, Member IDs, Loads & Supports)
    # ---------------------------------------------------------
    with tab1:
        fig_base = go.Figure()
        
        # 1. Plot Supports dynamically (Drawn first so they sit under the nodes)
        if not node_df.empty:
            for i, row in node_df.iterrows():
                try:
                    rx = int(row.get('Restrain_X', 0))
                    ry = int(row.get('Restrain_Y', 0))
                    nx, ny = float(row['X']), float(row['Y'])
                    
                    if rx == 1 and ry == 1:
                        # PIN SUPPORT (Both X and Y Restrained)
                        fig_base.add_trace(go.Scatter(
                            x=[nx], y=[ny], mode='markers',
                            marker=dict(symbol='triangle-up', size=20, color='forestgreen'),
                            showlegend=False, hoverinfo='skip'
                        ))
                        fig_base.add_annotation(
                            x=nx, y=ny, text="<b>Pin</b>", showarrow=False, yshift=-25,
                            font=dict(color="forestgreen", size=11)
                        )
                    elif rx == 0 and ry == 1:
                        # ROLLER SUPPORT (Y Restrained, X Free)
                        fig_base.add_trace(go.Scatter(
                            x=[nx], y=[ny], mode='markers',
                            marker=dict(symbol='circle-open', size=18, color='forestgreen', line=dict(width=4)),
                            showlegend=False, hoverinfo='skip'
                        ))
                        fig_base.add_annotation(
                            x=nx, y=ny, text="<b>Roller</b>", showarrow=False, yshift=-25,
                            font=dict(color="forestgreen", size=11)
                        )
                    elif rx == 1 and ry == 0:
                        # ROLLER SUPPORT Vertical (X Restrained, Y Free)
                        fig_base.add_trace(go.Scatter(
                            x=[nx], y=[ny], mode='markers',
                            marker=dict(symbol='square-open', size=18, color='forestgreen', line=dict(width=4)),
                            showlegend=False, hoverinfo='skip'
                        ))
                        fig_base.add_annotation(
                            x=nx, y=ny, text="<b>Roller (X-fixed)</b>", showarrow=False, xshift=-35,
                            font=dict(color="forestgreen", size=11)
                        )
                except: pass

        # 2. Plot Members and Member IDs dynamically
        if not node_df.empty and not member_df.empty:
            for i, row in member_df.iterrows():
                try:
                    ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                    n1, n2 = node_df.iloc[ni], node_df.iloc[nj]
                    x0, y0, x1, y1 = float(n1['X']), float(n1['Y']), float(n2['X']), float(n2['Y'])
                    
                    # Draw dashed line for the member
                    fig_base.add_trace(go.Scatter(
                        x=[x0, x1], y=[y0, y1], 
                        mode='lines', 
                        line=dict(color='gray', width=2, dash='dash'), 
                        showlegend=False
                    ))
                    
                    # Add Member Label in the middle
                    fig_base.add_annotation(
                        x=(x0+x1)/2, y=(y0+y1)/2, 
                        text=f"<b>M{i+1}</b>",
                        showarrow=False,
                        font=dict(color="blue", size=11),
                        bgcolor="rgba(255, 255, 255, 0.8)", 
                        bordercolor="blue", borderwidth=1
                    )
                except: pass
                
        # 3. Plot Nodes and Node Labels (Drawn on top of supports)
        if not node_df.empty:
            for i, row in node_df.iterrows():
                try:
                    nx, ny = float(row['X']), float(row['Y'])
                    fig_base.add_trace(go.Scatter(
                        x=[nx], y=[ny], 
                        mode='markers+text',
                        text=[f"<b>Node {i+1}</b>"], 
                        textposition="top center",
                        marker=dict(color='black', size=10), 
                        showlegend=False
                    ))
                except: pass
        
        # 4. Plot Load Arrows dynamically
        if not node_df.empty and not load_df.empty:
            for i, row in load_df.iterrows():
                try:
                    node_idx = int(row['Node_ID']) - 1
                    nx, ny = float(node_df.iloc[node_idx]['X']), float(node_df.iloc[node_idx]['Y'])
                    
                    # Handle Y-Direction Forces (Vertical)
                    fy = float(row.get('Force_Y (N)', 0))
                    if abs(fy) > 0:
                        ay_val = -50 if fy > 0 else 50
                        fig_base.add_annotation(
                            x=nx, y=ny,
                            ax=0, ay=ay_val, xref="x", yref="y", axref="pixel", ayref="pixel",
                            text=f"<b>{abs(fy)/1000} kN</b>",
                            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2.5, arrowcolor="darkorange",
                            font=dict(color="darkorange", size=11), bgcolor="white"
                        )
                        
                    # Handle X-Direction Forces (Horizontal)
                    fx = float(row.get('Force_X (N)', 0))
                    if abs(fx) > 0:
                        ax_val = -50 if fx > 0 else 50
                        fig_base.add_annotation(
                            x=nx, y=ny,
                            ax=ax_val, ay=0, xref="x", yref="y", axref="pixel", ayref="pixel",
                            text=f"<b>{abs(fx)/1000} kN</b>",
                            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2.5, arrowcolor="darkorange",
                            font=dict(color="darkorange", size=11), bgcolor="white"
                        )
                except: pass

        fig_base.update_layout(
            yaxis=dict(scaleanchor="x", scaleratio=1), 
            margin=dict(l=0, r=0, t=30, b=0),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig_base, use_container_width=True)
    # ---------------------------------------------------------
    # TAB 2: RESULTS (Thick 3D-Style Lines, Vibrant Colors)
    # ---------------------------------------------------------
    with tab2:
        if 'solved_truss' in st.session_state:
            fig_res = go.Figure()
            ts = st.session_state['solved_truss']
            
            # Plot Members with Forces
            for mbr in ts.members:
                f = mbr.calculate_force()
                val_kn = round(abs(f)/1000, 2)
                
                # Setup Colors and Nature
                if val_kn < 0.01:
                    nature = "Zero-Force"
                    color = "darkgray"
                else:
                    nature = "Compressive" if f < 0 else "Tensile"
                    color = "crimson" if f < 0 else "royalblue"
                
                x0, y0, x1, y1 = mbr.node_i.x, mbr.node_i.y, mbr.node_j.x, mbr.node_j.y
                mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
                
                # Calculate angle for text alignment
                dx, dy = x1 - x0, y1 - y0
                angle_deg = np.degrees(np.arctan2(dy, dx))
                if angle_deg > 90: angle_deg -= 180
                elif angle_deg < -90: angle_deg += 180
                
                # Draw thick member (Gives a 3D structural tube effect)
                fig_res.add_trace(go.Scatter(
                    x=[x0, x1], y=[y0, y1], 
                    mode='lines',
                    line=dict(color=color, width=8), 
                    showlegend=False
                ))
                
                # Add High-Visibility Force Label
                if val_kn >= 0.01: 
                    label_html = f"<b>{val_kn} kN</b><br><i>{nature}</i>"
                    fig_res.add_annotation(
                        x=mid_x, y=mid_y, text=label_html, showarrow=False,
                        textangle=-angle_deg, yshift=25, 
                        font=dict(color=color, size=12),
                        bgcolor="rgba(255,255,255,0.9)", 
                        bordercolor=color, borderwidth=2, borderpad=3
                    )
                else:
                    fig_res.add_annotation(
                        x=mid_x, y=mid_y, text="0.0 kN", showarrow=False,
                        font=dict(color="gray", size=10), bgcolor="white"
                    )

            # Draw Nodes and Support Reactions
            for node in ts.nodes:
                # Add stylish node joints
                fig_res.add_trace(go.Scatter(
                    x=[node.x], y=[node.y], mode='markers',
                    marker=dict(color='black', size=12, line=dict(color='white', width=2)), 
                    showlegend=False
                ))
                
                # Add Reaction Arrows
                if node.rx or node.ry:
                    rx_kn, ry_kn = round(node.rx_val/1000, 1), round(node.ry_val/1000, 1)
                    fig_res.add_annotation(
                        x=node.x, y=node.y, 
                        text=f"<b>R:</b> {rx_kn}kN, {ry_kn}kN",
                        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=3, 
                        arrowcolor="darkgreen", ax=0, ay=50, 
                        font=dict(color="white", size=11), bgcolor="darkgreen"
                    )

            fig_res.update_layout(
                yaxis=dict(scaleanchor="x", scaleratio=1), 
                plot_bgcolor='rgb(240, 242, 246)', # Soft gray background makes colors pop
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.session_state['current_fig'] = fig_res # Save the beautiful chart for the word report
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
        # Add the 'r' before the string so Python reads the LaTeX correctly
        st.markdown(r"Where $c = \cos(\theta) = \frac{\Delta x}{L}$ and $s = \sin(\theta) = \frac{\Delta y}{L}$.")
        
        # Display the numerical output
        mbr_opts = [f"Member {m.id}" for m in ts.members]
        sel_mbr = st.selectbox("Select Member to view its calculated 4x4 matrix:", mbr_opts)
        idx = int(sel_mbr.split(" ")[1]) - 1
        df_k = pd.DataFrame(ts.members[idx].k_global_matrix)
        st.dataframe(df_k.style.format("{:.2e}"))
        
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











