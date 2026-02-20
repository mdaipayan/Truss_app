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

    # FIX FOR REVIEWER 2: Always plot the base model AND Node Labels before solving
    if not node_df.empty:
        # Plot Node Labels Immediately
        for i, row in node_df.iterrows():
            try:
                fig.add_annotation(
                    x=float(row['X']), y=float(row['Y']),
                    text=f"<b>Node {i+1}</b>",
                    showarrow=False, yshift=15,
                    font=dict(color="black", size=12),
                    bgcolor="lightgray", bordercolor="black", borderwidth=1
                )
                fig.add_trace(go.Scatter(
                    x=[float(row['X'])], y=[float(row['Y'])], mode='markers',
                    marker=dict(color='black', size=8), showlegend=False
                ))
            except: pass

    if not node_df.empty and not member_df.empty:
        for i, row in member_df.iterrows():
            try:
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                n1, n2 = node_df.iloc[ni], node_df.iloc[nj]
                fig.add_trace(go.Scatter(
                    x=[n1['X'], n2['X']], y=[n1['Y'], n2['Y']],
                    mode='lines', line=dict(color='gray', width=1, dash='dot'),
                    showlegend=False
                ))
            except: pass

    # ... (Keep your existing 'if solved_truss in st.session_state:' plotting logic here) ...
    # [Your existing Plotly result rendering goes here]
    
    fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), showlegend=False)
    st.session_state['current_fig'] = fig
    st.plotly_chart(fig, use_container_width=True)

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





