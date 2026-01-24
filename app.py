import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from core_solver import TrussSystem, Node, Member

st.set_page_config(page_title="Professional Truss Suite", layout="wide")
st.title("🏗️ Professional Truss Analysis Developed by D Mandal")
fig = go.Figure()
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Input Data")
    
    st.subheader("Nodes")
    # Initializing with numeric types helps Streamlit infer the correct column type
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
            if 'solved_truss' in st.session_state:
                st.subheader("3. Export Results")
                from report_gen import generate_report
            import io
   
    # Export Results
    if 'solved_truss' in st.session_state:
        st.header("3. Export Results")
        from report_gen import generate_report
        
        ts_solved = st.session_state['solved_truss']
        
        if st.button("🚀 Prepare Professional Report"):
            with st.spinner("Generating Professional Report..."):
            # Define filename
                image_file = "truss_plot.png"
            
            # 1. Use the figure from session state (it's the most reliable)
            if 'current_fig' in st.session_state:
                st.session_state['current_fig'].write_image(image_file)
            else:
                # Fallback to the local fig variable if session state isn't used
                fig.write_image(image_file) 
            
            # 2. Generate the word document once
            generate_report(ts_solved, image_path=image_file)
            
            # 3. Provide the download button
            with open("Analysis_Report.docx", "rb") as f:
                st.download_button(
                    label="📥 Download Word Report",
                    data=f,
                    file_name="D_Mandal_Truss_Analysis.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
 
with col2:
    st.header("2. Model Visualization")
    

    # Always plot the base model if nodes/members exist
    if not node_df.empty and not member_df.empty:
        for i, row in member_df.iterrows():
            try:
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                n1 = node_df.iloc[ni]
                n2 = node_df.iloc[nj]
                fig.add_trace(go.Scatter(
                    x=[n1['X'], n2['X']], y=[n1['Y'], n2['Y']],
                    mode='lines+markers', line=dict(color='gray', width=1, dash='dot'),
                    name="Undeformed"
                ))
            except: pass

   # Overlay results if solved
    if 'solved_truss' in st.session_state:
        ts = st.session_state['solved_truss']
        
        # 1. Plot Members with Forces
        for mbr in ts.members:
            f = mbr.calculate_force()  # Logic from core_solver
            
            # Nature: Positive is Compressive, Negative is Tensile
            nature = "Compressive" if f > 0 else "Tensile"
            color = "red" if f > 0 else "blue"
            label = f"{round(abs(f)/1000, 2)} kN ({nature})"
            
            # Midpoint and Angle for parallel alignment
            mid_x = (mbr.node_i.x + mbr.node_j.x) / 2
            mid_y = (mbr.node_i.y + mbr.node_j.y) / 2
            dx = mbr.node_j.x - mbr.node_i.x
            dy = mbr.node_j.y - mbr.node_i.y
            angle_deg = np.degrees(np.arctan2(dy, dx))
            
            # Keep text upright
            if angle_deg > 90: angle_deg -= 180
            elif angle_deg < -90: angle_deg += 180

            fig.add_trace(go.Scatter(
                x=[mbr.node_i.x, mbr.node_j.x],
                y=[mbr.node_i.y, mbr.node_j.y],
                mode='lines+markers',
                line=dict(color=color, width=4),
                showlegend=False
            ))
            
            fig.add_annotation(
                x=mid_x, y=mid_y,
                text=label,
                showarrow=False,
                textangle=-angle_deg,
                yshift=12,
                font=dict(color=color, size=11)
            )

        # 2. Plot Reactions at Supports (Fixed 'n' variable error)
        for node in ts.nodes:
            if node.rx or node.ry:
                # Use 'node' instead of 'n' to avoid NameError
                rx_kn = round(node.rx_val / 1000, 2)
                ry_kn = round(node.ry_val / 1000, 2)
                
                fig.add_annotation(
                    x=node.x, y=node.y,
                    text=f"Rx: {rx_kn}kN, Ry: {ry_kn}kN",
                    showarrow=True,
                    arrowhead=1,
                    ax=0, ay=40,
                    font=dict(color="green", size=10),
                    bgcolor="white"
                )
                
                fig.add_trace(go.Scatter(
                    x=[node.x], y=[node.y],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=15, color='green'),
                    name=f"Support @ Node {node.id}"
                ))

    # Professional formatting
    fig.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), showlegend=True)
    st.session_state['current_fig'] = fig
    st.plotly_chart(fig, width='stretch')
    