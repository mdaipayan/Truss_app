import base64
import datetime
import html
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path

import streamlit as st


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


def _build_html(truss_system, image_base_path=None, image_res_path=None, scale_factor=1000.0, unit_label="kN"):
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
  footer {{ position: fixed; bottom: -8mm; left: 0; right: 0; color: #6b7280; font-size: 9px; border-top: 1px solid #d9e2ec; padding-top: 4px; }}
</style>
</head>
<body>
  <footer>Professional Truss Suite - Direct Stiffness Method Report</footer>
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
</body>
</html>
"""


def _chromium_executable():
    for command in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        executable = shutil.which(command)
        if executable:
            return executable
    return None


def _render_pdf_from_html(html_content, html_path, pdf_path):
    html_path.write_text(html_content, encoding="utf-8")
    chromium = _chromium_executable()
    if not chromium:
        _write_basic_pdf(pdf_path, "Structural Analysis Report\n\nPDF rendering requires Chromium.")
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
        _write_basic_pdf(pdf_path, "Structural Analysis Report\n\nPDF rendering failed in the current environment.")


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


def generate_report(truss_system, fig_base=None, fig_res=None, scale_factor=1000.0, unit_label="kN"):
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
    )

    try:
        _render_pdf_from_html(html_content, html_path, report_path)
    finally:
        for temp_path in (image_base_path, image_res_path, html_path):
            if temp_path.exists():
                temp_path.unlink()

    return str(report_path)
