
from pathlib import Path
import re
import sys
from datetime import datetime

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, Preformatted,
    KeepTogether, HRFlowable
)
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "Report"
SOURCE = REPORT_DIR / "OmniSight_Final_Project_Report.md"

DOCX_OUT = REPORT_DIR / "OmniSight_Final_Report_20261106.docx"
PDF_OUT = REPORT_DIR / "OmniSight_Final_Report_20261106.pdf"


def fail(message):
    print(f"\nERROR: {message}")
    sys.exit(1)


def read_and_validate():
    if not SOURCE.is_file():
        fail(f"Source report not found: {SOURCE}")

    text = SOURCE.read_text(encoding="utf-8-sig")

    # Validate Markdown code fences.
    fences = re.findall(r"(?m)^```", text)
    if len(fences) % 2:
        fail("Unmatched Markdown code fence. No output generated.")

    # Validate the numbered main report sections.
    sections = re.findall(r"(?m)^#\s+\d+\.\s+", text)
    if len(sections) != 18:
        fail(
            f"Expected 18 numbered main sections; found {len(sections)}. "
            "Review the source before generating."
        )

    # Validate every Markdown image reference.
    image_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    for reference in image_refs:
        image_path = (REPORT_DIR / reference).resolve()
        if not image_path.is_file():
            fail(f"Referenced image not found: {image_path}")

    if DOCX_OUT.exists() or PDF_OUT.exists():
        fail(
            "An output file with the selected date already exists. "
            "Rename the outputs in this script before running again."
        )

    print("Source validation passed.")
    print(f"Numbered sections: {len(sections)}")
    print(f"Code fences: {len(fences)}")
    print(f"Image references: {len(image_refs)}")

    return text


def inline_docx(paragraph, text):
    pattern = r"(\*\*.*?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))"
    parts = re.split(pattern, text)

    for part in parts:
        if not part:
            continue

        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True

        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(90, 60, 130)

        elif part.startswith("[") and "](" in part:
            match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)
            if match:
                run = paragraph.add_run(match.group(1))
                run.underline = True
                run.font.color.rgb = RGBColor(35, 95, 160)
            else:
                paragraph.add_run(part)

        else:
            paragraph.add_run(part)


def set_cell_shading(cell, fill):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(shading)


def build_docx(text):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(6)

    for name, size in [
        ("Heading 1", 17),
        ("Heading 2", 13),
        ("Heading 3", 11),
    ]:
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(31, 78, 121)

    # Header and page number.
    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.add_run("OMNISIGHT | FINAL PROJECT REPORT").font.size = Pt(8)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Page ")

    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)

    lines = text.splitlines()
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        # Fenced code blocks, including Mermaid source.
        if line.startswith("```"):
            language = line[3:].strip()
            code_lines = []
            i += 1

            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1

            if i < len(lines):
                i += 1

            if language.lower() == "mermaid":
                p = doc.add_paragraph()
                run = p.add_run(
                    "Architecture sequence diagram source "
                    "(Mermaid; preserved as text)"
                )
                run.bold = True
                run.font.size = Pt(9)

            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.2)
            p.paragraph_format.space_after = Pt(8)
            run = p.add_run("\n".join(code_lines))
            run.font.name = "Consolas"
            run.font.size = Pt(8)
            continue

        # Markdown image.
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            image_path = (REPORT_DIR / image_match.group(2)).resolve()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(image_path), width=Inches(6.0))

            if image_match.group(1):
                caption = doc.add_paragraph(image_match.group(1))
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in caption.runs:
                    run.italic = True
                    run.font.size = Pt(9)
            i += 1
            continue

        # Horizontal rule.
        if re.fullmatch(r"[-*_]{3,}", line):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            i += 1
            continue

        # Markdown table.
        if line.startswith("|"):
            rows = []

            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [
                    cell.strip()
                    for cell in lines[i].strip().strip("|").split("|")
                ]

                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1

            if rows:
                column_count = max(len(row) for row in rows)
                table = doc.add_table(rows=0, cols=column_count)
                table.style = "Table Grid"
                table.alignment = WD_TABLE_ALIGNMENT.CENTER

                for row_index, row_data in enumerate(rows):
                    cells = table.add_row().cells

                    for col_index in range(column_count):
                        value = row_data[col_index] if col_index < len(row_data) else ""
                        cells[col_index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        p = cells[col_index].paragraphs[0]
                        inline_docx(p, value)

                        if row_index == 0:
                            set_cell_shading(cells[col_index], "D9EAF7")
                            for run in p.runs:
                                run.bold = True

                doc.add_paragraph()
            continue

        # Headings.
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            p = doc.add_paragraph(style=f"Heading {level}")
            inline_docx(p, heading.group(2))
            i += 1
            continue

        # Bullet and numbered lists.
        bullet = re.match(r"^\s*[-*]\s+(.+)$", raw)
        numbered = re.match(r"^\s*\d+\.\s+(.+)$", raw)

        if bullet or numbered:
            value = bullet.group(1) if bullet else numbered.group(1)
            style = "List Bullet" if bullet else "List Number"
            p = doc.add_paragraph(style=style)
            inline_docx(p, value)
            i += 1
            continue

        # Ordinary paragraph.
        p = doc.add_paragraph()
        inline_docx(p, line)
        i += 1

    doc.core_properties.title = "OmniSight Final Project Report"
    doc.core_properties.subject = "Multimodal UI Self-Healing and RPA Agent"
    doc.core_properties.author = "Sheefa J Pathan"

    doc.save(DOCX_OUT)
    print(f"DOCX created: {DOCX_OUT}")


def reportlab_inline(text):
    # Escape source text first, then apply supported Markdown formatting.
    value = escape(text)

    value = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        value
    )
    value = re.sub(
        r"`([^`]+)`",
        r'<font name="Courier" color="#5A3C82">\1</font>',
        value
    )

    link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    value = re.sub(link_pattern, r'<u>\1</u>', value)

    return value


def build_pdf(text):
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=21,
        leading=27,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1F4E79"),
        spaceAfter=16,
    ))

    styles.add(ParagraphStyle(
        name="ReportH1",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1F4E79"),
        spaceBefore=13,
        spaceAfter=7,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="ReportH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#315F86"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="ReportH3",
        parent=styles["Heading3"],
        fontSize=10.5,
        leading=13,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="ReportSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=3,
    ))

    story = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        # Fenced code and Mermaid blocks.
        if line.startswith("```"):
            language = line[3:].strip()
            code_lines = []
            i += 1

            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1

            if i < len(lines):
                i += 1

            if language.lower() == "mermaid":
                story.append(Paragraph(
                    "<b>Architecture sequence diagram source "
                    "(Mermaid; preserved as text)</b>",
                    styles["ReportSmall"]
                ))

            code_text = "\n".join(code_lines)
            story.append(Preformatted(
                code_text,
                ParagraphStyle(
                    "CodeBlock",
                    fontName="Courier",
                    fontSize=6.5,
                    leading=8,
                    leftIndent=8,
                    rightIndent=8,
                    backColor=colors.HexColor("#F1F3F5"),
                    borderPadding=6,
                )
            ))
            story.append(Spacer(1, 7))
            continue

        # Markdown image.
        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if image_match:
            image_path = (REPORT_DIR / image_match.group(2)).resolve()
            picture = Image(str(image_path))
            picture._restrictSize(6.4 * inch, 7.0 * inch)
            story.append(picture)

            if image_match.group(1):
                story.append(Paragraph(
                    escape(image_match.group(1)),
                    styles["Italic"]
                ))

            story.append(Spacer(1, 8))
            i += 1
            continue

        if re.fullmatch(r"[-*_]{3,}", line):
            story.append(HRFlowable(
                width="100%",
                thickness=0.6,
                color=colors.lightgrey,
                spaceBefore=5,
                spaceAfter=8,
            ))
            i += 1
            continue

        # Markdown table.
        if line.startswith("|"):
            rows = []

            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [
                    cell.strip()
                    for cell in lines[i].strip().strip("|").split("|")
                ]

                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1

            if rows:
                column_count = max(len(row) for row in rows)
                data = []

                for row in rows:
                    data.append([
                        Paragraph(
                            reportlab_inline(row[c] if c < len(row) else ""),
                            styles["ReportSmall"]
                        )
                        for c in range(column_count)
                    ])

                table = Table(data, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C9D6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(table)
                story.append(Spacer(1, 8))
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            heading_text = reportlab_inline(heading.group(2))

            # Main title formatting.
            if i == 0 and level == 1:
                story.append(Paragraph(heading_text, styles["ReportTitle"]))
            else:
                style_name = {
                    1: "ReportH1",
                    2: "ReportH2",
                    3: "ReportH3",
                }[level]
                story.append(Paragraph(heading_text, styles[style_name]))

            i += 1
            continue

        bullet = re.match(r"^\s*[-*]\s+(.+)$", raw)
        numbered = re.match(r"^\s*\d+\.\s+(.+)$", raw)

        if bullet:
            story.append(Paragraph(
                "&bull;&nbsp;&nbsp;" + reportlab_inline(bullet.group(1)),
                styles["ReportBody"]
            ))
            i += 1
            continue

        if numbered:
            story.append(Paragraph(
                reportlab_inline(numbered.group(0)),
                styles["ReportBody"]
            ))
            i += 1
            continue

        story.append(Paragraph(reportlab_inline(line), styles["ReportBody"]))
        i += 1

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2,
            0.38 * inch,
            f"OmniSight Final Project Report | Page {document.page}"
        )
        canvas.restoreState()

    pdf = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="OmniSight Final Project Report",
        author="Sheefa J Pathan",
    )

    pdf.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    print(f"PDF created: {PDF_OUT}")


def main():
    print("OmniSight Final Review Report Generator")
    print("=" * 45)

    text = read_and_validate()

    build_docx(text)
    build_pdf(text)

    print("\nGeneration completed.")
    print("Please inspect both documents before submission.")
    print("Mermaid sequence is preserved as formatted source text,")
    print("not rendered as a graphical sequence diagram.")


if __name__ == "__main__":
    main()
