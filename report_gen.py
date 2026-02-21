from docx import Document
from docx.shared import Inches
import datetime
import plotly.io as pio
import streamlit as st
import uuid
import os

def save_truss_plot(fig, filename):
    try:
        fig.write_image(filename, engine="kaleido", format="png", scale=3, width=1000, height=800)
        return True
    except Exception as e:
        st.error(f"Kaleido Export Error: {e}")
        return False

def generate_report(truss_system, fig_base=None, fig_res=None, scale_factor=1000.0, unit_label="kN"):
    doc = Document()
    
    # FIX FOR CRITIQUE 11: Unique Identifiers prevent cross-user file clashes on the server
    uid = str(uuid.uuid4())[:8]
    image_base_path = f"temp_base_{uid}.png"
    image_res_path = f"temp_res_{uid}.png"
    report_name = f"Analysis_Report_{uid}.docx"
    
    doc.add_heading('Structural Analysis Report', 0)
    doc.add_paragraph(f"Report Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    doc.add_heading('Software Specifications', level=1)
    soft_table = doc.add_table(rows=1, cols=2)
    soft_table.style = 'Table Grid'
    hdr_cells = soft_table.rows[0].cells
    hdr_cells[0].text, hdr_cells[1].text = 'Property', 'Details'
    
    software_info = [
        ('Software Name', 'Professional Truss Suite'),
        ('Developer', 'Mr. D Mandal, Assistant Professor, KITS Ramtek'),
        ('Core Engine', 'Direct Stiffness Method (DSM)'),
        ('Analysis Type', 'Linear Static 2D Truss Analysis'),
        ('Visualization', 'Plotly Rendering Engine')
    ]
    
    for prop, detail in software_info:
        row_cells = soft_table.add_row().cells
        row_cells[0].text, row_cells[1].text = prop, detail

    doc.add_heading('Material & Section Properties', level=1)
    mat_table = doc.add_table(rows=1, cols=3)
    mat_table.style = 'Table Grid'
    mat_table.rows[0].cells[0].text, mat_table.rows[0].cells[1].text, mat_table.rows[0].cells[2].text = 'Member ID', 'Area (sq.m)', 'E (N/sq.m)'
    
    for mbr in truss_system.members:
        row = mat_table.add_row().cells
        row[0].text, row[1].text, row[2].text = str(mbr.id), f"{mbr.A:.2e}", f"{mbr.E:.2e}"

    if fig_base:
        doc.add_heading('Undeformed Geometry Visualization', level=1)
        if save_truss_plot(fig_base, image_base_path):
            doc.add_picture(image_base_path, width=Inches(5.5))
        else:
            doc.add_paragraph("Warning: Image generation failed due to environment constraints.")

    if fig_res:
        doc.add_heading('Structural Forces Visualization', level=1)
        if save_truss_plot(fig_res, image_res_path):
            doc.add_picture(image_res_path, width=Inches(5.5))
        else:
            doc.add_paragraph("Warning: Image generation failed due to environment constraints.")

    doc.add_heading('Nodal Displacements', level=1)
    disp_table = doc.add_table(rows=1, cols=3)
    disp_table.style = 'Table Grid'
    disp_table.rows[0].cells[0].text, disp_table.rows[0].cells[1].text, disp_table.rows[0].cells[2].text = 'Node ID', 'Ux (m)', 'Uy (m)'
    
    for n in truss_system.nodes:
        row = disp_table.add_row().cells
        # Safely get visual ID to match the screen
        visual_id = getattr(n, 'user_id', n.id)
        row[0].text, row[1].text, row[2].text = str(visual_id), f"{n.ux:.6e}", f"{n.uy:.6e}"

    doc.add_heading('Support Reactions', level=1)
    rxn_table = doc.add_table(rows=1, cols=3)
    rxn_table.style = 'Table Grid'
    rxn_table.rows[0].cells[0].text, rxn_table.rows[0].cells[1].text, rxn_table.rows[0].cells[2].text = 'Node ID', f'Rx ({unit_label})', f'Ry ({unit_label})'
    
    has_reactions = False
    for n in truss_system.nodes:
        if n.rx == 1 or n.ry == 1:
            has_reactions = True
            row = rxn_table.add_row().cells
            visual_id = getattr(n, 'user_id', n.id)
            row[0].text = str(visual_id)
            row[1].text = str(round(n.rx_val / scale_factor, 2)) if n.rx == 1 else "0.0"
            row[2].text = str(round(n.ry_val / scale_factor, 2)) if n.ry == 1 else "0.0"
            
    if not has_reactions: doc.add_paragraph("No rigid support reactions calculated.")

    doc.add_heading('Detailed Analysis Results', level=1)
    res_table = doc.add_table(rows=1, cols=3)
    res_table.style = 'Table Grid'
    res_table.rows[0].cells[0].text, res_table.rows[0].cells[1].text, res_table.rows[0].cells[2].text = 'Member', f'Force ({unit_label})', 'Nature'

    for mbr in truss_system.members:
        f = mbr.calculate_force()
        row = res_table.add_row().cells
        row[0].text, row[1].text = str(mbr.id), str(round(abs(f) / scale_factor, 2))
        if abs(f) / scale_factor < 0.01: row[2].text = "Zero-Force"
        else: row[2].text = "Compressive" if f < 0 else "Tensile"

    doc.save(report_name)
    
    # Clean up temp images to save server memory
    if os.path.exists(image_base_path): os.remove(image_base_path)
    if os.path.exists(image_res_path): os.remove(image_res_path)
        
    return report_name
        
