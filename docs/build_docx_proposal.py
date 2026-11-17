"""
CampusAssist: Automated Academic Proposal DOCX Generator
Builds a publication-grade Word document (.docx) with cover page,
numbered sections, tables, callouts, and embedded workflow diagrams.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

OUTPUT_FILE = "CampusAssist_Project_Proposal.docx"

def set_cell_background(cell, fill_hex):
    """Sets background color of a table cell."""
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets internal padding for a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_callout(doc, title, text, border_color="0F172A", bg_color="F8FAFC"):
    """Adds a stylish callout box with a colored left accent border."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=140)

    # Left border only
    borders_xml = f'''
    <w:tcBorders {nsdecls("w")}>
        <w:top w:val="none"/>
        <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>
        <w:bottom w:val="none"/>
        <w:right w:val="none"/>
    </w:tcBorders>
    '''
    cell._tc.get_or_add_tcPr().append(parse_xml(borders_xml))

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    run_t = p.add_run(f"[{title}]\n")
    run_t.bold = True
    run_t.font.size = Pt(10)
    run_t.font.color.rgb = RGBColor(15, 23, 42)

    run_b = p.add_run(text)
    run_b.font.size = Pt(9.5)
    run_b.font.color.rgb = RGBColor(51, 65, 85)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def style_heading(p, font_size=16, color_rgb=(15, 23, 42), bold=True, space_before=16, space_after=6):
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_with_next = True
    for r in p.runs:
        r.font.size = Pt(font_size)
        r.font.name = "Arial"
        r.font.bold = bold
        r.font.color.rgb = RGBColor(*color_rgb)

def add_section_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    if level == 1:
        style_heading(h, 15, (15, 23, 42), bold=True, space_before=18, space_after=6)
    elif level == 2:
        style_heading(h, 12.5, (30, 58, 138), bold=True, space_before=14, space_after=4)
    elif level == 3:
        style_heading(h, 11, (51, 65, 85), bold=True, space_before=10, space_after=3)
    return h

def build_document():
    doc = docx.Document()

    # Configure Margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # --------------------------------------------------------------------------
    # 1. COVER PAGE
    # --------------------------------------------------------------------------
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_inst.add_run("NATIONAL INSTITUTE OF TECHNOLOGY DURGAPUR\nDEPARTMENT OF COMPUTER SCIENCE & ENGINEERING\n")
    r_inst.bold = True
    r_inst.font.size = Pt(13)
    r_inst.font.color.rgb = RGBColor(15, 23, 42)

    # Spacing
    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_after = Pt(40)

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("CAMPUSASSIST\n")
    r_title.bold = True
    r_title.font.size = Pt(28)
    r_title.font.color.rgb = RGBColor(15, 23, 42)

    r_sub = p_title.add_run("Domain-Specific AI-Powered Student Assistance Web Application\nwith Retrieval-Augmented Grounding and Zero-Hallucination Guardrails\n")
    r_sub.bold = True
    r_sub.font.size = Pt(13)
    r_sub.font.color.rgb = RGBColor(37, 99, 235)

    # Horizontal Rule
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_line = p_line.add_run("_____________________________________________________________\n")
    r_line.font.color.rgb = RGBColor(203, 213, 225)

    p_doc = doc.add_paragraph()
    p_doc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_doc = p_doc.add_run("FINAL YEAR PROJECT PROPOSAL (B.TECH THESIS)")
    r_doc.bold = True
    r_doc.font.size = Pt(12)
    r_doc.font.color.rgb = RGBColor(100, 116, 139)

    # Spacer
    p_spacer2 = doc.add_paragraph()
    p_spacer2.paragraph_format.space_after = Pt(80)

    # Metadata Card
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = p_meta.add_run(
        "Submitted by:\n"
        "BITTYAM PAUL\n"
        "Department of Computer Science & Engineering\n"
        "National Institute of Technology Durgapur\n\n"
        "Supervised by:\n"
        "Project Evaluation Committee\n"
        "Department of Computer Science & Engineering\n"
        "Academic Year 2026\n"
    )
    r_meta.font.size = Pt(10.5)
    r_meta.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_page_break()

    # --------------------------------------------------------------------------
    # 2. ABSTRACT
    # --------------------------------------------------------------------------
    add_section_heading(doc, "2. Abstract", level=1)
    p_abs = doc.add_paragraph(
        "Navigating institutional procedures in higher education engineering institutes presents persistent logistical "
        "challenges for students. At the National Institute of Technology Durgapur (NIT Durgapur), official guidelines, "
        "procedural workflows, and administrative circulars governing hostel accommodation, semester academic registrations, "
        "mid-term/end-term examinations, and campus amenities are distributed across physical noticeboards, multi-page PDF "
        "handbooks, and segmented web portals. General-purpose commercial Large Language Models (LLMs) cannot reliably assist "
        "students because they lack internal access to localized NIT Durgapur regulations; when prompted, they frequently invent "
        "nonexistent rules or confuse policies from other institutions."
    )
    p_abs.paragraph_format.line_spacing = 1.15
    p_abs.paragraph_format.space_after = Pt(8)

    p_abs2 = doc.add_paragraph(
        "This project proposes and implements CampusAssist, a domain-specific, hallucination-resistant conversational student assistant. "
        "CampusAssist couples natural language intent classification and in-memory semantic vector search with a strictly controlled "
        "LLM generation layer under a Domain-Grounded Retrieval-Augmented Generation (RAG) architecture. Natural language queries are "
        "mapped into dense semantic vectors to identify underlying topics and intents, retrieving human-verified institutional records. "
        "If retrieved information satisfies statistical confidence thresholds (>= 0.50), an LLM synthesizes a grounded response citing "
        "official authorities and portal URLs. Conversely, if no verified record exists, a programmatic circuit breaker intercepts execution, "
        "refusing to fabricate policies and logging the query into an administrative triage queue for staff review."
    )
    p_abs2.paragraph_format.line_spacing = 1.15
    p_abs2.paragraph_format.space_after = Pt(8)

    add_callout(doc, "Key Academic Contributions",
                "• Strict Domain Grounding: Elimination of generative hallucination through pre-retrieval threshold gating.\n"
                "• Sub-Millisecond Vector Search: Custom in-memory NumPy dot-product engine executing in 0.19 ms.\n"
                "• Closed-Loop Knowledge Triage: Automated logging of unknown queries with atomic dynamic re-indexing.\n"
                "• Verified Empirical Reliability: 150 automated test cases with 100% pass rate under SQLite WAL mode.")

    # --------------------------------------------------------------------------
    # 3. INTRODUCTION
    # --------------------------------------------------------------------------
    add_section_heading(doc, "3. Introduction", level=1)
    doc.add_paragraph(
        "Modern engineering institutions operate complex multi-tiered administrative structures comprising academic sections, "
        "hall management councils, examination directorates, estate departments, and medical units. At NIT Durgapur, over 5,000 "
        "undergraduate, postgraduate, and doctoral students must interact with these administrative bodies for recurring procedural "
        "requirements throughout their academic journey."
    )
    doc.add_paragraph(
        "Students frequently encounter significant friction caused by information fragmentation. Official procedural circulars "
        "are distributed across physical caretaker desks, department bulletin boards, hostel registers, and ERP systems (Chanakya). "
        "Furthermore, students formulate questions using conversational slang ('Can I leave the hall tonight?') that fails to match "
        "the formal vocabulary found in official handbooks. General-purpose AI systems (e.g., ChatGPT, Gemini) cannot solve this problem "
        "in an unconstrained state because they lack internal access to localized NIT Durgapur circulars, leading to fabricated rules. "
        "CampusAssist addresses this by establishing a grounded, domain-specific retrieval-augmented architecture."
    )

    # --------------------------------------------------------------------------
    # 4. PROBLEM STATEMENT
    # --------------------------------------------------------------------------
    add_section_heading(doc, "4. Problem Statement", level=1)
    doc.add_paragraph(
        "Students at NIT Durgapur encounter difficulty in efficiently locating verified, actionable procedures across key operational areas:"
    )
    doc.add_paragraph(
        "1. Hostel Facilities & Rules: Gate passes, parental consent rules, mutual room swap criteria, electrical/water maintenance complaint logging, and curfew rules.\n"
        "2. Academic Registration: Semester registration workflows on the Chanakya ERP portal, elective subject enrollment, fee receipt submission, and late fine regulations.\n"
        "3. Examinations: Mid-term (30 marks) and end-term (50 marks) regulations, admit card downloads, calculator restrictions, medical absence reporting, and supplementary exam rules.\n"
        "4. Attendance Regulations: Minimum 75% classroom attendance requirements, condonation thresholds, and debarment consequences.\n"
        "5. Student Services & Amenities: Central library borrowing rules, Institute Medical Unit access, Wi-Fi configuration, and security lost-and-found helplines."
    )

    # --------------------------------------------------------------------------
    # 5. PROJECT OBJECTIVES
    # --------------------------------------------------------------------------
    add_section_heading(doc, "5. Project Objectives", level=1)
    doc.add_paragraph(
        "• Develop an Accessible Conversational Web Interface: Implement a responsive, lightweight, accessible student chat application requiring zero client compilation.\n"
        "• Centralize Verified Institutional Information: Construct a relational Knowledge Repository modeling institutional domains into Topics, Intents, and Verified Records.\n"
        "• Semantic Intent Identification: Implement normalized stem-aware text classification capable of recognizing student intent across arbitrary linguistic phrasing.\n"
        "• Sub-Millisecond Vector Retrieval: Implement an in-memory dense vector store utilizing vectorized matrix dot products for sub-millisecond cosine similarity search.\n"
        "• Enforce Factual Grounding: Construct bounded prompts that programmatically restrict the LLM to synthesized citations derived exclusively from retrieved verified context.\n"
        "• Implement a Zero-Hallucination Circuit Breaker: Programmatically intercept low-confidence queries (< 0.50), deliver safe fallback contact guidance, and catalog unresolved queries for administrative triage.\n"
        "• Provide Authorized Administrative Knowledge Management: Build a role-based administrative portal with PBKDF2 authentication, CSRF protection, and dynamic in-memory index synchronization.\n"
        "• Ensure High Availability & Offline Resilience: Architect dual-mode fallbacks: seamless transition from Google Gemini cloud embeddings/LLMs to local scikit-learn TF-IDF vectorizers and deterministic synthesizers."
    )

    # --------------------------------------------------------------------------
    # 6. PROPOSED SOLUTION & CORE PHILOSOPHY
    # --------------------------------------------------------------------------
    add_section_heading(doc, "6. Proposed Solution & Core Philosophy", level=1)
    doc.add_paragraph(
        "CampusAssist enforces a strict Verification Hierarchy: Every answer synthesized by the system is derived strictly from human-verified "
        "institutional records stored in a relational Knowledge Repository. The core operational sequence is:"
    )
    doc.add_paragraph(
        "Student Query  ==>  Topic & Intent Classification  ==>  Semantic Vector Search  ==>  Verified Knowledge Repository  ==>  Controlled LLM  ==>  Grounded Answer"
    )
    add_callout(doc, "Conceptual Example: Intent Generalization",
                "Consider these diverse questions:\n"
                "• 'How can I apply for hostel leave?'\n"
                "• 'I want to go home for two days. What should I do?'\n"
                "• 'Can I leave the hostel this weekend?'\n"
                "• 'What permission do I need to go home?'\n\n"
                "Traditional keyword queries fail on queries 2, 3, and 4. CampusAssist transforms each query into an L2-normalized vector. "
                "The mathematical cosine similarity between the query vector and the canonical intent anchors results in a high similarity score (>= 0.90), "
                "correctly routing all variations to Topic: Hostel, Intent: Hostel Leave, and retrieving the authoritative Caretaker/Warden procedure.")

    # --------------------------------------------------------------------------
    # 7. SYSTEM SCOPE
    # --------------------------------------------------------------------------
    add_section_heading(doc, "7. System Scope", level=1)
    doc.add_paragraph(
        "In-Scope Capabilities (Implemented in Current Prototype):\n"
        "• Multi-turn student conversational chat interface with session persistence.\n"
        "• Automatic intent classification and cosine similarity vector retrieval across 14 canonical institutional intents.\n"
        "• Grounded answer generation utilizing Google Gemini 2.5/1.5 Flash with deterministic offline fallback.\n"
        "• Contextual follow-up understanding resolving conversational anaphora ('Can I take it for 4 days?').\n"
        "• Programmatic circuit breaker routing sub-threshold queries to the unresolved_queries table.\n"
        "• Secure administrative portal featuring PBKDF2 authentication, CSRF synchronizer tokens, sliding-window rate limiting, and knowledge CRUD.\n"
        "• Real-time in-memory vector index synchronization upon administrative knowledge verification.\n"
        "• Complete automated test suite comprising 150 test cases with 100% pass rate.\n\n"
        "Out-of-Scope Capabilities (Planned Future Extensions):\n"
        "• Centralized NIT Durgapur LDAP / Single Sign-On student authentication (students currently use client-side UUID session tokens).\n"
        "• Automated document ingestion via optical character recognition (OCR) for scanned circular PDFs.\n"
        "• Multilingual and code-mixed translation (Hindi / Bengali / Hinglish phonetic parsing).\n"
        "• Direct bidirectional database integration with the institute's Chanakya ERP backend."
    )

    # --------------------------------------------------------------------------
    # 8. FUNCTIONAL REQUIREMENTS
    # --------------------------------------------------------------------------
    add_section_heading(doc, "8. Functional Requirements", level=1)
    
    fr_data = [
        ("FR-01", "Student Chat UI", "Responsive web chat UI supporting text input, markdown rendering, touch/keyboard accessibility.", "Fully Implemented"),
        ("FR-02", "Rate Limiting", "Sliding-window rate limits (60 req/min for chat, 5 req/15 min for login) to prevent abuse.", "Fully Implemented"),
        ("FR-03", "Input Validation", "Validate query bounds (non-empty, string type, maximum 1500 characters) with sanitized errors.", "Fully Implemented"),
        ("FR-04", "Intent Classification", "Classify student questions into institutional Topics and Intents with calibrated probability scoring.", "Fully Implemented"),
        ("FR-05", "Vector Embedding", "Generate 768-dimensional float32 semantic vectors with bounded LRU memory caching.", "Fully Implemented"),
        ("FR-06", "Semantic Search", "In-memory dot-product cosine similarity search filtered strictly by active and verified status.", "Fully Implemented"),
        ("FR-07", "Multi-Turn Memory", "Disambiguate follow-up questions using prior conversational turns to maintain context continuity.", "Fully Implemented"),
        ("FR-08", "Grounded Synthesis", "Synthesize responses strictly bounded by retrieved verified context with zero hallucination.", "Fully Implemented"),
        ("FR-09", "Circuit Breaker", "Intercept queries scoring below 0.50 similarity, block LLM invocation, and log to triage queue.", "Fully Implemented"),
        ("FR-10", "Admin Auth & RBAC", "Secure admin portal via salted PBKDF2 password hashing (260,000 rounds) and session tokens.", "Fully Implemented"),
        ("FR-11", "Knowledge CRUD", "Allow authorized staff to create, edit, verify, activate/deactivate knowledge items and training queries.", "Fully Implemented"),
        ("FR-12", "Atomic Re-Indexing", "Synchronize in-memory vector store and retrain classifier on knowledge commit without restart.", "Fully Implemented"),
        ("FR-13", "Student Feedback", "Allow students to submit Helpful / Unhelpful feedback on assistant responses, persisted to DB.", "Fully Implemented"),
        ("FR-14", "Audit Trail", "Maintain immutable audit log records of all administrative modifications, deletions, and logins.", "Fully Implemented"),
        ("FR-15", "LDAP / SSO Auth", "Authenticate students via institutional @nitdgp.ac.in credentials.", "Planned / Not Impl."),
        ("FR-16", "OCR PDF Ingestion", "Automatically parse scanned administrative circular PDFs via OCR into structured knowledge drafts.", "Planned / Not Impl."),
    ]

    tbl_fr = doc.add_table(rows=len(fr_data)+1, cols=4)
    tbl_fr.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_fr.autofit = False

    headers = ["ID", "Subsystem", "Functional Requirement Description", "Status"]
    col_widths = [Inches(0.8), Inches(1.5), Inches(3.0), Inches(1.2)]

    for c_idx, (h_text, w) in enumerate(zip(headers, col_widths)):
        cell = tbl_fr.cell(0, c_idx)
        cell.width = w
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, 80, 80, 100, 100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, row in enumerate(fr_data, start=1):
        bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, (val, w) in enumerate(zip(row, col_widths)):
            cell = tbl_fr.cell(r_idx, c_idx)
            cell.width = w
            set_cell_background(cell, bg)
            set_cell_margins(cell, 60, 60, 80, 80)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(30, 41, 59)
            if c_idx == 3 and "Fully" in val:
                r.bold = True
                r.font.color.rgb = RGBColor(5, 150, 105)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # --------------------------------------------------------------------------
    # 9. NON-FUNCTIONAL REQUIREMENTS
    # --------------------------------------------------------------------------
    add_section_heading(doc, "9. Non-Functional Requirements & Design Targets", level=1)
    doc.add_paragraph(
        "• Reliability: Zero-downtime dual-mode fallback architecture ensuring full offline operability.\n"
        "• Factual Grounding: Programmatic zero-hallucination guarantee derived from pre-retrieval threshold gating.\n"
        "• Security: PBKDF2 password hashing (260,000 rounds), CSRF synchronizer tokens, sliding-window rate limiters, log sanitizer.\n"
        "• Performance: Retrieval latency <= 5 ms (benchmark: 0.19 ms); Intent classification latency <= 10 ms (benchmark: 1.54 ms).\n"
        "• Usability: High-contrast WCAG AA compliant theme, mobile responsive drawer, accessible keyboard shortcuts.\n"
        "• Maintainability: Modular Flask Application Factory with decoupled services, dependency injection, and clean boundaries."
    )

    # --------------------------------------------------------------------------
    # 10. TECHNICAL ARCHITECTURE
    # --------------------------------------------------------------------------
    add_section_heading(doc, "10. Technical Architecture", level=1)
    doc.add_paragraph(
        "CampusAssist is structured as a decoupled multi-tier architecture. The presentation layer communicates with the "
        "Flask backend via asynchronous HTTPS/JSON REST endpoints. The backend coordinates security validation, intent classification, "
        "dense vector retrieval across an in-memory NumPy store, bounded LLM synthesis, and SQLite WAL persistence."
    )

    # Add Diagram 1
    if os.path.exists("docs/proposal_assets/diagram1_system_architecture.png"):
        doc.add_paragraph().paragraph_format.space_before = Pt(6)
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram1_system_architecture.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 1: High-Level System Architecture of CampusAssist.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 11. FRONTEND WORKFLOW
    # --------------------------------------------------------------------------
    add_section_heading(doc, "11. Frontend Workflow & Component Design", level=1)
    doc.add_paragraph(
        "The frontend operates as a single-page interactive chat interface. Upon loading, it initializes a persistent session UUID "
        "stored in localStorage. When a student enters a question, the interface renders an immediate user message bubble, triggers "
        "a pulsing logo loading state, and submits a POST request to /api/chat. Upon receiving the response, it renders the verified answer, "
        "official portal button, contact authorities, and helpful/unhelpful feedback buttons."
    )

    if os.path.exists("docs/proposal_assets/diagram2_frontend_workflow.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram2_frontend_workflow.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 2: Frontend Interaction Lifecycle and Asynchronous State Transitions.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 12. BACKEND WORKFLOW
    # --------------------------------------------------------------------------
    add_section_heading(doc, "12. Backend Processing Workflow (14-Step Pipeline)", level=1)
    doc.add_paragraph(
        "Every query processed by the application executes through a 14-step pipeline implemented in app/services/chat_service.py:"
    )

    if os.path.exists("docs/proposal_assets/diagram3_backend_workflow.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram3_backend_workflow.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 3: 14-Step Backend Processing Pipeline from Ingestion to Persistence.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 13. KNOWLEDGE REPOSITORY & SEMANTIC RETRIEVAL
    # --------------------------------------------------------------------------
    add_section_heading(doc, "13. Knowledge Repository & Semantic Vector Retrieval", level=1)
    doc.add_paragraph(
        "The Knowledge Repository models institutional procedures into Topics, Intents, and Verified Knowledge Records. "
        "The vector store maintains pre-computed L2-normalized float32 vectors across knowledge records and training exemplars in a contiguous "
        "2D NumPy matrix. Cosine similarity is computed via single matrix dot products: sims = np.dot(self._matrix, q_unit). "
        "Strict filters enforce is_active == 1 and verification_status == 'verified', ensuring unverified drafts are never returned."
    )

    if os.path.exists("docs/proposal_assets/diagram4_retrieval_workflow.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram4_retrieval_workflow.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 4: Vector Generation, Matrix Dot-Product Calculation, and Gating Logic.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 14. CONTROLLED LLM RESPONSE GENERATION
    # --------------------------------------------------------------------------
    add_section_heading(doc, "14. Controlled LLM Response Generation & Grounding Guardrails", level=1)
    doc.add_paragraph(
        "Generative synthesis is governed by strict closed-world prompt engineering. The LLM is provided with system instructions "
        "mandating that the retrieved verified context is the sole source of truth. Under zero-fabrication directives, the model cannot "
        "invent rules, fees, deadlines, or contacts. If API quota is exhausted or internet drops, the DeterministicFallbackProvider "
        "extracts procedure steps directly from SQLite columns without invoking generative APIs."
    )

    if os.path.exists("docs/proposal_assets/diagram5_llm_grounding_workflow.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram5_llm_grounding_workflow.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 5: Bounded Prompt Assembly, Controlled Synthesis, and Offline Fallback.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 15. UNKNOWN-QUERY WORKFLOW
    # --------------------------------------------------------------------------
    add_section_heading(doc, "15. Unknown-Query Workflow & Circuit Breaker Logic", level=1)
    doc.add_paragraph(
        "When student questions score below the 0.50 confidence threshold, the system intercepts execution with a programmatic circuit breaker. "
        "The LLM is completely bypassed, preventing any possibility of hallucination. The student receives polite guidance with official office "
        "locations, while the question is asynchronously written to the unresolved_queries table for administrative review."
    )

    if os.path.exists("docs/proposal_assets/diagram6_unknown_query_triage.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram6_unknown_query_triage.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 6: Circuit Breaker Interception, Admin Review Queue, and Dynamic Re-Indexing.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # --------------------------------------------------------------------------
    # 16. ADMINISTRATOR WORKFLOW
    # --------------------------------------------------------------------------
    add_section_heading(doc, "16. Administrator Workflow & Knowledge Lifecycle Management", level=1)
    doc.add_paragraph(
        "The administrative portal provides staff with full lifecycle management: secure login with brute-force rate limiting, "
        "analytical dashboards, triage queue for unverified queries, knowledge editor, and immutable audit logs. When a rule is verified, "
        "the in-memory vector store purges the cache, generates new embeddings, and rebuilds the dot-product matrix in under 50 ms."
    )

    # --------------------------------------------------------------------------
    # 17. DATABASE ARCHITECTURE
    # --------------------------------------------------------------------------
    add_section_heading(doc, "17. Database Architecture & Relational Schema Specification", level=1)
    doc.add_paragraph(
        "The relational database is implemented in SQLite 3 under Write-Ahead Logging (WAL) mode. The schema comprises 9 tables:\n"
        "• users: Administrator accounts and hashed credentials (PBKDF2).\n"
        "• topics: High-level operational domains (Hostel, Academics, Facilities).\n"
        "• intents: Canonical user objectives under topics (hostel_leave, examination_rules).\n"
        "• knowledge_items: Verified institutional procedures, summaries, keywords, portal URLs, and authorities.\n"
        "• sample_queries: Training questions mapped to intents for semantic search tuning.\n"
        "• conversations: Student session tokens and conversational metadata.\n"
        "• messages: Chronological message turns (role, content, matched knowledge ID, verified flag, feedback).\n"
        "• unresolved_queries: Triage queue for sub-threshold questions awaiting staff verification.\n"
        "• audit_logs: Immutable log of administrative actions, edits, and status changes."
    )

    # --------------------------------------------------------------------------
    # 18. SECURITY, PRIVACY & DATA PROTECTION
    # --------------------------------------------------------------------------
    add_section_heading(doc, "18. Security, Privacy & Data Protection Safeguards", level=1)
    doc.add_paragraph(
        "• Authentication: PBKDF2-HMAC-SHA256 password hashing with 260,000 rounds and random per-user salt.\n"
        "• Anti-CSRF: Synchronizer tokens validated on all state-changing endpoints using timing-safe comparisons.\n"
        "• Rate Limiting: Sliding-window in-memory limiter (60 req/min for chat, 5 req/15 min for admin login).\n"
        "• Input Bounds: Length validation (<= 1500 chars) and regex identifier sanitization (^[a-zA-Z0-9_-]+$).\n"
        "• Log Sanitization: Automatic scrubbing of API keys, tokens, and passwords from logs (logger_sanitizer.py).\n"
        "• Privacy Shield: Internal triage IDs, database keys, and system prompts stripped from student JSON responses."
    )

    # --------------------------------------------------------------------------
    # 19. TESTING & EVALUATION PLAN
    # --------------------------------------------------------------------------
    add_section_heading(doc, "19. Testing, Verification & Quality Assurance Plan", level=1)
    doc.add_paragraph(
        "The automated test suite comprises 20 test modules containing 150 test cases implemented using pytest. "
        "The test suite covers database operations, API routes, classifier accuracy, vector retrieval gating, LLM prompt formatting, "
        "circuit breaker activation, security penetration attacks (SQLi, XSS, CSRF), and multi-turn conversational follow-ups. "
        "Full test execution passed 150/150 tests (100% success rate) in 49.06 seconds."
    )

    # --------------------------------------------------------------------------
    # 20. IMPLEMENTATION STATUS MATRIX
    # --------------------------------------------------------------------------
    add_section_heading(doc, "20. Implementation Status Matrix", level=1)
    doc.add_paragraph(
        "The implementation status of all major project subsystems is summarized below:"
    )

    status_data = [
        ("Student Web UI", "Fully Implemented", "app/templates/chat.html, app/static/js/chat.js", "Responsive chat, mobile drawer, feedback buttons, ARIA labels."),
        ("REST API Router", "Fully Implemented", "app/routes/api_routes.py, admin_routes.py", "9 endpoints, input bounds, rate limiters, privacy shield."),
        ("Relational Database", "Fully Implemented", "app/models/schema.sql, repositories.py", "SQLite WAL mode, 9 tables, composite B-tree indexes."),
        ("Knowledge Repository", "Fully Implemented", "data/seed_knowledge.json, seed_db.py", "3 Topics, 14 canonical Intents, verified demo records."),
        ("Intent Classifier", "Fully Implemented", "app/services/classifier/intent_classifier.py", "Suffix stemming, sublinear TF-IDF, calibrated confidence."),
        ("Vector Embeddings", "Fully Implemented", "app/services/embeddings/gemini_provider.py", "Gemini 768-dim embeddings + local TF-IDF fallback, LRU cache."),
        ("Vector Search Store", "Fully Implemented", "app/services/retrieval/vector_store.py", "NumPy matrix dot product, active/verified filter, sub-ms."),
        ("Context Manager", "Fully Implemented", "app/services/context_manager.py", "Pronoun detection, query expansion, conversational memory."),
        ("Controlled LLM", "Fully Implemented", "app/services/llm/prompt_builder.py, service.py", "Bounded system prompt, Gemini Flash, Deterministic Fallback."),
        ("Circuit Breaker", "Fully Implemented", "app/services/chat_service.py (L309-365)", "Blocks LLM below 0.50 threshold, logs to triage queue."),
        ("Admin Portal & Auth", "Fully Implemented", "app/routes/admin_routes.py, auth_service.py", "PBKDF2 auth, CSRF, triage queue, knowledge CRUD, audit trail."),
        ("Dynamic Re-Indexing", "Fully Implemented", "app/services/knowledge_service.py", "Instant vector store rebuild & classifier retraining on commit."),
        ("Automated Tests", "Fully Implemented", "tests/ (20 test files, 150 cases)", "150 passed in 49.06s (100% pass rate)."),
        ("OCR PDF Ingestion", "Planned / Future", "None (Proposed)", "Automated extraction of circular PDFs via Tesseract OCR."),
        ("LDAP / SSO Auth", "Planned / Future", "None (Proposed)", "Integration with official @nitdgp.ac.in institutional login."),
    ]

    tbl_st = doc.add_table(rows=len(status_data)+1, cols=4)
    tbl_st.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_st.autofit = False

    s_headers = ["Subsystem", "Status", "Verified Source File(s)", "Verification Notes"]
    s_widths = [Inches(1.4), Inches(1.2), Inches(2.2), Inches(1.7)]

    for c_idx, (h_text, w) in enumerate(zip(s_headers, s_widths)):
        cell = tbl_st.cell(0, c_idx)
        cell.width = w
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, 80, 80, 100, 100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, row in enumerate(status_data, start=1):
        bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, (val, w) in enumerate(zip(row, s_widths)):
            cell = tbl_st.cell(r_idx, c_idx)
            cell.width = w
            set_cell_background(cell, bg)
            set_cell_margins(cell, 60, 60, 80, 80)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(30, 41, 59)
            if c_idx == 1 and "Fully" in val:
                r.bold = True
                r.font.color.rgb = RGBColor(5, 150, 105)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # --------------------------------------------------------------------------
    # 21. EXPECTED OUTCOMES
    # --------------------------------------------------------------------------
    add_section_heading(doc, "21. Expected Outcomes & Academic Impact", level=1)
    doc.add_paragraph(
        "• High Procedural Efficiency: Reduces student discovery time from hours of cross-referencing PDFs to seconds.\n"
        "• Elimination of AI Hallucinations: Zero fabrication of institutional rules, deadlines, or fees.\n"
        "• Natural Language Generalization: Bridges the linguistic gap between informal student slang and official administrative text.\n"
        "• Administrative Telemetry: Empowers institute authorities with data on common ambiguities and procedural bottlenecks."
    )

    # --------------------------------------------------------------------------
    # 22. SYSTEM LIMITATIONS
    # --------------------------------------------------------------------------
    add_section_heading(doc, "22. System Limitations & Known Constraints", level=1)
    doc.add_paragraph(
        "• Knowledge Currency: Requires administrative diligence to update knowledge items when institute circulars change.\n"
        "• Semantic Ambiguity: Highly ambiguous single-word queries cannot be resolved without preceding conversational turns.\n"
        "• External API Dependency: Cloud mode depends on Google Gemini API availability (mitigated by offline local fallback).\n"
        "• Scalability Ceiling: In-memory NumPy dot-product engine scales optimally to ~25,000 items before requiring HNSW index migration."
    )

    # --------------------------------------------------------------------------
    # 23. FUTURE SCOPE
    # --------------------------------------------------------------------------
    add_section_heading(doc, "23. Future Scope & Research Directions", level=1)
    doc.add_paragraph(
        "• Institutional SSO Integration: Connecting authentication to official @nitdgp.ac.in LDAP / Google Workspace credentials.\n"
        "• Multi-Modal Circular OCR: Automated PDF ingestion pipeline extracting text from scanned noticeboard images.\n"
        "• Indic Multilingual Support: Incorporating IndicBERT for native support of Hindi, Bengali, and phonetic Hinglish.\n"
        "• ERP Webhook Connectors: Real-time integration with Chanakya ERP for personalized credit and fee status checks.\n"
        "• Omnichannel Messaging: Deploying conversational webhooks on WhatsApp Business API and Telegram."
    )

    # --------------------------------------------------------------------------
    # 24. CONCLUSION
    # --------------------------------------------------------------------------
    add_section_heading(doc, "24. Conclusion", level=1)
    doc.add_paragraph(
        "CampusAssist demonstrates that domain-grounded artificial intelligence can effectively resolve institutional information accessibility "
        "challenges without exposing users to generative hallucinations. By combining hierarchical knowledge modeling, stem-aware classification, "
        "sub-millisecond in-memory vector search, strict closed-world prompt engineering, and an automated circuit breaker, the system delivers "
        "authoritative answers while providing staff with closed-loop knowledge management. The architecture is validated through 150 automated "
        "tests with 100% pass rate, providing a sound foundation for campus-wide deployment."
    )

    # --------------------------------------------------------------------------
    # 25. REFERENCES
    # --------------------------------------------------------------------------
    add_section_heading(doc, "25. References & Consulted Literature", level=1)
    doc.add_paragraph(
        "1. Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.\n"
        "2. Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. Information Processing & Management.\n"
        "3. Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. Foundations in IR.\n"
        "4. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP 2019.\n"
        "5. National Institute of Technology Durgapur. Academic Ordinances, Curriculum & Regulations. https://nitdgp.ac.in\n"
        "6. OWASP Foundation. (2025). OWASP Top 10 for Large Language Model Applications.\n"
        "7. Flask Documentation (v2.3+). Application Factories and Blueprint Modularization. Pallets Projects.\n"
        "8. SQLite Consortium. (2024). Write-Ahead Logging (WAL) Mode Specifications. SQLite.org."
    )

    # --------------------------------------------------------------------------
    # 26. MANDATORY IMPLEMENTATION WALKTHROUGH
    # --------------------------------------------------------------------------
    doc.add_page_break()
    add_section_heading(doc, "26. Mandatory Implementation Walkthrough: A Real CampusAssist Query", level=1)
    doc.add_paragraph(
        "To provide empirical verification of the technical implementation, this section traces an authentic student query from the "
        "Academics domain (completely distinct from Hostel Leave):"
    )

    add_callout(doc, "Walkthrough Query Scenario",
                "• Primary Student Question: 'How do I find examination information?'\n"
                "• Alternate Formulation: 'Where can I find examination rules and schedule?'\n"
                "• Domain: Academics (academics) • Intent: Examination Regulations (examination_rules)\n"
                "• Matched Knowledge Record: 'NIT Durgapur Examination Guidelines & Regulations (Demo Record)' (ID 8)\n"
                "• Authority: Controller of Examinations (CoE) / Academic Section • Portal: https://nitdgp.ac.in/p/academic-curriculum")

    doc.add_paragraph(
        "A. End-to-End Execution Flow:\n"
        "1. Student Input: chat.js captures submission, renders user bubble, initiates loading state.\n"
        "2. REST Ingestion: POST /api/chat received; sliding rate limiter and session ID sanitization executed.\n"
        "3. Validation: validate_input() confirms non-null string under 1500 characters.\n"
        "4. Storage: User message inserted into SQLite messages table under WAL mode.\n"
        "5. Classification: intent_classifier.classify() normalizes text and executes TF-IDF matching (Confidence: 1.0).\n"
        "6. Vectorization: 768-dim float32 vector generated and L2-normalized.\n"
        "7. Vector Dot Search: vector_store.search() executes np.dot(self._matrix, q_unit); Top match score: 1.0000.\n"
        "8. Gating: Score (1.0) >= 0.50 threshold; routes to Grounded Synthesis.\n"
        "9. Prompt Construction: prompt_builder formats system directives + question + Item ID 8 context.\n"
        "10. Synthesis: LLM synthesizes natural instructions on admit cards, reporting time, prohibited calculators, and medical absence.\n"
        "11. Assistant DB Save: Message persisted with is_verified = 1 and matched_knowledge_id = 8.\n"
        "12. Output Delivery: HTTP 200 JSON returned with answer, sources, portal URLs, and latency telemetry (10.12 ms total)."
    )

    # Walkthrough Table
    walk_data = [
        ("1. UI Event Submission", "app/static/js/chat.js", "handleSendMessage()", "L140-175", "Form submit event", "Validates textarea, renders user bubble", "fetch('/api/chat')"),
        ("2. REST Routing & Limits", "app/routes/api_routes.py", "@api_bp.route('/chat')", "L81-107", "JSON payload", "Rate limits, sanitizes session ID", "pipeline.process_chat()"),
        ("3. Input Validation", "app/services/chat_service.py", "validate_input()", "L91-112", "Query string", "Checks null, string type, len <= 1500", "Returns clean_query"),
        ("4. User Message Storage", "app/models/repositories.py", "create_message()", "L153-162", "Session ID, query", "SQLite INSERT into messages", "Returns user_msg_id"),
        ("5. Intent Classification", "app/services/classifier/intent_classifier.py", "classify()", "L164-204", "clean_query", "Stemming, TF-IDF cosine matching", "ClassificationResult (1.0)"),
        ("6. Vector Embeddings", "app/services/embeddings/gemini_provider.py", "get_embedding()", "L40-75", "Query string", "LRU cache, API, L2-normalization", "768-dim unit vector"),
        ("7. Matrix Dot Search", "app/services/retrieval/vector_store.py", "search()", "L113-156", "Unit query vector", "sims = np.dot(M, q_unit), status filter", "RetrievalResult (Score 1.0)"),
        ("8. Sufficiency Check", "app/services/chat_service.py", "process_chat()", "L228-236", "retrieved_items", "Evaluates score >= 0.50", "Routes to Grounded Branch"),
        ("9. Prompt Construction", "app/services/llm/prompt_builder.py", "build_prompt()", "L40-80", "Question, Context", "Assembles strict directives + records", "Returns bounded prompt"),
        ("10. LLM Generation", "app/services/llm/service.py", "generate_grounded_response()", "L110-155", "Bounded prompt", "Gemini 2.5 Flash / Deterministic Fallback", "GroundedResponse"),
        ("11. Assistant DB Save", "app/models/repositories.py", "create_message()", "L254-269", "Response, IDs", "SQLite INSERT into messages (verified=1)", "Returns assistant_msg_id"),
        ("12. Telemetry & JSON", "app/routes/api_routes.py", "chat() response", "L110-133", "result dict", "Packages JSON with telemetry timings", "HTTP 200 JSON"),
    ]

    tbl_wk = doc.add_table(rows=len(walk_data)+1, cols=7)
    tbl_wk.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_wk.autofit = False

    w_headers = ["Stage", "Source File", "Function / API", "Lines", "Input", "Processing", "Output"]
    w_widths = [Inches(0.9), Inches(1.3), Inches(1.1), Inches(0.6), Inches(0.8), Inches(1.1), Inches(0.7)]

    for c_idx, (h_text, w) in enumerate(zip(w_headers, w_widths)):
        cell = tbl_wk.cell(0, c_idx)
        cell.width = w
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, 60, 60, 80, 80)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, row in enumerate(walk_data, start=1):
        bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, (val, w) in enumerate(zip(row, w_widths)):
            cell = tbl_wk.cell(r_idx, c_idx)
            cell.width = w
            set_cell_background(cell, bg)
            set_cell_margins(cell, 50, 50, 60, 60)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(7.5)
            r.font.color.rgb = RGBColor(30, 41, 59)
            if c_idx == 3:
                r.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Embedded Code Panels
    add_section_heading(doc, "Source Code Visual Evidence Panels", level=2)
    doc.add_paragraph("The following code panels capture the exact implementation logic across the primary stages:")

    code_panels = [
        ("docs/proposal_assets/code_stage1_frontend_submission.png", "Figure 7A: Frontend Submission & Event Handling (app/static/js/chat.js: L140-175)."),
        ("docs/proposal_assets/code_stage2_api_endpoint.png", "Figure 7B: Backend REST API Endpoint & Rate Limiter (app/routes/api_routes.py: L81-120)."),
        ("docs/proposal_assets/code_stage3_intent_classification.png", "Figure 7C: Stemmed TF-IDF Intent Classification Engine (app/services/classifier/intent_classifier.py: L164-204)."),
        ("docs/proposal_assets/code_stage4_semantic_retrieval.png", "Figure 7D: Semantic Retrieval Coordination Pipeline (app/services/retrieval/semantic_search.py: L170-208)."),
        ("docs/proposal_assets/code_stage5_vector_store_dotproduct.png", "Figure 7E: In-Memory NumPy Vector Dot Product Search (app/services/retrieval/vector_store.py: L113-156)."),
        ("docs/proposal_assets/code_stage6_grounded_prompt_builder.png", "Figure 7F: Bounded Grounded Prompt Builder (app/services/llm/prompt_builder.py: L40-80)."),
        ("docs/proposal_assets/code_stage7_circuit_breaker_triage.png", "Figure 7G: Zero-Hallucination Circuit Breaker & Triage (app/services/chat_service.py: L309-350)."),
        ("docs/proposal_assets/code_stage8_response_persistence.png", "Figure 7H: Assistant Response Storage & Telemetry Packaging (app/services/chat_service.py: L254-298)."),
    ]

    for img_path, caption in code_panels:
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.add_run().add_picture(img_path, width=Inches(6.2))
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_cap = p_cap.add_run(caption)
            r_cap.italic = True
            r_cap.font.size = Pt(8.2)
            p_cap.paragraph_format.space_after = Pt(6)

    # Add Walkthrough Diagram
    if os.path.exists("docs/proposal_assets/diagram7_walkthrough_trace.png"):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture("docs/proposal_assets/diagram7_walkthrough_trace.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 8: Complete End-to-End Walkthrough Execution Trace.")
        r_cap.italic = True
        r_cap.font.size = Pt(8.5)
        p_cap.paragraph_format.space_after = Pt(10)

    # Save document
    doc.save(OUTPUT_FILE)
    print(f"DOCX Proposal successfully saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_document()
