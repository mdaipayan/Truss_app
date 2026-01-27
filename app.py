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

    # Always plot the base model
    if not node_df.empty and not member_df.empty:
        for i, row in member_df.iterrows():
            try:
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                n1, n2 = node_df.iloc[ni], node_df.iloc[nj]
                fig.add_trace(go.Scatter(
                    x=[n1['X'], n2['X']], y=[n1['Y'], n2['Y']],
                    mode='lines+markers', line=dict(color='gray', width=1, dash='dot'),
                    name="Undeformed", showlegend=False
                ))
            except: pass

    # Overlay results if solved
    if 'solved_truss' in st.session_state:
        ts = st.session_state['solved_truss']
        
        for mbr in ts.members:
            f = mbr.calculate_force()
            nature = "Compressive" if f < 0 else "Tensile" # Standard Engineering Convention
            color = "red" if f < 0 else "blue"
            label = f"{round(abs(f)/1000, 2)} kN ({nature})"
            
            mid_x, mid_y = (mbr.node_i.x + mbr.node_j.x) / 2, (mbr.node_i.y + mbr.node_j.y) / 2
            dx, dy = mbr.node_j.x - mbr.node_i.x, mbr.node_j.y - mbr.node_i.y
            angle_deg = np.degrees(np.arctan2(dy, dx))
            
            if angle_deg > 90: angle_deg -= 180
            elif angle_deg < -90: angle_deg += 180

            fig.add_trace(go.Scatter(
                x=[mbr.node_i.x, mbr.node_j.x], y=[mbr.node_i.y, mbr.node_j.y],
                mode='lines+markers', line=dict(color=color, width=4), showlegend=False
            ))
            
            fig.add_annotation(
                x=mid_x, y=mid_y, text=label, showarrow=False,
                textangle=-angle_deg, yshift=12, font=dict(color=color, size=11)
            )

        for node in ts.nodes:
            if node.rx or node.ry:
                rx_kn, ry_kn = round(node.rx_val / 1000, 2), round(node.ry_val / 1000, 2)
                fig.add_annotation(
                    x=node.x, y=node.y, text=f"Rx: {rx_kn}kN, Ry: {ry_kn}kN",
                    showarrow=True, arrowhead=1, ax=0, ay=40,
                    font=dict(color="green", size=10), bgcolor="white"
                )
                fig.add_trace(go.Scatter(
                    x=[node.x], y=[node.y], mode='markers',
                    marker=dict(symbol='triangle-up', size=15, color='green'),
                    name=f"Support @ Node {node.id}"
                ))

    fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), showlegend=True)
    st.session_state['current_fig'] = fig
    st.plotly_chart(fig, use_container_width=True)
