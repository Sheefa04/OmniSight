import os
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DOCX = PROJECT_ROOT / "OmniSight_Mid_Review_Project_Report.docx"
EVIDENCE_DIR = PROJECT_ROOT / "screenshots" / "evidence"

# Brand Colors
COLOR_PRIMARY = RGBColor(23, 76, 66)       # #174C42 Deep Teal
COLOR_SECONDARY = RGBColor(40, 102, 91)    # #28665B Sage Slate
COLOR_DARK = RGBColor(30, 41, 59)          # #1E293B Charcoal
COLOR_MUTED = RGBColor(100, 116, 139)      # #64748B Slate Muted
HEX_PRIMARY = "174C42"
HEX_LIGHT_BG = "F8FAFC"
HEX_BORDER = "CBD5E1"
HEX_CALLOUT_BG = "F0FDF4"
HEX_CALLOUT_BORDER = "174C42"

def set_cell_background(cell, fill_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_header_footer(doc):
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)
        
        # Header
        header = s.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("OmniSight: Multimodal UI Self-Healing & RPA Agent  |  Mid-Review Report")
        hrun.font.name = "Arial"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = COLOR_MUTED
        
        # Footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        frun = fp.add_run("Department of Artificial Intelligence and Data Science  |  Page ")
        frun.font.name = "Arial"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = COLOR_MUTED
        
        # Add Page Numbering XML field
        fldSimple = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls('w'))
        fp._p.append(fldSimple)

def add_styled_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(4)
    run = h.runs[0]
    run.font.name = "Arial"
    if level == 1:
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = COLOR_PRIMARY
    elif level == 2:
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = COLOR_SECONDARY
    else:
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = COLOR_DARK
    return h

def add_body_paragraph(doc, text="", bold_prefix=None, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        brun = p.add_run(bold_prefix)
        brun.font.name = "Arial"
        brun.font.size = Pt(10.5)
        brun.font.bold = True
        brun.font.color.rgb = COLOR_DARK
    if text:
        run = p.add_run(text)
        run.font.name = "Arial"
        run.font.size = Pt(10.5)
        run.font.color.rgb = COLOR_DARK
    return p

def add_callout_box(doc, text, title=None):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.27)
    set_cell_background(cell, HEX_CALLOUT_BG)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border only
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="0" w:color="{HEX_CALLOUT_BORDER}"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if title:
        trun = p.add_run(title + "\n")
        trun.font.name = "Arial"
        trun.font.size = Pt(10.5)
        trun.font.bold = True
        trun.font.color.rgb = COLOR_PRIMARY
    run = p.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(9.5)
    run.font.color.rgb = COLOR_DARK
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def format_table(tbl, col_widths, headers, data):
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    # Header Row
    hdr_cells = tbl.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].width = Inches(col_widths[i])
        set_cell_background(hdr_cells[i], HEX_PRIMARY)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(title)
        run.font.name = "Arial"
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        
    # Data Rows
    for r_idx, row_data in enumerate(data):
        row = tbl.add_row()
        fill = HEX_LIGHT_BG if (r_idx % 2 == 1) else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = Inches(col_widths[c_idx])
            set_cell_background(cell, fill)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(str(val))
            run.font.name = "Arial"
            run.font.size = Pt(9.0)
            run.font.color.rgb = COLOR_DARK
            
            # Status badge styling for Pass
            if str(val) == "PASS":
                run.font.bold = True
                run.font.color.rgb = RGBColor(40, 102, 91)

    # Subtle borders for all cells
    for row in tbl.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            b = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/><w:left w:val="none"/><w:right w:val="none"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_BORDER}"/></w:tcBorders>')
            tcPr.append(b)
            
    doc_p = tbl._element.getparent()

def generate_report():
    doc = Document()
    add_header_footer(doc)
    
    # ----------------------------------------------------
    # COVER / TITLE PAGE
    # ----------------------------------------------------
    cover_p0 = doc.add_paragraph()
    cover_p0.paragraph_format.space_before = Pt(36)
    cover_p0.paragraph_format.space_after = Pt(6)
    c0 = cover_p0.add_run("INTERNSHIP PROJECT MID-REVIEW REPORT")
    c0.font.name = "Arial"
    c0.font.size = Pt(12)
    c0.font.bold = True
    c0.font.color.rgb = COLOR_SECONDARY
    
    cover_p1 = doc.add_paragraph()
    cover_p1.paragraph_format.space_after = Pt(12)
    c1 = cover_p1.add_run("OmniSight: Multimodal UI Self-Healing & RPA Agent")
    c1.font.name = "Arial"
    c1.font.size = Pt(26)
    c1.font.bold = True
    c1.font.color.rgb = COLOR_PRIMARY
    
    cover_p2 = doc.add_paragraph()
    cover_p2.paragraph_format.space_after = Pt(32)
    c2 = cover_p2.add_run("Automated Website UI Inspection, Heuristic Issue Detection, and Approved Browser Remediation Engine")
    c2.font.name = "Arial"
    c2.font.size = Pt(13)
    c2.font.color.rgb = COLOR_MUTED
    
    # Metadata Table on Title Page
    meta_tbl = doc.add_table(rows=6, cols=2)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    meta_data = [
        ("Student Name:", "Sheefa J Pathan"),
        ("Degree & Branch:", "Bachelor of Engineering (B.E.), Artificial Intelligence and Data Science"),
        ("Institution:", "DR. D Y PATIL TECHNICAL CAMPUS"),
        ("Domain:", "Artificial Intelligence, Robotic Process Automation (RPA), Automated Web QA"),
        ("Review Type:", "Internship Project Mid-Review"),
        ("Repository URL:", "https://github.com/Sheefa04/OmniSight")
    ]
    for idx, (label, val) in enumerate(meta_data):
        c_lbl = meta_tbl.cell(idx, 0)
        c_val = meta_tbl.cell(idx, 1)
        c_lbl.width = Inches(2.0)
        c_val.width = Inches(4.27)
        set_cell_margins(c_lbl, top=60, bottom=60, left=40, right=40)
        set_cell_margins(c_val, top=60, bottom=60, left=40, right=40)
        
        p_l = c_lbl.paragraphs[0]
        p_l.paragraph_format.space_after = Pt(2)
        r_l = p_l.add_run(label)
        r_l.font.name = "Arial"
        r_l.font.size = Pt(10)
        r_l.font.bold = True
        r_l.font.color.rgb = COLOR_PRIMARY
        
        p_v = c_val.paragraphs[0]
        p_v.paragraph_format.space_after = Pt(2)
        r_v = p_v.add_run(val)
        r_v.font.name = "Arial"
        r_v.font.size = Pt(10)
        r_v.font.color.rgb = COLOR_DARK
        
    doc.add_page_break()
    
    # ----------------------------------------------------
    # TABLE OF CONTENTS
    # ----------------------------------------------------
    add_styled_heading(doc, "Table of Contents", level=1)
    toc_items = [
        ("1. Abstract", "3"),
        ("2. Introduction", "3"),
        ("3. Problem Statement", "4"),
        ("4. Objectives", "4"),
        ("5. Scope: Current Implementation and Out-of-Scope Features", "5"),
        ("6. Existing Systems and Limitations", "5"),
        ("7. Proposed System", "6"),
        ("8. Hardware and Software Requirements", "7"),
        ("9. System Architecture and Workflow", "7"),
        ("10. Technology Stack", "8"),
        ("11. Implementation Details", "9"),
        ("    11.1 FastAPI Backend (backend/main.py)", "9"),
        ("    11.2 Playwright & Chromium Automation", "9"),
        ("    11.3 DOM & Computed-Style Heuristics", "10"),
        ("    11.4 Human Approval Gate for Repairs", "10"),
        ("    11.5 Session-Scoped CSS Repair Safety", "10"),
        ("    11.6 Dashboard Interface (frontend/dashboard.html)", "11"),
        ("    11.7 ShopHub Demo Store (frontend/store.html)", "11"),
        ("12. Testing and Results (Reported Test Cases)", "12"),
        ("13. Screenshots and Visual Evidence Gallery", "13"),
        ("14. Limitations", "15"),
        ("15. Future Scope", "15"),
        ("16. Conclusion", "16"),
        ("17. References", "16"),
        ("18. Pre-Submission Checklist", "17")
    ]
    for item, page in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        r_item = p.add_run(item)
        r_item.font.name = "Arial"
        r_item.font.size = Pt(10)
        r_item.font.color.rgb = COLOR_DARK
        
        # Dots
        dots_count = max(5, 75 - len(item) - len(page))
        r_dots = p.add_run(" " + ("." * dots_count) + " ")
        r_dots.font.name = "Arial"
        r_dots.font.size = Pt(10)
        r_dots.font.color.rgb = COLOR_MUTED
        
        r_page = p.add_run(page)
        r_page.font.name = "Arial"
        r_page.font.size = Pt(10)
        r_page.font.bold = True
        r_page.font.color.rgb = COLOR_PRIMARY
        
    doc.add_page_break()
    
    # ----------------------------------------------------
    # 1. ABSTRACT
    # ----------------------------------------------------
    add_styled_heading(doc, "1. Abstract", level=1)
    add_body_paragraph(doc, 
        "Web applications deployed across dynamic client viewports frequently encounter visual defects such as unwrapped text elements, oversized buttons, and horizontal viewport overflow. While traditional automated testing suites (e.g. unit and functional testing tools) excel at detecting DOM node presence or HTTP API failures, they universally fail to evaluate aesthetic, geometric, and responsive layout integrity. Consequently, visual QA has remained an expensive, manual bottleneck, requiring engineers to visually discover, diagnose, and remediate visual regressions.")
    add_body_paragraph(doc, 
        "OmniSight introduces an interactive, human-supervised UI self-healing architecture. Powered by a high-concurrency FastAPI asynchronous backend and Playwright headless Chromium automation, OmniSight navigates to target websites across standard desktop, tablet, and mobile breakpoints. The engine conducts deterministic DOM and computed-style heuristic analysis to locate visual anomalies, captures full-page visual evidence, and presents diagnostic reports to the user. Upon explicit human authorization (approved=true), OmniSight injects safe, scoped CSS repairs within an active browser session, captures post-repair evidence, and renders dynamic Before/After visual comparisons. This report documents the completed mid-review prototype, verified across responsive viewports, validated against safety constraints, and supported by visual evidence.")

    # ----------------------------------------------------
    # 2. INTRODUCTION
    # ----------------------------------------------------
    add_styled_heading(doc, "2. Introduction", level=1)
    add_body_paragraph(doc, 
        "In modern web application engineering, user interfaces (UIs) represent the primary touchpoint between software products and end users. With the proliferation of diverse device form factors—ranging from high-resolution desktop monitors (1366×768) to modern smartphones (375×812, 390×844)—ensuring consistent visual rendering has become an intricate challenge. A CSS rule tailored for multi-column desktop grids can easily trigger text truncation, component collision, or page horizontal overflow on compact mobile viewports.")
    add_body_paragraph(doc, 
        "OmniSight bridges the gap between visual defect discovery and immediate remediation. Rather than merely recording failure logs in isolated testing consoles, OmniSight demonstrates the exact layout correction inside a real browser session. The core innovation rests on an approved self-healing loop: inspecting websites, evaluating layout geometry, requiring developer approval, and injecting temporary CSS repairs without mutating source files.")

    # ----------------------------------------------------
    # 3. PROBLEM STATEMENT
    # ----------------------------------------------------
    add_styled_heading(doc, "3. Problem Statement", level=1)
    add_body_paragraph(doc, "The project addresses four primary challenges in modern web quality engineering:")
    add_body_paragraph(doc, " Traditional test frameworks verify functional code execution (e.g., verifying a button triggers an API call) but cannot detect when fixed padding or unwrapped text causes that same button to spill off the screen.", bold_prefix="1. Invisibility of Visual Layout Breakages: ")
    add_body_paragraph(doc, " Identifying visual bugs requires human QA testers to physically resize viewports or inspect simulated devices, slowing release velocity.", bold_prefix="2. High Cost of Manual Responsive QA: ")
    add_body_paragraph(doc, " Autonomous bots that directly rewrite server-side source files introduce high risk of regression or unintended side-effects into production codebases.", bold_prefix="3. Safety Concerns in Autonomous AI Agents: ")
    add_body_paragraph(doc, " Stakeholders and engineers require immediate side-by-side visual proof (Before vs. After) to confirm that a proposed CSS remediation resolves the bug without harming surrounding components.", bold_prefix="4. Lack of Tangible Visual Evidence: ")

    # ----------------------------------------------------
    # 4. OBJECTIVES
    # ----------------------------------------------------
    add_styled_heading(doc, "4. Objectives", level=1)
    add_body_paragraph(doc, "The key technical objectives established for this internship project mid-review are:")
    add_body_paragraph(doc, " Develop an automated inspection controller using Playwright Chromium to ingest any valid HTTP/HTTPS URL and capture timestamped full-page screenshots across custom viewports.", bold_prefix="• Multi-Viewport Automated Inspection: ")
    add_body_paragraph(doc, " Implement deterministic DOM and computed-style evaluation algorithms to identify oversized elements, unwrapped buttons, and horizontal document overflow.", bold_prefix="• Geometric Heuristic Detection: ")
    add_body_paragraph(doc, " Enforce a mandatory authorization gate requiring explicit human approval (approved=true) before applying any remediation.", bold_prefix="• Human-in-the-Loop Safety Gate: ")
    add_body_paragraph(doc, " Apply non-destructive CSS repairs inside an active browser session without altering original source code files.", bold_prefix="• Safe Session-Scoped Remediation: ")
    add_body_paragraph(doc, " Construct a modern web dashboard featuring real-time backend health monitoring, issue diagnostics, and dynamic Before/After visual comparisons.", bold_prefix="• Dynamic Evidence Dashboard: ")

    # ----------------------------------------------------
    # 5. SCOPE: CURRENT IMPLEMENTATION VS OUT-OF-SCOPE
    # ----------------------------------------------------
    add_styled_heading(doc, "5. Scope: Current Implementation and Out-of-Scope Features", level=1)
    add_body_paragraph(doc, "To maintain academic honesty and clear engineering boundaries, the project distinguishes strictly between current verified deliverables and planned future capabilities:")
    
    scope_headers = ["Feature Category", "Current Mid-Review Scope (Implemented)", "Future Project Scope (Out-of-Scope)"]
    scope_data = [
        ["Backend Architecture", "FastAPI asynchronous service with /health, /inspect-browser, /detect-issues, and /repair-ui.", "Distributed multi-agent microservice architecture."],
        ["Browser Automation", "Playwright Chromium headless browser engine running on Windows Proactor Event Loop.", "Multi-browser matrix (WebKit/Safari, Firefox) and native mobile emulators."],
        ["Issue Detection", "Deterministic DOM bounding-box checks and computed-style heuristics (oversized-button, overflow).", "Generative Vision-Language Model (VLM) reasoning for qualitative visual balance."],
        ["Repair Mechanism", "Session-scoped CSS injection (max-width, white-space) applied in isolated browser session.", "Automated Git commit creation and GitHub Pull Request patch generation."],
        ["Target Website", "ShopHub demo store (frontend/store.html) and public HTTP/HTTPS URLs.", "Enterprise single-page apps (SPAs) requiring complex multi-step authentication."],
        ["Evidence & Reporting", "Dynamic Before/After dashboard display and PNG screenshot storage.", "Automated downloadable PDF/HTML executive audit report generation."]
    ]
    scope_tbl = doc.add_table(rows=1, cols=3)
    format_table(scope_tbl, [1.5, 2.4, 2.37], scope_headers, scope_data)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ----------------------------------------------------
    # 6. EXISTING SYSTEMS AND LIMITATIONS
    # ----------------------------------------------------
    add_styled_heading(doc, "6. Existing Systems and Limitations", level=1)
    add_body_paragraph(doc, "Existing quality assurance platforms fall into two distinct paradigms, neither of which fulfills the self-healing requirements addressed by OmniSight:")
    
    comp_headers = ["Platform Category", "Representative Tools", "Primary Operating Method", "Key Limitations"]
    comp_data = [
        ["Functional Testing Frameworks", "Selenium, Cypress, Playwright Test", "Validates DOM element presence, text content, and HTTP status codes.", "Passes tests even when components are clipped, hidden, or visually broken on mobile screens. No repair capability."],
        ["Visual Regression Testing", "Applitools Eyes, Percy by BrowserStack", "Captures baseline screenshots and performs pixel-by-pixel differential hashing.", "Extremely sensitive to minor dynamic content (anti-aliasing, ads). Identifies differences but cannot diagnose causes or generate repairs."],
        ["OmniSight (Proposed Platform)", "OmniSight Agent", "Combines DOM geometric heuristics, human approval gating, and session-scoped CSS repair.", "Provides closed-loop diagnosis, approved repair execution, and side-by-side visual verification without altering code."]
    ]
    comp_tbl = doc.add_table(rows=1, cols=4)
    format_table(comp_tbl, [1.4, 1.4, 1.7, 1.77], comp_headers, comp_data)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ----------------------------------------------------
    # 7. PROPOSED SYSTEM
    # ----------------------------------------------------
    add_styled_heading(doc, "7. Proposed System", level=1)
    add_body_paragraph(doc, 
        "OmniSight implements an intelligent 5-stage closed-loop quality engineering workflow. By coupling browser automation with explicit human supervision, the system detects visual layout defects and demonstrates immediate remediation:")
    add_body_paragraph(doc, " The developer inputs a target URL and selects the viewport breakpoint (Desktop 1366×768, Tablet 768×1024, Mobile 375×812 or 390×844).", bold_prefix="Stage 1 - Target Ingestion & Emulation: ")
    add_body_paragraph(doc, " Playwright launches headless Chromium, navigates to the URL, awaits network idle, and saves a high-resolution baseline screenshot with a unique UUID.", bold_prefix="Stage 2 - Automated Baseline Capture: ")
    add_body_paragraph(doc, " An in-page evaluation script inspects element bounding boxes and computed styles, flagging elements that extend beyond window boundaries or exhibit fixed unwrapped styling.", bold_prefix="Stage 3 - Deterministic Heuristic Analysis: ")
    add_body_paragraph(doc, " The dashboard presents the detected defect to the developer. The system enforces an absolute security gate: remediation cannot proceed without explicit user approval.", bold_prefix="Stage 4 - Human-in-the-Loop Approval: ")
    add_body_paragraph(doc, " Upon approval (approved=true), Playwright injects safe scoped CSS rules into the browser session, captures the post-repair screenshot, and renders dynamic Before/After visual comparison images.", bold_prefix="Stage 5 - Session Remediation & Verification: ")

    # ----------------------------------------------------
    # 8. HARDWARE AND SOFTWARE REQUIREMENTS
    # ----------------------------------------------------
    add_styled_heading(doc, "8. Hardware and Software Requirements", level=1)
    
    req_headers = ["Category", "Minimum Specification", "Recommended Specification", "Purpose in Project"]
    req_data = [
        ["Processor (CPU)", "Intel Core i5 / AMD Ryzen 5 (2.4 GHz)", "Intel Core i7 / AMD Ryzen 7 (3.2 GHz+)", "Concurrent execution of FastAPI server and headless Chromium."],
        ["System Memory (RAM)", "8 GB DDR4", "16 GB DDR4/DDR5", "Headless browser instances require sufficient memory for rendering."],
        ["Disk Storage", "2 GB free space", "10 GB SSD storage", "Storage for virtual environments, Playwright drivers, and screenshots."],
        ["Operating System", "Windows 10/11 64-bit", "Windows 11 64-bit", "Host OS configured with Windows Proactor Event Loop for subprocesses."],
        ["Python Runtime", "Python 3.10", "Python 3.12 (64-bit)", "Core backend language providing native async/await capabilities."],
        ["Browser Engine", "Chromium (Playwright managed)", "Chromium v1.50+", "Headless browser automation engine for navigation and screenshotting."]
    ]
    req_tbl = doc.add_table(rows=1, cols=4)
    format_table(req_tbl, [1.4, 1.4, 1.6, 1.87], req_headers, req_data)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ----------------------------------------------------
    # 9. SYSTEM ARCHITECTURE AND WORKFLOW
    # ----------------------------------------------------
    add_styled_heading(doc, "9. System Architecture and Workflow", level=1)
    add_body_paragraph(doc, 
        "The architecture of OmniSight decouples the client user interface from the heavy browser automation engine through an asynchronous REST API:")
    
    add_callout_box(doc,
        "OmniSight System Architecture Flow:\n\n"
        "[Client Dashboard (frontend/dashboard.html)]\n"
        "      │   ▲   (Asynchronous REST API / JSON)\n"
        "      ▼   │\n"
        "[FastAPI Backend Server (backend/main.py @ localhost:8000)]\n"
        "      │   ├── /health          -> System connectivity monitoring\n"
        "      │   ├── /inspect-browser -> Full-page screenshot capture\n"
        "      │   ├── /detect-issues   -> DOM & computed-style heuristics\n"
        "      │   └── /repair-ui       -> Scoped CSS session repair (requires approved=true)\n"
        "      ▼\n"
        "[Playwright Automation Engine (Async Python + Chromium)]\n"
        "      │   ├── Viewport Emulation (1366x768, 768x1024, 375x812, 390x844)\n"
        "      │   ├── DOM Tree Traversal & Client Rect Evaluation\n"
        "      │   └── Scoped <style id='omnisight-demo-repair'> Injection\n"
        "      ▼\n"
        "[Target Web Page: ShopHub Demo Store (frontend/store.html)]\n"
        "      │\n"
        "      ▼\n"
        "[Screenshot Storage: backend/screenshots/ (Exposed via FastAPI StaticFiles)]",
        title="Figure 9.1: OmniSight Technical Architecture Diagram"
    )
    
    add_body_paragraph(doc, 
        "Data flows sequentially: The dashboard submits the target URL and viewport via HTTP POST. FastAPI validates the payload with Pydantic and dispatches an asynchronous worker to Playwright. Playwright launches Chromium, sets viewport constraints, navigates to the page, and executes DOM scripts. Output screenshots are written to backend/screenshots/ and returned as relative URLs, which the frontend mounts dynamically with timestamp query strings (?t=timestamp) to circumvent browser caching.")

    # ----------------------------------------------------
    # 10. TECHNOLOGY STACK
    # ----------------------------------------------------
    add_styled_heading(doc, "10. Technology Stack", level=1)
    add_body_paragraph(doc, "The technology stack was selected to prioritize asynchronous concurrency, browser fidelity, and lightweight, framework-free frontend performance:")
    add_body_paragraph(doc, " Powers the REST API. Chosen for native Python async/await support, automatic OpenAPI/Swagger documentation generation, and high throughput.", bold_prefix="• FastAPI (Python 3.12): ")
    add_body_paragraph(doc, " Controls headless Chromium. Chosen over Selenium due to superior execution speed, native viewport sizing, network idle listeners, and asynchronous execution.", bold_prefix="• Playwright for Python: ")
    add_body_paragraph(doc, " Enforces strict data validation on incoming URLs (HttpUrl) and request payloads, preventing malformed requests from reaching the browser engine.", bold_prefix="• Pydantic v2: ")
    add_body_paragraph(doc, " Specifically configured at the entry point of main.py to resolve Windows-specific event loop limitations when spawning browser subprocesses.", bold_prefix="• Windows Proactor Event Loop Policy: ")
    add_body_paragraph(doc, " Engineered without heavyweight frameworks (e.g. React or Vue) to ensure rapid loading, complete styling control, and zero build-step overhead.", bold_prefix="• Vanilla HTML5, CSS3, & Modern ES6 JavaScript: ")

    # ----------------------------------------------------
    # 11. IMPLEMENTATION DETAILS
    # ----------------------------------------------------
    add_styled_heading(doc, "11. Implementation Details", level=1)
    
    add_styled_heading(doc, "11.1 FastAPI Backend (backend/main.py)", level=2)
    add_body_paragraph(doc, 
        "The backend server exposes four core REST endpoints configured with Cross-Origin Resource Sharing (CORSMiddleware) to allow requests from local origins. Dynamic screenshot files are served statically through app.mount('/screenshots', StaticFiles(directory=SCREENSHOT_DIR)). Validation logic ensures that only HTTP/HTTPS protocols are accepted, preventing arbitrary local file access.")

    add_styled_heading(doc, "11.2 Playwright and Chromium Browser Automation", level=2)
    add_body_paragraph(doc, 
        "Browser instances are launched asynchronously using async_playwright().start(). For each inspection or repair request, an isolated browser context is instantiated with explicit viewport width and height. Pages navigate using wait_until='domcontentloaded' with a 30-second fail-safe timeout, guaranteeing clean resource release in finally blocks.")

    add_styled_heading(doc, "11.3 DOM and Computed-Style Heuristic Issue Detection", level=2)
    add_body_paragraph(doc, 
        "The /detect-issues endpoint evaluates DOM geometry in the browser context via page.evaluate(). It checks all visible elements: (1) whether rect.right > window.innerWidth + 1 (overflowing viewport), (2) whether document.documentElement.scrollWidth > window.innerWidth (page-wide horizontal scrollbar), and (3) whether elements matching button.broken-button or button.buggy-button exhibit unwrapped text or oversized dimensions. Detected issues are returned as structured JSON containing element tag, bounding dimensions, and textual descriptions.")

    add_styled_heading(doc, "11.4 Human Approval Gate for Repairs", level=2)
    add_body_paragraph(doc, 
        "To enforce safe robotic process automation, the /repair-ui endpoint implements a strict security check: if not request.approved: raise HTTPException(status_code=400, detail='Repair not applied. Set approved=true to authorize the demo repair.'). This ensures that remediation actions can never be executed autonomously without human consent.")

    add_styled_heading(doc, "11.5 Session-Scoped CSS Repair Without Modifying Original Files", level=2)
    add_body_paragraph(doc, 
        "When approved, the repair engine injects a scoped <style> block into document.head targeting the defective button:")
    add_callout_box(doc,
        "button.buggy-button, button.broken-button {\n"
        "    position: relative !important;\n"
        "    max-width: 100% !important;\n"
        "    box-sizing: border-box !important;\n"
        "    white-space: normal !important;\n"
        "    overflow-wrap: anywhere !important;\n"
        "    z-index: 1 !important;\n"
        "}",
        title="Listing 11.1: Scoped Temporary CSS Remediation Rule"
    )
    add_body_paragraph(doc, 
        "This rule constrains button width to its parent container and forces text to wrap cleanly across multiple lines. The fix exists exclusively inside that Chromium session; target website source files are not modified.")

    add_styled_heading(doc, "11.6 Dashboard Interface (frontend/dashboard.html)", level=2)
    add_body_paragraph(doc, 
        "The dashboard features input forms for URL and viewport selection, live backend health pills, metrics cards (Websites Inspected, Issues Detected, Repairs Applied), an inspection evidence viewer, and a Before/After comparison card. The frontend includes a dedicated formatApiError() utility that parses complex FastAPI error objects into human-readable strings, resolving the previous Error: [object Object] bug.")

    add_styled_heading(doc, "11.7 ShopHub Demo Store (frontend/store.html)", level=2)
    add_body_paragraph(doc, 
        "ShopHub is a standalone responsive e-commerce demo site featuring an intentional responsive flaw: an 'Add to Cart — Special Offer' button (.broken-button) with white-space: nowrap and oversized horizontal padding. On desktop screens, it sits inside a wide product grid, but on mobile viewports (<700px), it extends across its container and risks overflowing.")

    # ----------------------------------------------------
    # 12. TESTING AND RESULTS
    # ----------------------------------------------------
    add_styled_heading(doc, "12. Testing and Results (Reported Test Cases)", level=1)
    add_body_paragraph(doc, 
        "The table below details all nine test cases defined for the OmniSight prototype. Note: These results represent reported test outputs generated during development and automated evaluation suites; they require confirmation against the latest live execution output before final submission.")
    
    test_headers = ["Test ID", "Test Case Description", "Input / Condition", "Expected Outcome", "Reported Status"]
    test_data = [
        ["TC-01", "API Health Check", "GET /health", "HTTP 200, status: healthy", "PASS"],
        ["TC-02", "Repair Without Approval", "POST /repair-ui with approved=false", "HTTP 400 rejection; repair blocked", "PASS"],
        ["TC-03", "Malformed URL Validation", "POST /repair-ui with invalid string", "HTTP 422 schema validation rejection", "PASS"],
        ["TC-04", "Non-Broken Page Handling", "POST /repair-ui on https://example.com", "HTTP 200, status: not_applied reported", "PASS"],
        ["TC-05", "Desktop Viewport Capture", "1366×768 resolution on store.html", "Full desktop page screenshot captured", "PASS"],
        ["TC-06", "Mobile 375×812 Inspection", "375×812 resolution on store.html", "Detect oversized button and unwrapped text", "PASS"],
        ["TC-07", "Mobile 390×844 Inspection", "390×844 resolution on store.html", "Verify rendering on modern iPhone standard", "PASS"],
        ["TC-08", "Tablet 768×1024 Inspection", "768×1024 resolution on store.html", "Verify 2-column responsive layout", "PASS"],
        ["TC-09", "Dashboard End-to-End Flow", "Full inspection & repair loop on UI", "Dynamic Before/After screenshots updated", "PASS"]
    ]
    test_tbl = doc.add_table(rows=1, cols=5)
    format_table(test_tbl, [0.8, 1.5, 1.6, 1.67, 0.7], test_headers, test_data)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ----------------------------------------------------
    # 13. SCREENSHOTS AND EVIDENCE
    # ----------------------------------------------------
    add_styled_heading(doc, "13. Screenshots and Visual Evidence Gallery", level=1)
    add_body_paragraph(doc, 
        "The following evidence files were generated by the automated test suite and stored in the project repository under screenshots/evidence/. Note: The existence, visual fidelity, and accuracy of each screenshot must be verified against current repository contents before final submission.")
    
    ev_files = [
        ("01_dashboard_initial.png", "Figure 13.1: OmniSight Dashboard Initial State before running inspection."),
        ("02_desktop_store_1366x768.png", "Figure 13.2: ShopHub Demo Store Baseline rendering on Desktop (1366×768)."),
        ("03_mobile_store_375x812.png", "Figure 13.3: ShopHub Demo Store Mobile Viewport (375×812) showing the unwrapped broken button."),
        ("03b_mobile_store_390x844.png", "Figure 13.4: ShopHub Demo Store Mobile Viewport on modern iPhone standard (390×844)."),
        ("04_tablet_store_768x1024.png", "Figure 13.5: ShopHub Demo Store Tablet Viewport rendering (768×1024)."),
        ("05_dashboard_issues_detected.png", "Figure 13.6: OmniSight Dashboard displaying detected issue metric (1 issue found)."),
        ("06_dashboard_repaired_comparison.png", "Figure 13.7: OmniSight Dashboard Before/After comparison panel with green success banner.")
    ]
    
    for filename, caption in ev_files:
        img_path = EVIDENCE_DIR / filename
        add_body_paragraph(doc, f"Evidence File: screenshots/evidence/{filename}", bold_prefix="• ")
        if img_path.exists():
            try:
                # Add picture centered
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(4)
                p_img.paragraph_format.space_after = Pt(2)
                p_img.add_run().add_picture(str(img_path), width=Inches(5.0))
            except Exception as e:
                add_body_paragraph(doc, f"[Image file present at {img_path.name}; could not embed inline: {e}]")
        else:
            add_body_paragraph(doc, f"[Image file {filename} referenced; verify file path prior to submission.]")
            
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(10)
        r_cap = p_cap.add_run(caption)
        r_cap.font.name = "Arial"
        r_cap.font.size = Pt(8.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = COLOR_MUTED

    # ----------------------------------------------------
    # 14. LIMITATIONS
    # ----------------------------------------------------
    add_styled_heading(doc, "14. Limitations", level=1)
    add_body_paragraph(doc, "In accordance with academic transparency, the following technical limitations are acknowledged:")
    add_body_paragraph(doc, " The CSS repair is injected solely into the active Playwright browser session and recorded in screenshots. It does not permanently alter the target website's HTML/CSS files.", bold_prefix="1. Session-Scoped Remediation: ")
    add_body_paragraph(doc, " The current issue detector uses deterministic geometry and computed styles. It cannot evaluate subjective visual quality, color contrast ratios, or aesthetic balance.", bold_prefix="2. Heuristic Detection Scope: ")
    add_body_paragraph(doc, " The current prototype does not yet include a fully integrated multimodal vision-language model; VLM reasoning is planned for future scope.", bold_prefix="3. Absence of Integrated VLM: ")
    add_body_paragraph(doc, " Inspection of remote external websites requires continuous outbound HTTP/HTTPS connectivity.", bold_prefix="4. Network Connectivity: ")

    # ----------------------------------------------------
    # 15. FUTURE SCOPE
    # ----------------------------------------------------
    add_styled_heading(doc, "15. Future Scope", level=1)
    add_body_paragraph(doc, "Following successful mid-review completion, the project will expand along four key engineering trajectories:")
    add_body_paragraph(doc, " Integrate multimodal vision models (e.g. Gemini Vision API) to evaluate screenshots for aesthetic balance, contrast compliance, and semantic visual harmony.", bold_prefix="1. Multimodal Vision-Language Model Integration: ")
    add_body_paragraph(doc, " Extend the agent to automatically re-evaluate the repaired DOM state to programmatically confirm zero remaining defects before presenting results.", bold_prefix="2. Automated Post-Repair Verification Agent: ")
    add_body_paragraph(doc, " Enable the engine to package approved CSS repairs into downloadable .patch/.diff files or submit automated GitHub Pull Requests.", bold_prefix="3. Source Code Patch & Pull Request Generator: ")
    add_body_paragraph(doc, " Implement automated export of comprehensive PDF and HTML audit reports containing embedded visual diffs and executive summaries.", bold_prefix="4. Downloadable Executive Audit Reports: ")

    # ----------------------------------------------------
    # 16. CONCLUSION
    # ----------------------------------------------------
    add_styled_heading(doc, "16. Conclusion", level=1)
    add_body_paragraph(doc, 
        "OmniSight establishes a validated, robust prototype demonstrating that automated website inspection, responsive issue detection, and safe UI self-healing can be unified into an efficient, human-supervised engineering tool. By coupling FastAPI with Playwright Chromium automation and enforcing mandatory human approval gates, the platform mitigates the risks of uncontrolled autonomous code mutation while providing engineers with undeniable Before/After visual proof. All nine mid-review test cases have been reported as passing, and the core blocking repair bug has been completely resolved. The platform provides a sound foundation for post-mid-review expansion into multimodal vision analysis.")

    # ----------------------------------------------------
    # 17. REFERENCES
    # ----------------------------------------------------
    add_styled_heading(doc, "17. References", level=1)
    refs = [
        ("1. FastAPI Documentation:", " Tiangolo, S. FastAPI: Modern, High-Performance Web Framework for Python. Available at: https://fastapi.tiangolo.com/"),
        ("2. Playwright for Python:", " Microsoft Corporation. Playwright: Fast and reliable end-to-end testing for modern web apps. Available at: https://playwright.dev/python/"),
        ("3. Pydantic Documentation:", " Colvin, S. et al. Pydantic: Data validation using Python type annotations. Available at: https://docs.pydantic.dev/"),
        ("4. W3C CSS Flexible Box Layout Module:", " World Wide Web Consortium. CSS Flexible Box Layout Module Level 1. Available at: https://www.w3.org/TR/css-flexbox-1/"),
        ("5. MDN Web Docs:", " Mozilla Developer Network. Responsive design concepts and media queries. Available at: https://developer.mozilla.org/")
    ]
    for pref, text in refs:
        add_body_paragraph(doc, text, bold_prefix=pref, space_after=4)

    # ----------------------------------------------------
    # 18. PRE-SUBMISSION CHECKLIST
    # ----------------------------------------------------
    add_styled_heading(doc, "18. Pre-Submission Checklist", level=1)
    add_body_paragraph(doc, "Before final submission of this mid-review report, verify that the following items are confirmed:")
    checklist_items = [
        "[  ] Verify that the student details (Sheefa J Pathan, DR. D Y PATIL TECHNICAL CAMPUS) match institutional records.",
        "[  ] Confirm all nine reported test cases (TC-01 to TC-09) against the latest automated test suite execution output.",
        "[  ] Confirm that all 7 referenced evidence screenshot files exist in screenshots/evidence/ and render clearly.",
        "[  ] Confirm that the GitHub repository (https://github.com/Sheefa04/OmniSight) is up to date with the latest commit.",
        "[  ] Ensure that all limitations regarding session-scoped CSS repair (non-permanent) are clearly articulated.",
        "[  ] Verify page numbering, table borders, and heading hierarchy in Microsoft Word before final printing or PDF export."
    ]
    for item in checklist_items:
        add_body_paragraph(doc, item, space_after=3)
        
    doc.save(str(OUTPUT_DOCX))
    print(f"Successfully generated Word document: {OUTPUT_DOCX}")

if __name__ == "__main__":
    generate_report()
