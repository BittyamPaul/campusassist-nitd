"""
CampusAssist: Automated Academic Proposal PDF Generator
Builds a publication-grade PDF document with numbered canvas ("Page X of Y"),
professional typography, tables, and embedded high-resolution diagrams.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

OUTPUT_PDF = "CampusAssist_Project_Proposal.pdf"

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count (Page X of Y)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Suppress headers/footers on cover page

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header
        self.drawString(54, 11 * 72 - 36, "CampusAssist: AI-Powered Student Assistant for NIT Durgapur — Project Proposal")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)

        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 36, page_text)
        self.drawString(54, 36, "Department of Computer Science & Engineering, NIT Durgapur • Bittyam Paul")
        self.line(54, 46, 8.5 * 72 - 54, 46)

        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    c_navy = colors.HexColor("#0F172A")
    c_blue = colors.HexColor("#1E3A8A")
    c_accent = colors.HexColor("#2563EB")
    c_body = colors.HexColor("#1E293B")
    c_muted = colors.HexColor("#64748B")

    style_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_navy,
        alignment=1,
        spaceAfter=12
    )

    style_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        alignment=1,
        spaceAfter=20
    )

    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_navy,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=c_blue,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_body,
        spaceAfter=6
    )

    style_bullet = ParagraphStyle(
        'BulletDark',
        parent=style_body,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    style_caption = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10.5,
        textColor=c_muted,
        alignment=1,
        spaceBefore=4,
        spaceAfter=10
    )

    style_th = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    style_td = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=c_body
    )

    style_td_status = ParagraphStyle(
        'TableCellStatus',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#059669")
    )

    story = []

    # --------------------------------------------------------------------------
    # 1. COVER PAGE
    # --------------------------------------------------------------------------
    story.append(Spacer(1, 40))
    p_inst = Paragraph(
        "<b>NATIONAL INSTITUTE OF TECHNOLOGY DURGAPUR</b><br/>"
        "<font size=10 color='#475569'>DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING</font>",
        ParagraphStyle('InstHead', alignment=1, leading=16, spaceAfter=40)
    )
    story.append(p_inst)

    story.append(Spacer(1, 30))
    story.append(Paragraph("CAMPUSASSIST", style_title))
    story.append(Paragraph(
        "Domain-Specific AI-Powered Student Assistance Web Application<br/>"
        "with Retrieval-Augmented Grounding & Zero-Hallucination Guardrails",
        style_subtitle
    ))

    story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=20, spaceBefore=10))

    story.append(Paragraph(
        "<b>FINAL YEAR PROJECT PROPOSAL (B.TECH THESIS)</b>",
        ParagraphStyle('DocType', alignment=1, fontName='Helvetica-Bold', fontSize=11, textColor=c_muted, spaceAfter=80)
    ))

    story.append(Spacer(1, 60))

    p_cand = Paragraph(
        "<b>Submitted by:</b><br/>"
        "<b>BITTYAM PAUL</b><br/>"
        "Department of Computer Science & Engineering<br/>"
        "National Institute of Technology Durgapur<br/><br/>"
        "<b>Supervised by:</b><br/>"
        "Project Evaluation Committee<br/>"
        "Academic Year 2026",
        ParagraphStyle('MetaCard', alignment=1, fontName='Helvetica', fontSize=10, leading=14, textColor=c_body)
    )
    story.append(p_cand)

    story.append(PageBreak())

    # --------------------------------------------------------------------------
    # 2. ABSTRACT
    # --------------------------------------------------------------------------
    story.append(Paragraph("2. Abstract", style_h1))
    story.append(Paragraph(
        "Navigating institutional procedures in higher education engineering institutes presents persistent logistical "
        "challenges for students. At the National Institute of Technology Durgapur (NIT Durgapur), official guidelines, "
        "procedural workflows, and administrative circulars governing hostel accommodation, semester academic registrations, "
        "mid-term/end-term examinations, and campus amenities are distributed across physical noticeboards, multi-page PDF "
        "handbooks, and segmented web portals. General-purpose commercial Large Language Models (LLMs) cannot reliably assist "
        "students because they lack internal access to localized NIT Durgapur regulations; when prompted, they frequently invent "
        "nonexistent rules or confuse policies from other institutions.",
        style_body
    ))
    story.append(Paragraph(
        "This project proposes and implements CampusAssist, a domain-specific, hallucination-resistant conversational student assistant. "
        "CampusAssist couples natural language intent classification and in-memory semantic vector search with a strictly controlled "
        "LLM generation layer under a Domain-Grounded Retrieval-Augmented Generation (RAG) architecture. Natural language queries are "
        "mapped into dense semantic vectors to identify underlying topics and intents, retrieving human-verified institutional records. "
        "If retrieved information satisfies statistical confidence thresholds (>= 0.50), an LLM synthesizes a grounded response citing "
        "official authorities and portal URLs. Conversely, if no verified record exists, a programmatic circuit breaker intercepts execution, "
        "refusing to fabricate policies and logging the query into an administrative triage queue for staff review.",
        style_body
    ))

    # Abstract Callout Box
    c_data = [[
        Paragraph(
            "<b>Key Academic Contributions & Engineering Innovations:</b><br/>"
            "• <b>Strict Domain Grounding:</b> Elimination of generative hallucination through pre-retrieval threshold gating.<br/>"
            "• <b>Sub-Millisecond Vector Search:</b> Custom in-memory NumPy dot-product engine executing in 0.19 ms.<br/>"
            "• <b>Closed-Loop Knowledge Triage:</b> Automated logging of unknown queries with atomic dynamic re-indexing.<br/>"
            "• <b>Verified Empirical Reliability:</b> 150 automated test cases with 100% pass rate under SQLite WAL mode.",
            style_body
        )
    ]]
    t_call = Table(c_data, colWidths=[500])
    t_call.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('LINELEFT', (0,0), (0,0), 3.0, colors.HexColor("#0F172A")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_call)
    story.append(Spacer(1, 10))

    # --------------------------------------------------------------------------
    # 3. INTRODUCTION & 4. PROBLEM STATEMENT
    # --------------------------------------------------------------------------
    story.append(Paragraph("3. Introduction", style_h1))
    story.append(Paragraph(
        "Modern engineering institutions operate complex multi-tiered administrative structures comprising academic sections, "
        "hall management councils, examination directorates, estate departments, and medical units. At NIT Durgapur, over 5,000 "
        "undergraduate, postgraduate, and doctoral students must interact with these administrative bodies for recurring procedural "
        "requirements throughout their academic journey.",
        style_body
    ))
    story.append(Paragraph(
        "Students frequently encounter significant friction caused by information fragmentation. Official procedural circulars "
        "are distributed across physical caretaker desks, department bulletin boards, hostel registers, and ERP systems (Chanakya). "
        "Furthermore, students formulate questions using conversational slang ('Can I leave the hall tonight?') that fails to match "
        "the formal vocabulary found in official handbooks. General-purpose AI systems (e.g., ChatGPT, Gemini) cannot solve this problem "
        "in an unconstrained state because they lack internal access to localized NIT Durgapur circulars, leading to fabricated rules. "
        "CampusAssist addresses this by establishing a grounded, domain-specific retrieval-augmented architecture.",
        style_body
    ))

    story.append(Paragraph("4. Problem Statement", style_h1))
    story.append(Paragraph(
        "Students at NIT Durgapur encounter difficulty in efficiently locating verified, actionable procedures across key operational areas:",
        style_body
    ))
    story.append(Paragraph("• <b>Hostel Facilities & Rules:</b> Gate passes, parental consent rules, mutual room swap criteria, electrical/water maintenance complaint logging, and curfew rules.", style_bullet))
    story.append(Paragraph("• <b>Academic Registration:</b> Semester registration workflows on the Chanakya ERP portal, elective subject enrollment, fee receipt submission, and late fine regulations.", style_bullet))
    story.append(Paragraph("• <b>Examinations:</b> Mid-term (30 marks) and end-term (50 marks) regulations, admit card downloads, calculator restrictions, medical absence reporting, and supplementary exam rules.", style_bullet))
    story.append(Paragraph("• <b>Attendance Regulations:</b> Minimum 75% classroom attendance requirements, condonation thresholds, and debarment consequences.", style_bullet))
    story.append(Paragraph("• <b>Student Services & Amenities:</b> Central library borrowing rules, Institute Medical Unit access, Wi-Fi configuration, and security lost-and-found helplines.", style_bullet))

    # --------------------------------------------------------------------------
    # 5. OBJECTIVES & 6. PROPOSED SOLUTION
    # --------------------------------------------------------------------------
    story.append(Paragraph("5. Project Objectives", style_h1))
    story.append(Paragraph("1. Develop an Accessible Conversational Web Interface with zero client compilation.", style_bullet))
    story.append(Paragraph("2. Centralize Verified Institutional Information in a relational Knowledge Repository.", style_bullet))
    story.append(Paragraph("3. Implement Semantic Intent Identification capable of recognizing student goals across arbitrary slang.", style_bullet))
    story.append(Paragraph("4. Realize Sub-Millisecond Vector Retrieval utilizing vectorized NumPy matrix dot products.", style_bullet))
    story.append(Paragraph("5. Enforce Factual Grounding via bounded system prompt engineering.", style_bullet))
    story.append(Paragraph("6. Implement a Zero-Hallucination Circuit Breaker intercepting sub-threshold queries (< 0.50).", style_bullet))
    story.append(Paragraph("7. Provide Authorized Administrative Knowledge Management with dynamic in-memory re-indexing.", style_bullet))
    story.append(Paragraph("8. Ensure High Availability & Offline Resilience with local TF-IDF and deterministic fallbacks.", style_bullet))

    story.append(Paragraph("6. Proposed Solution & Core Philosophy", style_h1))
    story.append(Paragraph(
        "CampusAssist enforces the pipeline: <b>Student Query -> Intent Classification -> Semantic Search -> Verified Knowledge Repository -> Controlled LLM -> Grounded Response</b>. "
        "For example, queries such as <i>'How can I apply for hostel leave?'</i>, <i>'I want to go home for two days'</i>, and <i>'Can I leave the hostel this weekend?'</i> "
        "all map semantically to Topic: <b>Hostel</b> and Intent: <b>Hostel Leave</b>, retrieving the authoritative warden/caretaker procedure rather than relying on exact string matching.",
        style_body
    ))

    # --------------------------------------------------------------------------
    # 7. SYSTEM SCOPE & 8. FUNCTIONAL REQUIREMENTS
    # --------------------------------------------------------------------------
    story.append(Paragraph("7. System Scope", style_h1))
    story.append(Paragraph(
        "<b>In-Scope Capabilities (Implemented):</b> Multi-turn chat with session persistence, semantic retrieval across 14 intents, "
        "Gemini 2.5/1.5 Flash grounded answer generation, deterministic offline fallback, circuit breaker triage queue, secure admin portal with PBKDF2 auth, "
        "dynamic in-memory re-indexing, and 150 automated test cases with 100% pass rate.<br/>"
        "<b>Out-of-Scope Capabilities (Planned Future Scope):</b> Centralized campus LDAP / SSO student login, automated circular OCR PDF parsing, "
        "and multilingual phonetic Hinglish/Benglish translation.",
        style_body
    ))

    story.append(Paragraph("8. Functional Requirements", style_h1))
    
    fr_rows = [
        [Paragraph("<b>ID</b>", style_th), Paragraph("<b>Subsystem</b>", style_th), Paragraph("<b>Requirement Description</b>", style_th), Paragraph("<b>Status</b>", style_th)],
        [Paragraph("FR-01", style_td), Paragraph("Student Chat UI", style_td), Paragraph("Responsive web chat UI supporting text input, markdown rendering, touch/keyboard navigation.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-02", style_td), Paragraph("Rate Limiting", style_td), Paragraph("Sliding-window rate limits (60 req/min for chat, 5 req/15 min for login) to prevent abuse.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-03", style_td), Paragraph("Input Validation", style_td), Paragraph("Validate query bounds (non-empty, string type, maximum 1500 characters) with sanitized errors.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-04", style_td), Paragraph("Intent Classification", style_td), Paragraph("Classify student questions into institutional Topics and Intents with calibrated probability scoring.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-05", style_td), Paragraph("Vector Embedding", style_td), Paragraph("Generate 768-dimensional float32 semantic vectors with bounded LRU memory caching.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-06", style_td), Paragraph("Semantic Search", style_td), Paragraph("In-memory dot-product cosine similarity search filtered strictly by active and verified status.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-07", style_td), Paragraph("Multi-Turn Memory", style_td), Paragraph("Disambiguate follow-up questions using prior conversational turns to maintain context continuity.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-08", style_td), Paragraph("Grounded Synthesis", style_td), Paragraph("Synthesize responses strictly bounded by retrieved verified context with zero hallucination.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-09", style_td), Paragraph("Circuit Breaker", style_td), Paragraph("Intercept queries scoring below 0.50 similarity, block LLM invocation, and log to triage queue.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-10", style_td), Paragraph("Admin Auth & RBAC", style_td), Paragraph("Secure admin portal via salted PBKDF2 password hashing (260,000 rounds) and session tokens.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-11", style_td), Paragraph("Knowledge CRUD", style_td), Paragraph("Allow authorized staff to create, edit, verify, activate/deactivate knowledge items and training queries.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-12", style_td), Paragraph("Atomic Re-Indexing", style_td), Paragraph("Synchronize in-memory vector store and retrain classifier on knowledge commit without restart.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-13", style_td), Paragraph("Student Feedback", style_td), Paragraph("Allow students to submit Helpful / Unhelpful feedback on assistant responses, persisted to DB.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-14", style_td), Paragraph("Audit Trail", style_td), Paragraph("Maintain immutable audit log records of all administrative modifications, deletions, and logins.", style_td), Paragraph("Fully Implemented", style_td_status)],
        [Paragraph("FR-15", style_td), Paragraph("LDAP / SSO Auth", style_td), Paragraph("Authenticate students via institutional @nitdgp.ac.in credentials.", style_td), Paragraph("Planned / Future", style_td)],
        [Paragraph("FR-16", style_td), Paragraph("OCR PDF Ingestion", style_td), Paragraph("Automatically parse scanned administrative circular PDFs via OCR into structured knowledge drafts.", style_td), Paragraph("Planned / Future", style_td)],
    ]

    t_fr = Table(fr_rows, colWidths=[45, 95, 260, 100])
    t_fr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ]))
    story.append(t_fr)
    story.append(Spacer(1, 10))

    # --------------------------------------------------------------------------
    # 9. NON-FUNCTIONAL REQUIREMENTS & 10. ARCHITECTURE
    # --------------------------------------------------------------------------
    story.append(Paragraph("9. Non-Functional Requirements", style_h1))
    story.append(Paragraph(
        "• <b>Reliability:</b> Zero-downtime dual-mode fallback architecture ensuring full offline operability.<br/>"
        "• <b>Factual Grounding:</b> Programmatic zero-hallucination guarantee derived from pre-retrieval threshold gating.<br/>"
        "• <b>Security:</b> PBKDF2 password hashing (260,000 rounds), CSRF synchronizer tokens, sliding-window rate limiters, log sanitizer.<br/>"
        "• <b>Performance:</b> Retrieval latency <= 5 ms (benchmark: 0.19 ms); Intent classification latency <= 10 ms (benchmark: 1.54 ms).<br/>"
        "• <b>Usability:</b> High-contrast WCAG AA compliant theme, mobile responsive drawer, accessible keyboard shortcuts.<br/>"
        "• <b>Maintainability:</b> Modular Flask Application Factory with decoupled services and dependency injection.",
        style_body
    ))

    story.append(Paragraph("10. Technical Architecture", style_h1))
    story.append(Paragraph(
        "CampusAssist is structured as a decoupled three-tier architecture: Presentation Layer (HTML5/CSS3/ES6 JS), "
        "Application Layer (Python 3.11, Flask, scikit-learn, NumPy, Google Gemini API), and Data Layer (SQLite 3 WAL mode with composite indexes).",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram1_system_architecture.png"):
        story.append(Image("docs/proposal_assets/diagram1_system_architecture.png", width=490, height=275))
        story.append(Paragraph("Figure 1: High-Level System Architecture of CampusAssist.", style_caption))

    # --------------------------------------------------------------------------
    # 11. FRONTEND WORKFLOW & 12. BACKEND WORKFLOW
    # --------------------------------------------------------------------------
    story.append(Paragraph("11. Frontend Workflow & Component Design", style_h1))
    story.append(Paragraph(
        "The frontend operates as an asynchronous single-page application. When a query is entered, the UI renders the user bubble, "
        "displays a pulsing mascot typing indicator, and dispatches a JSON POST to /api/chat. Upon receipt, it formats the answer with "
        "verified badges, authority contacts, official portal links, and feedback actions.",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram2_frontend_workflow.png"):
        story.append(Image("docs/proposal_assets/diagram2_frontend_workflow.png", width=490, height=265))
        story.append(Paragraph("Figure 2: Frontend Interaction Lifecycle and Asynchronous State Transitions.", style_caption))

    story.append(Paragraph("12. Backend Processing Workflow (14-Step Pipeline)", style_h1))
    story.append(Paragraph(
        "Every student question executes through a 14-step pipeline: (1) Route ingestion, (2) Input bounds check, (3) Session UUID setup, "
        "(4) Student message DB insert, (5) Query normalization & stemming, (6) Intent & topic classification, (7) Dense embedding generation, "
        "(8) Vector dot-product search, (8b) Contextual follow-up evaluation, (9) Threshold gating (>= 0.50), (10) Sufficiency check, "
        "(11) Bounded prompt assembly, (12) Controlled LLM synthesis, (13) Assistant message DB insert, and (14) Structured JSON return.",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram3_backend_workflow.png"):
        story.append(Image("docs/proposal_assets/diagram3_backend_workflow.png", width=490, height=325))
        story.append(Paragraph("Figure 3: 14-Step Backend Processing Pipeline from Ingestion to Persistence.", style_caption))

    # --------------------------------------------------------------------------
    # 13. KNOWLEDGE REPOSITORY & 14. CONTROLLED LLM
    # --------------------------------------------------------------------------
    story.append(Paragraph("13. Knowledge Repository & Semantic Vector Retrieval", style_h1))
    story.append(Paragraph(
        "Knowledge entries are indexed into unit-normalized 768-dimensional float32 vectors. Cosine similarity is computed via single C-level "
        "BLAS dot products: <code>sims = np.dot(self._matrix, q_unit)</code>. Strict filtering enforces <code>is_active == 1</code> and "
        "<code>verification_status == 'verified'</code>, preventing draft contamination.",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram4_retrieval_workflow.png"):
        story.append(Image("docs/proposal_assets/diagram4_retrieval_workflow.png", width=490, height=265))
        story.append(Paragraph("Figure 4: Vector Generation, Matrix Dot-Product Calculation, and Gating Logic.", style_caption))

    story.append(Paragraph("14. Controlled LLM Response Generation & Grounding Guardrails", style_h1))
    story.append(Paragraph(
        "PromptBuilder constructs closed-world prompts where the retrieved verified text is designated as the sole source of truth. "
        "Under zero-fabrication directives, the model cannot invent regulations or contacts. Under network failure, the DeterministicFallbackProvider "
        "formats database columns directly without calling external APIs.",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram5_llm_grounding_workflow.png"):
        story.append(Image("docs/proposal_assets/diagram5_llm_grounding_workflow.png", width=490, height=290))
        story.append(Paragraph("Figure 5: Bounded Prompt Assembly, Controlled Synthesis, and Offline Fallback.", style_caption))

    # --------------------------------------------------------------------------
    # 15. UNKNOWN QUERY & 16. ADMIN WORKFLOW
    # --------------------------------------------------------------------------
    story.append(Paragraph("15. Unknown-Query Workflow & Circuit Breaker Logic", style_h1))
    story.append(Paragraph(
        "Queries with retrieval similarity < 0.50 trigger the programmatic circuit breaker. Generative synthesis is aborted, a friendly contact "
        "notice is returned, and the query is queued in the <code>unresolved_queries</code> table for staff triage.",
        style_body
    ))

    if os.path.exists("docs/proposal_assets/diagram6_unknown_query_triage.png"):
        story.append(Image("docs/proposal_assets/diagram6_unknown_query_triage.png", width=490, height=290))
        story.append(Paragraph("Figure 6: Circuit Breaker Interception, Admin Review Queue, and Dynamic Re-Indexing.", style_caption))

    story.append(Paragraph("16. Administrator Workflow & Knowledge Lifecycle Management", style_h1))
    story.append(Paragraph(
        "Staff access the admin portal via rate-limited PBKDF2 authentication to inspect unresolved queries, add or edit verified knowledge, "
        "and review audit trails. When an administrator commits a verified item, dynamic re-indexing rebuilds the in-memory vector store in under 50 ms.",
        style_body
    ))

    # --------------------------------------------------------------------------
    # 17. DATABASE ARCHITECTURE & 18. SECURITY
    # --------------------------------------------------------------------------
    story.append(Paragraph("17. Database Architecture & Relational Schema", style_h1))
    story.append(Paragraph(
        "The relational schema comprises 9 SQLite tables configured with Write-Ahead Logging (WAL) and foreign keys:<br/>"
        "• <code>users</code>: Admin accounts with PBKDF2 hashed credentials.<br/>"
        "• <code>topics</code>: High-level operational domains (Hostel, Academics, Facilities).<br/>"
        "• <code>intents</code>: Specific user goals under topics.<br/>"
        "• <code>knowledge_items</code>: Authoritative verified procedures and metadata.<br/>"
        "• <code>sample_queries</code>: Exemplar questions for semantic matching.<br/>"
        "• <code>conversations</code>: Session tracking.<br/>"
        "• <code>messages</code>: Chronological conversational turns with verified flags and feedback.<br/>"
        "• <code>unresolved_queries</code>: Triage queue for sub-threshold questions.<br/>"
        "• <code>audit_logs</code>: Immutable log of administrative actions and edits.",
        style_body
    ))

    story.append(Paragraph("18. Security, Privacy & Data Protection Safeguards", style_h1))
    story.append(Paragraph(
        "• Passwords hashed with PBKDF2-HMAC-SHA256 (260,000 iterations).<br/>"
        "• CSRF synchronizer tokens validated with timing-safe comparison.<br/>"
        "• Sliding-window rate limiters (60 req/min chat, 5 req/15 min login).<br/>"
        "• Input length bounds (1500 chars) and regex identifier sanitization.<br/>"
        "• Log scrubbing of API keys, bearer tokens, and credentials.<br/>"
        "• Student privacy shield redacting internal triage IDs from responses.",
        style_body
    ))

    # --------------------------------------------------------------------------
    # 19. TESTING & 20. IMPLEMENTATION STATUS
    # --------------------------------------------------------------------------
    story.append(Paragraph("19. Testing, Verification & Quality Assurance Plan", style_h1))
    story.append(Paragraph(
        "The automated test suite comprises 20 test modules containing 150 test cases implemented using pytest. "
        "The test suite covers database operations, API routes, classifier accuracy, vector retrieval gating, LLM prompt formatting, "
        "circuit breaker activation, security penetration attacks (SQLi, XSS, CSRF), and multi-turn conversational follow-ups. "
        "Full test execution passed 150/150 tests (100% success rate) in 49.06 seconds.",
        style_body
    ))

    story.append(Paragraph("20. Implementation Status Matrix", style_h1))

    st_rows = [
        [Paragraph("<b>Subsystem</b>", style_th), Paragraph("<b>Status</b>", style_th), Paragraph("<b>Verified Source File(s)</b>", style_th), Paragraph("<b>Verification Notes</b>", style_th)],
        [Paragraph("Student Web UI", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/templates/chat.html, app/static/js/chat.js", style_td), Paragraph("Responsive chat, mobile drawer, feedback buttons, ARIA labels.", style_td)],
        [Paragraph("REST API Router", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/routes/api_routes.py, admin_routes.py", style_td), Paragraph("9 endpoints, input bounds, rate limiters, privacy shield.", style_td)],
        [Paragraph("Relational DB", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/models/schema.sql, repositories.py", style_td), Paragraph("SQLite WAL mode, 9 tables, composite B-tree indexes.", style_td)],
        [Paragraph("Knowledge Repo", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("data/seed_knowledge.json, seed_db.py", style_td), Paragraph("3 Topics, 14 canonical Intents, verified demo records.", style_td)],
        [Paragraph("Intent Classifier", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/classifier/intent_classifier.py", style_td), Paragraph("Suffix stemming, sublinear TF-IDF, calibrated confidence.", style_td)],
        [Paragraph("Vector Embeddings", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/embeddings/gemini_provider.py", style_td), Paragraph("Gemini 768-dim embeddings + local TF-IDF fallback, LRU cache.", style_td)],
        [Paragraph("Vector Search Store", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/retrieval/vector_store.py", style_td), Paragraph("NumPy matrix dot product, active/verified filter, sub-ms.", style_td)],
        [Paragraph("Context Manager", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/context_manager.py", style_td), Paragraph("Pronoun detection, query expansion, conversational memory.", style_td)],
        [Paragraph("Controlled LLM", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/llm/prompt_builder.py, service.py", style_td), Paragraph("Bounded system prompt, Gemini Flash, Deterministic Fallback.", style_td)],
        [Paragraph("Circuit Breaker", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/chat_service.py (L309-365)", style_td), Paragraph("Blocks LLM below 0.50 threshold, logs to triage queue.", style_td)],
        [Paragraph("Admin Portal & Auth", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/routes/admin_routes.py, auth_service.py", style_td), Paragraph("PBKDF2 auth, CSRF, triage queue, knowledge CRUD, audit trail.", style_td)],
        [Paragraph("Dynamic Re-Index", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("app/services/knowledge_service.py", style_td), Paragraph("Instant vector store rebuild & classifier retraining on commit.", style_td)],
        [Paragraph("Automated Tests", style_td), Paragraph("Fully Implemented", style_td_status), Paragraph("tests/ (20 test files, 150 cases)", style_td), Paragraph("150 passed in 49.06s (100% pass rate).", style_td)],
        [Paragraph("OCR PDF Ingestion", style_td), Paragraph("Planned / Future", style_td), Paragraph("None (Proposed)", style_td), Paragraph("Automated extraction of circular PDFs via Tesseract OCR.", style_td)],
        [Paragraph("LDAP / SSO Auth", style_td), Paragraph("Planned / Future", style_td), Paragraph("None (Proposed)", style_td), Paragraph("Integration with official @nitdgp.ac.in institutional login.", style_td)],
    ]

    t_st = Table(st_rows, colWidths=[90, 85, 175, 150])
    t_st.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ]))
    story.append(t_st)
    story.append(Spacer(1, 10))

    # --------------------------------------------------------------------------
    # 21. OUTCOMES, 22. LIMITATIONS, 23. FUTURE, 24. CONCLUSION, 25. REFS
    # --------------------------------------------------------------------------
    story.append(Paragraph("21. Expected Outcomes", style_h1))
    story.append(Paragraph(
        "• High Procedural Efficiency: Reduces student discovery time from hours to seconds.<br/>"
        "• Elimination of AI Hallucinations: Zero fabrication of institutional rules, deadlines, or fees.<br/>"
        "• Natural Language Generalization: Bridges the gap between informal student slang and official administrative text.<br/>"
        "• Administrative Telemetry: Empowers authorities with data on procedural ambiguities.",
        style_body
    ))

    story.append(Paragraph("22. System Limitations", style_h1))
    story.append(Paragraph(
        "• Knowledge Currency: Requires administrative diligence to update records when regulations change.<br/>"
        "• Semantic Ambiguity: Single-word ambiguous queries require prior conversational turns to resolve.<br/>"
        "• External API Dependency: Cloud mode depends on Gemini API availability (mitigated by offline local fallback).<br/>"
        "• Scalability Threshold: In-memory dot products scale to ~25,000 records before requiring HNSW index migration.",
        style_body
    ))

    story.append(Paragraph("23. Future Scope", style_h1))
    story.append(Paragraph(
        "• Institutional SSO Integration with official @nitdgp.ac.in LDAP credentials.<br/>"
        "• Multi-Modal Circular OCR parsing scanned noticeboard circulars.<br/>"
        "• Indic Multilingual Support for Hindi, Bengali, and phonetic Hinglish.<br/>"
        "• ERP Webhook Connectors for personalized Chanakya grade and attendance checks.<br/>"
        "• Omnichannel Messaging via WhatsApp and Telegram bot webhooks.",
        style_body
    ))

    story.append(Paragraph("24. Conclusion", style_h1))
    story.append(Paragraph(
        "CampusAssist demonstrates that domain-grounded artificial intelligence can effectively resolve institutional information accessibility "
        "challenges without exposing users to generative hallucinations. By combining hierarchical knowledge modeling, stem-aware classification, "
        "sub-millisecond in-memory vector search, strict closed-world prompt engineering, and an automated circuit breaker, the system delivers "
        "authoritative answers while providing staff with closed-loop knowledge management. The architecture is validated through 150 automated "
        "tests with 100% pass rate, providing a sound foundation for campus-wide deployment.",
        style_body
    ))

    story.append(Paragraph("25. References & Consulted Literature", style_h1))
    story.append(Paragraph(
        "1. Lewis, P., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020.<br/>"
        "2. Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. Information Processing & Management.<br/>"
        "3. Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. Foundations in IR.<br/>"
        "4. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP 2019.<br/>"
        "5. National Institute of Technology Durgapur. Academic Ordinances, Curriculum & Regulations. https://nitdgp.ac.in<br/>"
        "6. OWASP Foundation. (2025). OWASP Top 10 for Large Language Model Applications.<br/>"
        "7. Flask Documentation (v2.3+). Application Factories and Blueprint Modularization. Pallets Projects.<br/>"
        "8. SQLite Consortium. (2024). Write-Ahead Logging (WAL) Mode Specifications. SQLite.org.",
        style_body
    ))

    # --------------------------------------------------------------------------
    # 26. MANDATORY IMPLEMENTATION WALKTHROUGH
    # --------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph("26. Mandatory Implementation Walkthrough: A Real CampusAssist Query", style_h1))
    story.append(Paragraph(
        "To provide empirical verification of the technical implementation, this section traces an authentic student query from the "
        "Academics domain (completely distinct from Hostel Leave):<br/>"
        "• <b>Primary Student Question:</b> 'How do I find examination information?'<br/>"
        "• <b>Alternate Formulation:</b> 'Where can I find examination rules and schedule?'<br/>"
        "• <b>Domain:</b> Academics (academics) • <b>Intent:</b> Examination Regulations (examination_rules)<br/>"
        "• <b>Matched Knowledge Record:</b> 'NIT Durgapur Examination Guidelines & Regulations (Demo Record)' (ID 8)<br/>"
        "• <b>Authority:</b> Controller of Examinations (CoE) / Academic Section • <b>Portal:</b> https://nitdgp.ac.in/p/academic-curriculum",
        style_body
    ))

    wk_rows = [
        [Paragraph("<b>Stage</b>", style_th), Paragraph("<b>Source File</b>", style_th), Paragraph("<b>Function / API</b>", style_th), Paragraph("<b>Lines</b>", style_th), Paragraph("<b>Input</b>", style_th), Paragraph("<b>Processing</b>", style_th), Paragraph("<b>Output</b>", style_th)],
        [Paragraph("1. UI Submission", style_td), Paragraph("app/static/js/chat.js", style_td), Paragraph("handleSendMessage()", style_td), Paragraph("L140-175", style_td_status), Paragraph("Form submit", style_td), Paragraph("Validates textarea, renders bubble", style_td), Paragraph("fetch('/api/chat')", style_td)],
        [Paragraph("2. REST Routing", style_td), Paragraph("app/routes/api_routes.py", style_td), Paragraph("@api_bp.route('/chat')", style_td), Paragraph("L81-107", style_td_status), Paragraph("JSON payload", style_td), Paragraph("Rate limits, sanitizes session ID", style_td), Paragraph("process_chat()", style_td)],
        [Paragraph("3. Validation", style_td), Paragraph("app/services/chat_service.py", style_td), Paragraph("validate_input()", style_td), Paragraph("L91-112", style_td_status), Paragraph("Query string", style_td), Paragraph("Checks null, string type, len <= 1500", style_td), Paragraph("clean_query", style_td)],
        [Paragraph("4. User DB Save", style_td), Paragraph("app/models/repositories.py", style_td), Paragraph("create_message()", style_td), Paragraph("L153-162", style_td_status), Paragraph("Session ID, query", style_td), Paragraph("SQLite INSERT into messages", style_td), Paragraph("user_msg_id", style_td)],
        [Paragraph("5. Classification", style_td), Paragraph("app/services/classifier/intent_classifier.py", style_td), Paragraph("classify()", style_td), Paragraph("L164-204", style_td_status), Paragraph("clean_query", style_td), Paragraph("Stemming, TF-IDF cosine matching", style_td), Paragraph("Conf: 1.0", style_td)],
        [Paragraph("6. Embeddings", style_td), Paragraph("app/services/embeddings/gemini_provider.py", style_td), Paragraph("get_embedding()", style_td), Paragraph("L40-75", style_td_status), Paragraph("Query string", style_td), Paragraph("LRU cache, API, L2-normalization", style_td), Paragraph("768-dim unit vec", style_td)],
        [Paragraph("7. Dot Search", style_td), Paragraph("app/services/retrieval/vector_store.py", style_td), Paragraph("search()", style_td), Paragraph("L113-156", style_td_status), Paragraph("Unit query vector", style_td), Paragraph("sims = np.dot(M, q_unit), filter", style_td), Paragraph("Score: 1.0", style_td)],
        [Paragraph("8. Sufficiency", style_td), Paragraph("app/services/chat_service.py", style_td), Paragraph("process_chat()", style_td), Paragraph("L228-236", style_td_status), Paragraph("retrieved_items", style_td), Paragraph("Evaluates score >= 0.50", style_td), Paragraph("Grounded Branch", style_td)],
        [Paragraph("9. Prompt Build", style_td), Paragraph("app/services/llm/prompt_builder.py", style_td), Paragraph("build_prompt()", style_td), Paragraph("L40-80", style_td_status), Paragraph("Question, Context", style_td), Paragraph("Assembles directives + records", style_td), Paragraph("Bounded prompt", style_td)],
        [Paragraph("10. LLM Synth", style_td), Paragraph("app/services/llm/service.py", style_td), Paragraph("generate_grounded_response()", style_td), Paragraph("L110-155", style_td_status), Paragraph("Bounded prompt", style_td), Paragraph("Gemini 2.5 Flash / Fallback", style_td), Paragraph("GroundedResponse", style_td)],
        [Paragraph("11. Asst DB Save", style_td), Paragraph("app/models/repositories.py", style_td), Paragraph("create_message()", style_td), Paragraph("L254-269", style_td_status), Paragraph("Response, IDs", style_td), Paragraph("SQLite INSERT (verified=1)", style_td), Paragraph("asst_msg_id", style_td)],
        [Paragraph("12. JSON Output", style_td), Paragraph("app/routes/api_routes.py", style_td), Paragraph("chat() response", style_td), Paragraph("L110-133", style_td_status), Paragraph("result dict", style_td), Paragraph("Packages telemetry timings", style_td), Paragraph("HTTP 200 JSON", style_td)],
    ]

    t_wk = Table(wk_rows, colWidths=[65, 85, 75, 45, 65, 95, 70])
    t_wk.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ]))
    story.append(t_wk)
    story.append(Spacer(1, 10))

    # Add Walkthrough Code Panels
    story.append(Paragraph("Source Code Implementation Panels", style_h2))

    c_panels = [
        ("docs/proposal_assets/code_stage1_frontend_submission.png", "Figure 7A: Frontend Submission & Event Handling (app/static/js/chat.js: L140-175)."),
        ("docs/proposal_assets/code_stage2_api_endpoint.png", "Figure 7B: Backend REST API Endpoint & Rate Limiter (app/routes/api_routes.py: L81-120)."),
        ("docs/proposal_assets/code_stage3_intent_classification.png", "Figure 7C: Stemmed TF-IDF Intent Classification Engine (app/services/classifier/intent_classifier.py: L164-204)."),
        ("docs/proposal_assets/code_stage4_semantic_retrieval.png", "Figure 7D: Semantic Retrieval Coordination Pipeline (app/services/retrieval/semantic_search.py: L170-208)."),
        ("docs/proposal_assets/code_stage5_vector_store_dotproduct.png", "Figure 7E: In-Memory NumPy Vector Dot Product Search (app/services/retrieval/vector_store.py: L113-156)."),
        ("docs/proposal_assets/code_stage6_grounded_prompt_builder.png", "Figure 7F: Bounded Grounded Prompt Builder (app/services/llm/prompt_builder.py: L40-80)."),
        ("docs/proposal_assets/code_stage7_circuit_breaker_triage.png", "Figure 7G: Zero-Hallucination Circuit Breaker & Triage (app/services/chat_service.py: L309-350)."),
        ("docs/proposal_assets/code_stage8_response_persistence.png", "Figure 7H: Assistant Response Storage & Telemetry Packaging (app/services/chat_service.py: L254-298)."),
    ]

    for img_path, caption in c_panels:
        if os.path.exists(img_path):
            story.append(Image(img_path, width=490, height=210))
            story.append(Paragraph(caption, style_caption))

    # Add Diagram 7
    if os.path.exists("docs/proposal_assets/diagram7_walkthrough_trace.png"):
        story.append(Image("docs/proposal_assets/diagram7_walkthrough_trace.png", width=490, height=285))
        story.append(Paragraph("Figure 8: Complete End-to-End Walkthrough Execution Trace.", style_caption))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Proposal successfully generated at: {OUTPUT_PDF}")

if __name__ == "__main__":
    build_pdf()
