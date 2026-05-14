import base64
import datetime
import html
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path

import streamlit as st


REFERENCE_TEXT = (
    "Mandal, D. (2026). Development of an interactive web-based tool for 2D truss "
    "analysis using the direct stiffness method. Computer Applications in Engineering "
    "Education, 34(3), e70183."
)
REFERENCE_DOI = "https://doi.org/10.1002/cae.70183"
REFERENCE_BIBTEX = """@article{mandal2026truss,
  title={Development of an interactive web-based tool for 2D truss analysis using the direct stiffness method},
  author={Mandal, Daipayan},
  journal={Computer Applications in Engineering Education},
  volume={34},
  number={3},
  pages={e70183},
  year={2026},
  publisher={Wiley},
  doi={10.1002/cae.70183},
  url={https://doi.org/10.1002/cae.70183}
}"""


def save_truss_plot(fig, filename):
    try:
        fig.write_image(filename, engine="kaleido", format="png", scale=3, width=1000, height=800)
        return True
    except Exception as e:
        st.error(f"Kaleido Export Error: {e}")
        return False


def _format(value):
    return html.escape(str(value))


def _table(headers, rows):
    header_html = "".join(f"<th>{_format(header)}</th>" for header in headers)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{_format(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>"


def _image_html(path, caption):
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return f"""
        <figure>
            <img src="data:image/png;base64,{encoded}" alt="{_format(caption)}" />
            <figcaption>{_format(caption)}</figcaption>
        </figure>
    """


def _format_number(value):
    return f"{float(value):.6e}"


def _matrix_table(matrix, row_labels=None, col_labels=None):
    rows = []
    if col_labels is not None:
        rows.append(["", *col_labels])
    for index, row_values in enumerate(matrix):
        formatted_row = [_format_number(value) for value in row_values]
        if row_labels is not None:
            formatted_row.insert(0, row_labels[index])
        rows.append(formatted_row)

    body = "".join(
        "<tr>" + "".join(f"<td>{_format(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table class='matrix-table'><tbody>{body}</tbody></table>"


def _calculation_details_html(truss_system):
    sections = [
        "<h2>Detailed Direct Stiffness Method Calculations</h2>",
        "<p class='formula'>Element axial stiffness: k_local = (EA/L) [[1, -1], [-1, 1]]</p>",
        "<p class='formula'>Transformation vector: T = [-c, -s, c, s], with c = Δx/L and s = Δy/L.</p>",
        "<p class='formula'>Element global stiffness: k_global = (EA/L) TᵀT.</p>",
    ]

    for mbr in truss_system.members:
        length = mbr.L or mbr.get_length()
        c_value = mbr.c
        s_value = mbr.s
        axial_stiffness = mbr.E * mbr.A / length
        local_matrix = [[axial_stiffness, -axial_stiffness], [-axial_stiffness, axial_stiffness]]
        t_vector = mbr.T_vector if mbr.T_vector is not None else [-c_value, -s_value, c_value, s_value]
        t_transpose = [[value] for value in t_vector]
        u_local = mbr.u_local if mbr.u_local is not None else [mbr.node_i.ux, mbr.node_i.uy, mbr.node_j.ux, mbr.node_j.uy]
        k_global = mbr.k_global_matrix if mbr.k_global_matrix is not None else mbr.get_k_global()

        sections.extend([
            f"<h3>Member {mbr.id} Full Calculation</h3>",
            "<p class='formula'>"
            f"Δx = {_format_number(mbr.node_j.x - mbr.node_i.x)} m, "
            f"Δy = {_format_number(mbr.node_j.y - mbr.node_i.y)} m, "
            f"L = {_format_number(length)} m, c = {_format_number(c_value)}, s = {_format_number(s_value)}"
            "</p>",
            "<p class='formula'>"
            f"EA/L = ({_format_number(mbr.E)} × {_format_number(mbr.A)}) / {_format_number(length)} "
            f"= {_format_number(axial_stiffness)} N/m"
            "</p>",
            "<h4>Local stiffness matrix k_local</h4>",
            _matrix_table(local_matrix, row_labels=["i", "j"], col_labels=["i", "j"]),
            "<h4>Transformation matrix/vector T</h4>",
            _matrix_table([t_vector], col_labels=["-c", "-s", "c", "s"]),
            "<h4>Transpose matrix Tᵀ</h4>",
            _matrix_table(t_transpose, row_labels=["-c", "-s", "c", "s"]),
            "<h4>Element global stiffness matrix k_global</h4>",
            _matrix_table(k_global, row_labels=["uix", "uiy", "ujx", "ujy"], col_labels=["uix", "uiy", "ujx", "ujy"]),
            "<h4>Member displacement vector and axial force</h4>",
            _matrix_table([u_local], col_labels=["uix", "uiy", "ujx", "ujy"]),
            "<p class='formula'>"
            f"F_axial = (EA/L)(T · u_local) = {_format_number(mbr.internal_force)} N"
            "</p>",
        ])

    if truss_system.K_global is not None:
        dof_labels = [f"DOF {index}" for index in range(truss_system.K_global.shape[0])]
        sections.extend([
            "<h3>Assembled Global Stiffness Matrix K_global</h3>",
            _matrix_table(truss_system.K_global, row_labels=dof_labels, col_labels=dof_labels),
        ])

    if truss_system.K_reduced is not None:
        free_labels = [f"DOF {index}" for index in truss_system.free_dofs]
        sections.extend([
            "<h3>Reduced System K_ff U_f = F_f</h3>",
            f"<p class='formula'>Free DOFs: {_format(truss_system.free_dofs)}</p>",
            "<h4>Reduced stiffness matrix K_ff</h4>",
            _matrix_table(truss_system.K_reduced, row_labels=free_labels, col_labels=free_labels),
        ])

    if truss_system.F_reduced is not None:
        sections.extend([
            "<h4>Reduced load vector F_f</h4>",
            _matrix_table([[value] for value in truss_system.F_reduced], row_labels=[f"DOF {index}" for index in truss_system.free_dofs], col_labels=["Force (N)"]),
        ])

    if truss_system.U_global is not None:
        sections.extend([
            "<h3>Solved Global Displacement Vector U_global</h3>",
            _matrix_table([[value] for value in truss_system.U_global], row_labels=[f"DOF {index}" for index in range(len(truss_system.U_global))], col_labels=["Displacement (m)"]),
        ])

    return "".join(sections)


def _calculation_details_text(truss_system):
    lines = [
        "",
        "Detailed Direct Stiffness Method Calculations",
        "Element axial stiffness: k_local = (EA/L) [[1, -1], [-1, 1]]",
        "Transformation vector: T = [-c, -s, c, s] where c = dx/L and s = dy/L",
        "Element global stiffness: k_global = (EA/L) T^T T",
    ]
    for mbr in truss_system.members:
        length = mbr.L or mbr.get_length()
        axial_stiffness = mbr.E * mbr.A / length
        t_vector = mbr.T_vector if mbr.T_vector is not None else [-mbr.c, -mbr.s, mbr.c, mbr.s]
        u_local = mbr.u_local if mbr.u_local is not None else [mbr.node_i.ux, mbr.node_i.uy, mbr.node_j.ux, mbr.node_j.uy]
        lines.extend([
            "",
            f"Member {mbr.id}",
            f"dx={_format_number(mbr.node_j.x - mbr.node_i.x)} m, dy={_format_number(mbr.node_j.y - mbr.node_i.y)} m",
            f"L={_format_number(length)} m, c={_format_number(mbr.c)}, s={_format_number(mbr.s)}",
            f"EA/L=({_format_number(mbr.E)} * {_format_number(mbr.A)}) / {_format_number(length)} = {_format_number(axial_stiffness)} N/m",
            f"T={[_format_number(value) for value in t_vector]}",
            f"T^T={[_format_number(value) for value in t_vector]}",
            f"u_local={[_format_number(value) for value in u_local]}",
            f"F_axial=(EA/L)(T.u_local)={_format_number(mbr.internal_force)} N",
        ])
    if truss_system.K_global is not None:
        lines.extend(["", f"K_global shape: {truss_system.K_global.shape}", str(truss_system.K_global)])
    if truss_system.K_reduced is not None:
        lines.extend(["", f"Free DOFs: {truss_system.free_dofs}", "K_ff:", str(truss_system.K_reduced)])
    if truss_system.F_reduced is not None:
        lines.extend(["F_f:", str(truss_system.F_reduced)])
    if truss_system.U_global is not None:
        lines.extend(["U_global:", str(truss_system.U_global)])
    return "\n".join(lines)


def _build_html(truss_system, image_base_path=None, image_res_path=None, scale_factor=1000.0, unit_label="kN", include_calculations=False):
    software_rows = [
        ("Software Name", "Professional Truss Suite"),
        ("Developer", "Mr. D Mandal, Assistant Professor, KITS Ramtek"),
        ("Core Engine", "Direct Stiffness Method (DSM)"),
        ("Analysis Type", "Linear Static 2D Truss Analysis"),
        ("Visualization", "Plotly Rendering Engine"),
        ("Report Format", "Portable Document Format (PDF)"),
    ]

    support_count = sum(1 for node in truss_system.nodes if node.rx or node.ry)
    summary_rows = [
        ("Nodes", len(truss_system.nodes)),
        ("Members", len(truss_system.members)),
        ("Supported Nodes", support_count),
        ("Force Display Unit", unit_label),
    ]

    material_rows = [(mbr.id, f"{mbr.A:.2e}", f"{mbr.E:.2e}") for mbr in truss_system.members]

    displacement_rows = []
    for node in truss_system.nodes:
        visual_id = getattr(node, "user_id", node.id)
        displacement_rows.append((visual_id, f"{node.ux:.6e}", f"{node.uy:.6e}"))

    reaction_rows = []
    for node in truss_system.nodes:
        if node.rx == 1 or node.ry == 1:
            visual_id = getattr(node, "user_id", node.id)
            reaction_rows.append(
                (
                    visual_id,
                    round(node.rx_val / scale_factor, 2) if node.rx == 1 else "0.0",
                    round(node.ry_val / scale_factor, 2) if node.ry == 1 else "0.0",
                )
            )

    result_rows = []
    for mbr in truss_system.members:
        force = mbr.calculate_force()
        scaled_force = abs(force) / scale_factor
        if scaled_force < 0.01:
            nature = "Zero-Force"
        else:
            nature = "Compressive" if force < 0 else "Tensile"
        result_rows.append((mbr.id, round(scaled_force, 2), nature))

    figure_sections = []
    if image_base_path:
        figure_sections.append(_image_html(image_base_path, "Undeformed Geometry Visualization"))
    if image_res_path:
        figure_sections.append(_image_html(image_res_path, "Structural Forces Visualization"))
    figures_html = "".join(figure_sections)

    reactions_html = (
        _table(["Node ID", f"Rx ({unit_label})", f"Ry ({unit_label})"], reaction_rows)
        if reaction_rows
        else "<p class='note'>No rigid support reactions calculated.</p>"
    )
    calculation_details_html = _calculation_details_html(truss_system) if include_calculations else ""

    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Structural Analysis Report</title>
<style>
  @page {{ size: A4; margin: 16mm 14mm 17mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: Arial, Helvetica, sans-serif; color: #1f2933; margin: 0; }}
  .cover {{ border-bottom: 4px solid #1f4e79; padding-bottom: 14px; margin-bottom: 18px; }}
  h1 {{ color: #1f4e79; font-size: 28px; margin: 0 0 6px; letter-spacing: 0.2px; }}
  h2 {{ color: #1f4e79; font-size: 16px; margin: 22px 0 9px; border-bottom: 1px solid #b7c9dc; padding-bottom: 4px; }}
  .subtitle {{ color: #52616f; font-size: 11px; margin: 0; }}
  .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }}
  table {{ width: 100%; border-collapse: collapse; margin: 7px 0 13px; page-break-inside: avoid; }}
  th {{ background: #1f4e79; color: #fff; text-align: center; font-size: 10px; padding: 7px 6px; }}
  td {{ border: 1px solid #c9d3df; font-size: 10px; padding: 6px; text-align: center; }}
  tbody tr:nth-child(even) td {{ background: #f3f6fa; }}
  figure {{ margin: 12px 0 18px; page-break-inside: avoid; text-align: center; }}
  img {{ max-width: 100%; max-height: 470px; border: 1px solid #c9d3df; padding: 5px; }}
  figcaption {{ color: #52616f; font-size: 10px; margin-top: 5px; }}
  .note {{ background: #fff8e1; border-left: 4px solid #f5a623; padding: 9px; font-size: 10px; }}
  .reference {{ font-size: 10px; line-height: 1.45; }}
  .formula {{ font-size: 10px; line-height: 1.45; }}
  h3 {{ color: #305f89; font-size: 13px; margin: 16px 0 7px; }}
  h4 {{ color: #40566b; font-size: 11px; margin: 10px 0 5px; }}
  .matrix-table {{ font-family: "Courier New", monospace; font-size: 8px; page-break-inside: avoid; }}
  .matrix-table td {{ padding: 4px; }}
  .bibtex {{ white-space: pre-wrap; background: #f3f6fa; border: 1px solid #c9d3df; padding: 8px; font-size: 9px; line-height: 1.35; }}
  .report-footer {{ color: #6b7280; font-size: 9px; border-top: 1px solid #d9e2ec; padding-top: 6px; margin-top: 18px; }}
</style>
</head>
<body>
  <section class="cover">
    <h1>Structural Analysis Report</h1>
    <p class="subtitle">Generated: {_format(generated_at)} | Analysis Type: Linear Static 2D Truss Analysis</p>
  </section>

  <section class="summary-grid">
    <div>
      <h2>Software Specifications</h2>
      {_table(["Property", "Details"], software_rows)}
    </div>
    <div>
      <h2>Model Summary</h2>
      {_table(["Metric", "Value"], summary_rows)}
    </div>
  </section>

  <h2>Material &amp; Section Properties</h2>
  {_table(["Member ID", "Area (sq.m)", "E (N/sq.m)"], material_rows)}

  {figures_html}

  <h2>Nodal Displacements</h2>
  {_table(["Node ID", "Ux (m)", "Uy (m)"], displacement_rows)}

  <h2>Support Reactions</h2>
  {reactions_html}

  <h2>Detailed Analysis Results</h2>
  {_table(["Member", f"Force ({unit_label})", "Nature"], result_rows)}

  {calculation_details_html}

  <h2>Reference</h2>
  <p class="reference">{_format(REFERENCE_TEXT)} DOI: <a href="{REFERENCE_DOI}">{REFERENCE_DOI}</a></p>
  <pre class="bibtex">{_format(REFERENCE_BIBTEX)}</pre>

  <div class="report-footer">Professional Truss Suite - Direct Stiffness Method Report</div>
</body>
</html>
"""


def _chromium_executable():
    for command in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        executable = shutil.which(command)
        if executable:
            return executable
    return None


def _build_text_report(truss_system, scale_factor=1000.0, unit_label="kN", include_calculations=False):
    lines = [
        "Structural Analysis Report",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Software Specifications",
        "- Software Name: Professional Truss Suite",
        "- Core Engine: Direct Stiffness Method (DSM)",
        "- Analysis Type: Linear Static 2D Truss Analysis",
        "",
        "Model Summary",
        f"- Nodes: {len(truss_system.nodes)}",
        f"- Members: {len(truss_system.members)}",
        f"- Force Display Unit: {unit_label}",
        "",
        "Nodal Displacements",
    ]
    for node in truss_system.nodes:
        visual_id = getattr(node, "user_id", node.id)
        lines.append(f"- Node {visual_id}: Ux={node.ux:.6e} m, Uy={node.uy:.6e} m")

    lines.extend(["", "Support Reactions"])
    has_reactions = False
    for node in truss_system.nodes:
        if node.rx == 1 or node.ry == 1:
            has_reactions = True
            visual_id = getattr(node, "user_id", node.id)
            rx_value = round(node.rx_val / scale_factor, 2) if node.rx == 1 else "0.0"
            ry_value = round(node.ry_val / scale_factor, 2) if node.ry == 1 else "0.0"
            lines.append(f"- Node {visual_id}: Rx={rx_value} {unit_label}, Ry={ry_value} {unit_label}")
    if not has_reactions:
        lines.append("- No rigid support reactions calculated.")

    lines.extend(["", "Detailed Analysis Results"])
    for mbr in truss_system.members:
        force = mbr.calculate_force()
        scaled_force = abs(force) / scale_factor
        if scaled_force < 0.01:
            nature = "Zero-Force"
        else:
            nature = "Compressive" if force < 0 else "Tensile"
        lines.append(f"- Member {mbr.id}: {round(scaled_force, 2)} {unit_label}, {nature}")

    if include_calculations:
        lines.append(_calculation_details_text(truss_system))

    lines.extend(["", "Reference", f"{REFERENCE_TEXT} DOI: {REFERENCE_DOI}", "", REFERENCE_BIBTEX])
    return "\n".join(lines)


def _render_pdf_from_html(html_content, html_path, pdf_path, fallback_text):
    html_path.write_text(html_content, encoding="utf-8")
    chromium = _chromium_executable()
    if not chromium:
        _write_basic_pdf(pdf_path, fallback_text)
        return

    try:
        subprocess.run(
            [
                chromium,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                str(html_path.resolve()),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        st.error(f"Chromium PDF Export Error: {exc.stderr or exc}")
        _write_basic_pdf(pdf_path, fallback_text)


def _pdf_escape(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_basic_pdf(pdf_path, text):
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, width=82) or [""])

    content_lines = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines[:52]):
        if index:
            content_lines.append("T*")
        content_lines.append(f"({_pdf_escape(line)}) Tj")
    content_lines.append("ET")
    content = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(content)} >> stream\n".encode("ascii") + content + b"\nendstream endobj\n",
    ]

    with open(pdf_path, "wb") as pdf_file:
        pdf_file.write(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(pdf_file.tell())
            pdf_file.write(obj)
        xref_pos = pdf_file.tell()
        pdf_file.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        pdf_file.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf_file.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        pdf_file.write(
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
        )


def generate_report(truss_system, fig_base=None, fig_res=None, scale_factor=1000.0, unit_label="kN", include_calculations=False):
    uid = str(uuid.uuid4())[:8]
    image_base_path = Path(f"temp_base_{uid}.png")
    image_res_path = Path(f"temp_res_{uid}.png")
    html_path = Path(f"Analysis_Report_{uid}.html")
    report_path = Path(f"Analysis_Report_{uid}.pdf")

    base_image_for_html = None
    result_image_for_html = None

    if fig_base is not None and save_truss_plot(fig_base, image_base_path):
        base_image_for_html = image_base_path
    if fig_res is not None and save_truss_plot(fig_res, image_res_path):
        result_image_for_html = image_res_path

    html_content = _build_html(
        truss_system,
        image_base_path=base_image_for_html,
        image_res_path=result_image_for_html,
        scale_factor=scale_factor,
        unit_label=unit_label,
        include_calculations=include_calculations,
    )
    fallback_text = _build_text_report(
        truss_system,
        scale_factor=scale_factor,
        unit_label=unit_label,
        include_calculations=include_calculations,
    )

    try:
        _render_pdf_from_html(html_content, html_path, report_path, fallback_text)
    finally:
        for temp_path in (image_base_path, image_res_path, html_path):
            if temp_path.exists():
                temp_path.unlink()

    return str(report_path)
