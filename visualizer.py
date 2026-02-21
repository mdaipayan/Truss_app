import plotly.graph_objects as go
import pandas as pd
import numpy as np

import plotly.graph_objects as go
import pandas as pd
import numpy as np

def draw_undeformed_geometry(node_df, member_df, load_df, scale_factor=1000.0, unit_label="kN"):
    """Generates the base geometry Plotly figure and returns any input errors."""
    fig_base = go.Figure()
    node_errors, member_errors, load_errors = [], [], []
    
    # 1. Plot Supports and Nodes
    if not node_df.empty:
        for i, row in node_df.iterrows():
            try:
                if pd.isna(row.get('X')) or pd.isna(row.get('Y')): continue
                nx, ny = float(row['X']), float(row['Y'])
                
                rx = int(row.get('Restrain_X', 0)) if not pd.isna(row.get('Restrain_X')) else 0
                ry = int(row.get('Restrain_Y', 0)) if not pd.isna(row.get('Restrain_Y')) else 0
                
                if rx == 1 and ry == 1:
                    fig_base.add_trace(go.Scatter(x=[nx], y=[ny], mode='markers', marker=dict(symbol='triangle-up', size=20, color='forestgreen'), showlegend=False, hoverinfo='skip'))
                    fig_base.add_annotation(x=nx, y=ny, text="<b>Pin</b>", showarrow=False, yshift=-25, font=dict(color="forestgreen", size=11))
                elif rx == 0 and ry == 1:
                    fig_base.add_trace(go.Scatter(x=[nx], y=[ny], mode='markers', marker=dict(symbol='circle-open', size=18, color='forestgreen', line=dict(width=4)), showlegend=False, hoverinfo='skip'))
                    fig_base.add_annotation(x=nx, y=ny, text="<b>Roller</b>", showarrow=False, yshift=-25, font=dict(color="forestgreen", size=11))
                elif rx == 1 and ry == 0:
                    fig_base.add_trace(go.Scatter(x=[nx], y=[ny], mode='markers', marker=dict(symbol='square-open', size=18, color='forestgreen', line=dict(width=4)), showlegend=False, hoverinfo='skip'))
                    fig_base.add_annotation(x=nx, y=ny, text="<b>Roller (X-fixed)</b>", showarrow=False, xshift=-35, font=dict(color="forestgreen", size=11))
                
                fig_base.add_trace(go.Scatter(x=[nx], y=[ny], mode='markers+text', text=[f"<b>Node {i+1}</b>"], textposition="top center", marker=dict(color='black', size=10), showlegend=False))
            except (ValueError, TypeError):
                node_errors.append(str(i+1))

    # 2. Plot Members
    if not node_df.empty and not member_df.empty:
        for i, row in member_df.iterrows():
            try:
                if pd.isna(row.get('Node_I')) or pd.isna(row.get('Node_J')): continue
                ni, nj = int(row['Node_I'])-1, int(row['Node_J'])-1
                
                # FIX: Check against the actual index labels, not the length of the dataframe
                if ni not in node_df.index or nj not in node_df.index:
                    member_errors.append(f"M{i+1} (Invalid Node ID)")
                    continue
                    
                # FIX: Use .loc for label-based indexing to survive row deletions
                n1, n2 = node_df.loc[ni], node_df.loc[nj]
                
                if pd.isna(n1.get('X')) or pd.isna(n2.get('X')): continue
                x0, y0, x1, y1 = float(n1['X']), float(n1['Y']), float(n2['X']), float(n2['Y'])
                
                fig_base.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode='lines', line=dict(color='gray', width=2, dash='dash'), showlegend=False))
                fig_base.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=f"<b>M{i+1}</b>", showarrow=False, font=dict(color="blue", size=11), bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="blue", borderwidth=1)
            except (ValueError, TypeError, IndexError):
                member_errors.append(f"M{i+1}")

    # 3. Plot Load Arrows
    if not node_df.empty and not load_df.empty:
        for i, row in load_df.iterrows():
            try:
                if pd.isna(row.get('Node_ID')): continue
                node_idx = int(row['Node_ID']) - 1
                
                # FIX: Check against the actual index labels
                if node_idx not in node_df.index:
                    load_errors.append(f"Row {i+1} (Node not found)")
                    continue
                    
                # FIX: Use .loc for label-based indexing
                nx, ny = float(node_df.loc[node_idx]['X']), float(node_df.loc[node_idx]['Y'])
                
                fy = float(row.get('Force_Y (N)', 0)) if not pd.isna(row.get('Force_Y (N)')) else 0.0
                fx = float(row.get('Force_X (N)', 0)) if not pd.isna(row.get('Force_X (N)')) else 0.0
                
                if abs(fy) > 0:
                    ay_val = -50 if fy > 0 else 50
                    fig_base.add_annotation(x=nx, y=ny, ax=0, ay=ay_val, xref="x", yref="y", axref="pixel", ayref="pixel", text=f"<b>{round(abs(fy)/scale_factor, 2)} {unit_label}</b>", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2.5, arrowcolor="darkorange", font=dict(color="darkorange", size=11), bgcolor="white")
                if abs(fx) > 0:
                    ax_val = -50 if fx > 0 else 50
                    fig_base.add_annotation(x=nx, y=ny, ax=ax_val, ay=0, xref="x", yref="y", axref="pixel", ayref="pixel", text=f"<b>{round(abs(fx)/scale_factor, 2)} {unit_label}</b>", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2.5, arrowcolor="darkorange", font=dict(color="darkorange", size=11), bgcolor="white")
            except (ValueError, TypeError, IndexError):
                load_errors.append(f"Row {i+1}")

    fig_base.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='white')
    return fig_base, node_errors, member_errors, load_errors


def draw_results_fbd(ts, scale_factor=1000.0, unit_label="kN"):
    """Generates the solved free-body diagram figure with separated reactions."""
    fig_res = go.Figure()
    
    # Plot Members with Forces
    for mbr in ts.members:
        f = mbr.calculate_force()
        val_scaled = round(abs(f) / scale_factor, 2)
        
        # Determine Color and Nature
        if val_scaled < 0.01:
            nature, color = "Zero-Force", "darkgray"
        else:
            nature = "Compressive" if f < 0 else "Tensile"
            color = "crimson" if f < 0 else "royalblue"
        
        x0, y0, x1, y1 = mbr.node_i.x, mbr.node_i.y, mbr.node_j.x, mbr.node_j.y
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        
        dx, dy = x1 - x0, y1 - y0
        angle_deg = np.degrees(np.arctan2(dy, dx))
        if angle_deg > 90: angle_deg -= 180
        elif angle_deg < -90: angle_deg += 180
        
        fig_res.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode='lines', line=dict(color=color, width=8), showlegend=False))
        
        # Add labels based on scaled value
        if val_scaled >= 0.01: 
            label_html = f"<b>{val_scaled} {unit_label}</b><br><i>{nature}</i>"
            fig_res.add_annotation(x=mid_x, y=mid_y, text=label_html, showarrow=False, textangle=-angle_deg, yshift=25, font=dict(color=color, size=12), bgcolor="rgba(255,255,255,0.9)", bordercolor=color, borderwidth=2, borderpad=3)
        else:
            fig_res.add_annotation(x=mid_x, y=mid_y, text=f"0.0 {unit_label}", showarrow=False, font=dict(color="gray", size=10), bgcolor="white")

    # Draw Nodes and Separated Support Reactions
    for node in ts.nodes:
        fig_res.add_trace(go.Scatter(x=[node.x], y=[node.y], mode='markers', marker=dict(color='black', size=12, line=dict(color='white', width=2)), showlegend=False))
        
        if node.rx:
            rx_scaled = round(node.rx_val / scale_factor, 2)
            ax_val = -50 if rx_scaled >= 0 else 50
            fig_res.add_annotation(x=node.x, y=node.y, text=f"<b>Rx: {abs(rx_scaled)} {unit_label}</b>", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=3, arrowcolor="darkgreen", ax=ax_val, ay=0, font=dict(color="white", size=11), bgcolor="darkgreen")
            
        if node.ry:
            ry_scaled = round(node.ry_val / scale_factor, 2)
            ay_val = 50 if ry_scaled >= 0 else -50
            fig_res.add_annotation(x=node.x, y=node.y, text=f"<b>Ry: {abs(ry_scaled)} {unit_label}</b>", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=3, arrowcolor="darkgreen", ax=0, ay=ay_val, font=dict(color="white", size=11), bgcolor="darkgreen")

    fig_res.update_layout(yaxis=dict(scaleanchor="x", scaleratio=1), plot_bgcolor='rgb(240, 242, 246)', margin=dict(l=0, r=0, t=30, b=0))
    return fig_res
