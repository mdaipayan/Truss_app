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
    
    st.subheader("Nodes")
    node_df = st.data_editor(
        pd.DataFrame(columns=["X", "Y", "Restrain_X", "Restrain_Y"]), 
        num_rows="dynamic", 
        key="nodes"
    )
    
    st.subheader("Members")
    member_df = st.data_editor(
        pd.DataFrame(columns=["Node_I", "Node_J", "Area(sq.m)", "E (N/sq.m)"]), 
        num_rows="dynamic", 
        key="members"
    )
    
    st.subheader("Nodal Loads")
    load_df = st.data_editor(
        pd.DataFrame(columns=["Node_ID", "Force_X (N)", "Force_Y (N)"]), 
        num_rows="dynamic", 
        key="loads"
    )
    
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
    # TAB 1: BASE MODEL (Geometry, Node IDs, Member IDs)
    # ---------------------------------------------------------
    with tab1:
        fig_base = go.Figure()
        
        # Plot Nodes and Node Labels
        if not node_df.empty:
            for i, row in node_df.iterrows():
                try:
                    fig_base.add_trace(go.Scatter(
                        x=[float(row['X'])], y=[float(row['Y'])], 
                        mode='markers+text',
                        text=[f"<b>Node {i+1}</b>"], 
                        textposition="top center",
                        marker=dict(color='black', size=10), 
                        showlegend=False
                    ))
                except: pass

        # Plot Members and Member IDs
        if not node_df.empty and not member_df.empty:
            for i, row in member_df.iterrows():
                try:
                    ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                    n1, n2 = node_df.iloc[ni], node_df.iloc[nj]
                    x0, y0, x1, y1 = n1['X'], n1['Y'], n2['X'], n2['Y']
                    
                    # Draw dashed line
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
                        bgcolor="white", bordercolor="gray", borderwidth=1
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
        st.markdown("The $2n \times 2n$ global stiffness matrix is partitioned into free ($f$) and restrained ($s$) degrees of freedom[cite: 90].")
        
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






