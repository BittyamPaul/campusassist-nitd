import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# -----------------------------------------------------------------------------
# Color Palette & Typography Configuration
# -----------------------------------------------------------------------------
NAVY_DARK    = RGBColor(11, 25, 44)       # #0B192C Primary Header / Brand Dark
BLUE_DEEP    = RGBColor(30, 62, 98)       # #1E3E62 Subheaders / Accents
CRIMSON_NITD = RGBColor(184, 0, 31)       # #B8001F Official NITD Crimson Accent
AZURE_ACCENT = RGBColor(37, 99, 235)      # #2563EB Interactive Tech Azure
EMERALD_OK   = RGBColor(5, 150, 105)      # #059669 Verified / Success Green
AMBER_WARN   = RGBColor(217, 119, 6)      # #D97706 Fallback / Notice Amber
BG_OFFWHITE  = RGBColor(248, 250, 252)    # #F8FAFC Canvas background
CARD_BG      = RGBColor(255, 255, 255)    # #FFFFFF Card background
BORDER_MUTED = RGBColor(226, 232, 240)    # #E2E8F0 Card borders
TEXT_PRIMARY = RGBColor(15, 23, 42)       # #0F172A Main body text
TEXT_MUTED   = RGBColor(100, 116, 139)    # #64748B Secondary / metadata text
WHITE        = RGBColor(255, 255, 255)

FONT_HEADING = "Arial"
FONT_BODY    = "Calibri"

ASSETS_DIR = Path("CampusAssist_Presentation_Assets")

def create_deck():
    prs = Presentation()
    # 16:9 Widescreen standard
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]  # Blank slide

    def add_header(slide, title_text, category_text="CAMPUSASSIST • NIT DURGAPUR"):
        # Header banner shape
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.9))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        # Category / Kicker
        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.name = FONT_HEADING
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = CRIMSON_NITD
        p_cat.space_after = Pt(2)

        # Title
        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.name = FONT_HEADING
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY_DARK

        # Subtle separator line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
        line.fill.solid()
        line.fill.fore_color.rgb = BORDER_MUTED
        line.line.color.rgb = BORDER_MUTED

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=BORDER_MUTED):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
        return shape

    def set_notes(slide, notes_text):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = notes_text

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    # Background full-bleed
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY_DARK
    bg1.line.fill.background()

    # Decorative top bar
    bar1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12))
    bar1.fill.solid()
    bar1.fill.fore_color.rgb = CRIMSON_NITD
    bar1.line.fill.background()

    # Main title content box
    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.933), Inches(4.2))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p = tf1.paragraphs[0]
    p.text = "NATIONAL INSTITUTE OF TECHNOLOGY DURGAPUR"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CRIMSON_NITD
    p.space_after = Pt(14)

    p2 = tf1.add_paragraph()
    p2.text = "CampusAssist: AI-Powered Student Assistant"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(36)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_after = Pt(10)

    p3 = tf1.add_paragraph()
    p3.text = "Domain-Specific Conversational Intelligence via Verified Institutional Knowledge Grounding & Semantic Retrieval"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(17)
    p3.font.color.rgb = RGBColor(203, 213, 225)
    p3.space_after = Pt(28)

    # Metadata card inside title
    p4 = tf1.add_paragraph()
    p4.text = "Presented by: Bittyam Paul   |   Department of Computer Science & Engineering"
    p4.font.name = FONT_BODY
    p4.font.size = Pt(14)
    p4.font.bold = True
    p4.font.color.rgb = WHITE
    p4.space_after = Pt(4)

    p5 = tf1.add_paragraph()
    p5.text = "Capstone Engineering Project Proposal   •   Academic Session 2025–2026   •   NIT Durgapur, West Bengal"
    p5.font.name = FONT_BODY
    p5.font.size = Pt(12)
    p5.font.color.rgb = RGBColor(148, 163, 184)

    set_notes(s1, (
        "Good morning, respected professor and project review committee. "
        "I am Bittyam Paul from the Department of Computer Science & Engineering at NIT Durgapur. "
        "Today, I am presenting 'CampusAssist'—a domain-specific AI student assistant engineered specifically "
        "for National Institute of Technology Durgapur. "
        "CampusAssist is not a generic conversational bot; it is a grounded conversational retrieval system "
        "designed to deliver factually verified institutional information without hallucinations. "
        "Over the next 15 minutes, I will walk you through the problem, our architecture, the retrieval pipeline, "
        "actual code implementations, and live runtime evidence."
    ))

    # =========================================================================
    # SLIDE 2: Problem Statement and Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Problem Statement & Motivation", "Context & Problem Definition")

    cards_data_s2 = [
        ("Fragmented Institutional Data", 
         "Critical campus regulations—hostel gate passes, academic registration calendars, examination handbooks, and scholarship guidelines—are dispersed across disparate portals, noticeboards, and multi-page PDFs.",
         "High Information Discovery Latency"),
        ("Repeated Manual Inquiries",
         "Hostel offices, administrative desks, and department staff face recurrent, high-volume repetitive queries regarding routine regulations, diverting resources from critical operations.",
         "Administrative Overhead"),
        ("Phrasing Variance in Student Queries",
         "Students express the identical underlying need using completely distinct terminology (e.g., 'apply for gate pass' vs 'can I go home this weekend?'). Traditional keyword search fails on semantic variance.",
         "Keyword Matching Fragility"),
        ("Hallucination Risk of Generic LLMs",
         "Public LLMs (ChatGPT, Gemini) produce plausible yet fabricated policies, outdated fees, and fictitious deadlines when queried on institutional rules due to a lack of factual grounding.",
         "Unacceptable Reliability Deficit")
    ]

    col_w = Inches(2.75)
    gap = Inches(0.24)
    top_pos = Inches(1.7)
    card_h = Inches(5.1)

    for i, (title, desc, tag) in enumerate(cards_data_s2):
        left_pos = Inches(0.8) + i * (col_w + gap)
        add_card(s2, left_pos, top_pos, col_w, card_h)
        
        tbox = s2.shapes.add_textbox(left_pos + Inches(0.2), top_pos + Inches(0.25), col_w - Inches(0.4), card_h - Inches(0.5))
        tf = tbox.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = f"0{i+1}"
        p.font.name = FONT_HEADING
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = CRIMSON_NITD
        p.space_after = Pt(8)

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(15)
        p2.font.bold = True
        p2.font.color.rgb = NAVY_DARK
        p2.space_after = Pt(10)

        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.name = FONT_BODY
        p3.font.size = Pt(12)
        p3.font.color.rgb = TEXT_MUTED
        p3.space_after = Pt(16)

        p4 = tf.add_paragraph()
        p4.text = f"Impact: {tag}"
        p4.font.name = FONT_BODY
        p4.font.size = Pt(11)
        p4.font.bold = True
        p4.font.color.rgb = BLUE_DEEP

    set_notes(s2, (
        "Let us examine why existing methods fall short at NIT Durgapur. "
        "First, vital policies are scattered across the Chanakya portal, website notices, and academic handbooks. "
        "Second, administrative offices face repetitive queues for basic routine questions. "
        "Third, keyword search engines require students to know exact administrative jargon. "
        "Finally, simply connecting students to a generic LLM is dangerous: general models hallucinate rules and fees. "
        "These four challenges define the core engineering motivation for CampusAssist."
    ))

    # =========================================================================
    # SLIDE 3: Proposed Solution and Objectives
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Proposed Solution & Core Principles", "System Design & Objectives")

    # Flow banner across top
    flow_box = add_card(s3, Inches(0.8), Inches(1.65), Inches(11.733), Inches(1.3), bg_color=NAVY_DARK, border_color=NAVY_DARK)
    tbox = s3.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(11.333), Inches(1.1))
    tf = tbox.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = "CORE ARCHITECTURAL PRINCIPLE"
    p.font.name = FONT_HEADING
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CRIMSON_NITD
    p.space_after = Pt(4)

    p2 = tf.add_paragraph()
    p2.text = "Different Questions  ➔  Topic & Intent Classification  ➔  Semantic Search  ➔  Verified NIT Knowledge  ➔  Controlled LLM  ➔  Grounded Response"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(14)
    p2.font.bold = True
    p2.font.color.rgb = WHITE

    # 4 Core Objectives
    objs = [
        ("Centralized Verified Knowledge", "Structure institutional guidelines into authoritative, versioned records verified by campus administrators.", AZURE_ACCENT),
        ("Intent-Aware Dual-Layer Retrieval", "Combine statistical intent classification with dense vector semantic search to map varied student questions to exact answers.", CRIMSON_NITD),
        ("Anti-Hallucination LLM Guardrails", "Constrain language model generation strictly to retrieved verified text chunks; block speculative answers completely.", EMERALD_OK),
        ("Safe Fallback & Human Triage", "Trigger automated circuit-breakers on low-confidence queries; log unverified queries for administrator review and indexing.", AMBER_WARN)
    ]

    card_w2 = Inches(5.75)
    card_h2 = Inches(1.8)
    for i, (title, desc, color) in enumerate(objs):
        row = i // 2
        col = i % 2
        left_pos = Inches(0.8) + col * (card_w2 + Inches(0.233))
        top_pos = Inches(3.2) + row * (card_h2 + Inches(0.2))

        add_card(s3, left_pos, top_pos, card_w2, card_h2)
        tbox = s3.shapes.add_textbox(left_pos + Inches(0.25), top_pos + Inches(0.2), card_w2 - Inches(0.5), card_h2 - Inches(0.4))
        tf = tbox.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = f"Objective {i+1}: {title}"
        p.font.name = FONT_HEADING
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = color
        p.space_after = Pt(6)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_MUTED

    set_notes(s3, (
        "Our solution is built on a fundamental principle: "
        "A student question is never sent directly to an LLM. Instead, it passes through topic/intent classification, "
        "filters a verified knowledge repository via semantic vector search, and only the retrieved verified context "
        "is provided to a strictly controlled language model. "
        "This guarantees that the LLM acts purely as a linguistic synthesis engine rather than an institutional authority."
    ))

    # =========================================================================
    # SLIDE 4: System Features and Actual Chatbot UI
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "System Features & Actual Chatbot Interface", "User Experience & Features")

    # Left: Features list (width 4.8 in)
    feat_card = add_card(s4, Inches(0.8), Inches(1.65), Inches(4.5), Inches(5.2))
    tbox = s4.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(4.1), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Key Implemented Capabilities"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(12)

    features = [
        ("NIT Durgapur Institutional Branding", "Custom UI reflecting the official emblem, crimson/dark palette, and motto 'उद्योगः पुरुषस्य लक्षणम्'."),
        ("Multi-Turn Session Persistence", "Client-side and server-side SQLite session management allowing seamless conversation switching and history review."),
        ("Interactive Topic & Suggestion Chips", "Curated quick-start prompt chips for immediate discovery of hostel, academic, and facility rules."),
        ("Real-Time Visual Feedback", "Animated typing indicators, message bubble animations, and non-blocking error recovery banners."),
        ("Verified Status Indicators", "Explicit visual badges ('🛡️ Verified NIT Record') demarcating authoritative answers from general fallback notices.")
    ]

    for title, desc in features:
        p1 = tf.add_paragraph()
        p1.text = f"• {title}"
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = BLUE_DEEP
        
        p2 = tf.add_paragraph()
        p2.text = f"  {desc}"
        p2.font.name = FONT_BODY
        p2.font.size = Pt(10.5)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(8)

    # Right: Screenshot (width 7.0 in)
    img_path_s4 = ASSETS_DIR / "ui_slide04_main_chat.png"
    if img_path_s4.exists():
        s4.shapes.add_picture(str(img_path_s4), Inches(5.5), Inches(1.65), width=Inches(7.033))
    else:
        add_card(s4, Inches(5.5), Inches(1.65), Inches(7.033), Inches(5.2))

    set_notes(s4, (
        "Here on Slide 4 is a genuine screenshot of the running CampusAssist student interface. "
        "As you can observe on the right, the interface is branded with NIT Durgapur's official crest and motto. "
        "It features quick-access explore cards for hostel leave, facilities, and academic regulations. "
        "The left sidebar preserves previous chat sessions, allowing students to continue or clear conversations. "
        "Everything shown here is fully implemented in HTML5, CSS3, and modern JavaScript without heavy external UI dependencies."
    ))

    # =========================================================================
    # SLIDE 5: Technical Stack
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Verified Technical Stack", "Engineering Architecture")

    tech_categories = [
        ("Frontend Client", "HTML5, Vanilla CSS3, Modern JS (ES2021)", "Single-page responsive conversational UI; zero bulky frameworks; fast 60fps DOM rendering."),
        ("Backend Framework", "Python 3.12, Flask 3.0.x", "Modular application factory architecture with registered Blueprints for API, Admin, and Views."),
        ("Relational Database", "SQLite 3 (WAL Mode), SQLAlchemy ORM", "ACID-compliant storage for conversations, verified knowledge, taxonomy, and audit trails across 7 tables."),
        ("Intent Classification", "Scikit-Learn, TF-IDF Vectorizer", "Statistical n-gram feature extraction paired with Logistic Regression / SVC for fast sub-5ms intent mapping."),
        ("Semantic Retrieval", "Sentence-Transformers, NumPy", "Local 384-dimensional dense embeddings (all-MiniLM-L6-v2) with vectorized dot-product cosine similarity."),
        ("Controlled LLM", "Google Gemini 1.5 Flash (API) + Deterministic Fallback", "High-speed API synthesis with strict temperature (0.2) plus an autonomous local fallback when offline."),
        ("Security & Auth", "Werkzeug scrypt, CSRF, Secure Cookies", "Salted scrypt password hashing for administrators, constant-time token comparison, and input sanitization."),
        ("Automated Testing", "Pytest 9.x (150 Passing Tests)", "Rigorous test suite covering unit models, API endpoints, classification accuracy, and full integration in 49s.")
    ]

    card_w3 = Inches(2.75)
    card_h3 = Inches(2.45)
    for i, (cat, tech, purpose) in enumerate(tech_categories):
        r = i // 4
        c = i % 4
        left_pos = Inches(0.8) + c * (card_w3 + Inches(0.24))
        top_pos = Inches(1.7) + r * (card_h3 + Inches(0.2))

        add_card(s5, left_pos, top_pos, card_w3, card_h3)
        tbox = s5.shapes.add_textbox(left_pos + Inches(0.18), top_pos + Inches(0.18), card_w3 - Inches(0.36), card_h3 - Inches(0.36))
        tf = tbox.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = cat.upper()
        p.font.name = FONT_HEADING
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = CRIMSON_NITD
        p.space_after = Pt(4)

        p2 = tf.add_paragraph()
        p2.text = tech
        p2.font.name = FONT_HEADING
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = NAVY_DARK
        p2.space_after = Pt(6)

        p3 = tf.add_paragraph()
        p3.text = purpose
        p3.font.name = FONT_BODY
        p3.font.size = Pt(11)
        p3.font.color.rgb = TEXT_MUTED

    set_notes(s5, (
        "Slide 5 documents the exact technical stack verified in our workspace. "
        "We deliberately avoided over-engineering: Flask provides a lightweight, auditable micro-framework. "
        "For classification, Scikit-Learn TF-IDF delivers millisecond intent mapping. "
        "For semantic retrieval, we utilize 384-dimensional dense vectors with an in-memory NumPy cosine similarity store. "
        "And for validation, 150 automated test cases run continuously under Pytest with 100% pass rates."
    ))

    # =========================================================================
    # SLIDE 6: Overall System Architecture
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Overall System Architecture", "System Design & Component Tiers")

    # Diagram on Left (width 7.2 in)
    diag_path_s6 = ASSETS_DIR / "diagram1_system_architecture.png"
    if diag_path_s6.exists():
        s6.shapes.add_picture(str(diag_path_s6), Inches(0.8), Inches(1.65), width=Inches(7.2))
    else:
        add_card(s6, Inches(0.8), Inches(1.65), Inches(7.2), Inches(5.2))

    # Explanatory card on Right (width 4.3 in)
    add_card(s6, Inches(8.2), Inches(1.65), Inches(4.333), Inches(5.2))
    tbox = s6.shapes.add_textbox(Inches(8.4), Inches(1.85), Inches(3.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Architectural Tier Decomposition"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(12)

    tiers = [
        ("Tier 1: Presentation Layer", "Web browser interface executing asynchronous JSON communication over REST API (/api/chat, /api/conversations)."),
        ("Tier 2: Orchestration & Services", "Flask blueprints dispatching queries to ChatService, coordinating input validation, session tracking, and triage."),
        ("Tier 3: Dual Intelligence Engine", "Statistical IntentClassifier narrows domain scope; SemanticSearchService retrieves top-k dense vector candidates."),
        ("Tier 4: Synthesis & Persistence", "PromptBuilder injects verified chunks into Gemini LLM; SQLite database commits audit trail and conversations.")
    ]

    for title, desc in tiers:
        p1 = tf.add_paragraph()
        p1.text = f"• {title}"
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = BLUE_DEEP
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(8)

    set_notes(s6, (
        "This architectural diagram illustrates our 4-tier separation of concerns. "
        "The Presentation Tier submits queries to the REST API. "
        "The Application Tier coordinates services via `ChatService`. "
        "Notice the intelligence separation: the intent classifier and vector store run locally in-process, "
        "filtering verified knowledge records from the database. "
        "Finally, the synthesized answer and retrieval metadata are committed back to SQLite."
    ))

    # =========================================================================
    # SLIDE 7: Frontend and Backend Workflow
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Frontend & Backend Execution Workflows", "Execution Pipelines")

    # Left: Frontend workflow
    add_card(s7, Inches(0.8), Inches(1.65), Inches(5.75), Inches(5.2))
    diag_f = ASSETS_DIR / "diagram2_frontend_workflow.png"
    if diag_f.exists():
        s7.shapes.add_picture(str(diag_f), Inches(1.0), Inches(1.8), width=Inches(5.35))

    # Right: Backend workflow
    add_card(s7, Inches(6.783), Inches(1.65), Inches(5.75), Inches(5.2))
    diag_b = ASSETS_DIR / "diagram3_backend_workflow.png"
    if diag_b.exists():
        s7.shapes.add_picture(str(diag_b), Inches(6.983), Inches(1.8), width=Inches(5.35))

    set_notes(s7, (
        "Slide 7 contrasts the frontend and backend workflows side by side. "
        "On the left, the frontend captures user input, provides instant UI feedback with an animated typing indicator, "
        "and handles potential connection errors with retry capabilities. "
        "On the right, the backend receives the JSON payload, validates the input, runs intent classification, "
        "executes filtered vector search, constructs the grounded prompt, and handles persistence. "
        "This clear separation ensures high responsiveness and fault tolerance."
    ))

    # =========================================================================
    # SLIDE 8: Topic and Intent Classification
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Topic & Intent Classification", "Domain Understanding")

    # Left: Concept explanation (width 5.5 in)
    add_card(s8, Inches(0.8), Inches(1.65), Inches(5.5), Inches(5.2))
    tbox = s8.shapes.add_textbox(Inches(1.0), Inches(1.85), Inches(5.1), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Hierarchical Taxonomy Model"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(10)

    p1 = tf.add_paragraph()
    p1.text = "• Broad Topic: Represents the high-level campus administrative division (e.g., 'Hostel', 'Academics', 'Campus Facilities')."
    p1.font.name = FONT_BODY
    p1.font.size = Pt(12)
    p1.font.color.rgb = TEXT_MUTED
    p1.space_after = Pt(8)

    p2 = tf.add_paragraph()
    p2.text = "• Specific Intent: Represents the precise student communicative goal (e.g., 'hostel_leave', 'room_change', 'examination_rules', 'attendance_rules')."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(12)
    p2.font.color.rgb = TEXT_MUTED
    p2.space_after = Pt(12)

    p3 = tf.add_paragraph()
    p3.text = "Statistical Classifier Pipeline"
    p3.font.name = FONT_HEADING
    p3.font.size = Pt(15)
    p3.font.bold = True
    p3.font.color.rgb = BLUE_DEEP
    p3.space_after = Pt(8)

    p4 = tf.add_paragraph()
    p4.text = "1. Tokenization & TF-IDF Extraction: Extracts character & word n-grams (1,2) over normalized text.\n" \
              "2. Supervised Classification: Evaluates calibrated probability distribution P(Intent | Query) using Logistic Regression / SVC.\n" \
              "3. Confidence Thresholding: Flags queries below confidence threshold (0.55) as out-of-scope for fallback triage."
    p4.font.name = FONT_BODY
    p4.font.size = Pt(11.5)
    p4.font.color.rgb = TEXT_MUTED

    # Right: Phrasing Invariance Example Box (width 6.0 in)
    add_card(s8, Inches(6.5), Inches(1.65), Inches(6.033), Inches(5.2))
    tbox2 = s8.shapes.add_textbox(Inches(6.7), Inches(1.85), Inches(5.633), Inches(4.8))
    tf2 = tbox2.text_frame
    tf2.word_wrap = True

    p = tf2.paragraphs[0]
    p.text = "Phrasing Invariance Demonstration"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = CRIMSON_NITD
    p.space_after = Pt(10)

    phrasings = [
        '"How can I apply for hostel leave?"',
        '"I want to go home for two days. What should I do?"',
        '"Can I leave the hostel this weekend?"',
        '"What permission do I need to go home?"',
        '"How to get a gate pass for leave?"'
    ]

    p_sub = tf2.add_paragraph()
    p_sub.text = "5 Completely Different Phrasings:"
    p_sub.font.name = FONT_HEADING
    p_sub.font.size = Pt(12)
    p_sub.font.bold = True
    p_sub.font.color.rgb = NAVY_DARK
    p_sub.space_after = Pt(6)

    for q in phrasings:
        pq = tf2.add_paragraph()
        pq.text = f"  • {q}"
        pq.font.name = FONT_BODY
        pq.font.size = Pt(11.5)
        pq.font.color.rgb = TEXT_PRIMARY
        pq.space_after = Pt(3)

    p_map = tf2.add_paragraph()
    p_map.text = "\nUnified Output Resolution:"
    p_map.font.name = FONT_HEADING
    p_map.font.size = Pt(12)
    p_map.font.bold = True
    p_map.font.color.rgb = BLUE_DEEP
    p_map.space_after = Pt(4)

    p_res = tf2.add_paragraph()
    p_res.text = "➔ Broad Topic: Hostel (ID 2)\n" \
                 "➔ Specific Intent: Hostel Leave / Gate Pass (hostel_leave, ID 1)\n" \
                 "➔ Target Knowledge ID: 1 ('NIT Durgapur Hostel Leave & Gate Pass Rules')"
    p_res.font.name = FONT_BODY
    p_res.font.size = Pt(12)
    p_res.font.bold = True
    p_res.font.color.rgb = EMERALD_OK

    set_notes(s8, (
        "Slide 8 addresses why classification is critical. "
        "A student might say 'Can I leave the hostel this weekend?' or 'What permission do I need to go home?'. "
        "Notice that the words 'leave' and 'permission' do not match identical string patterns. "
        "Our TF-IDF classifier maps both distinct sentences to Topic: Hostel, Intent: hostel_leave with high confidence. "
        "This drastically prunes the candidate search space before semantic retrieval occurs."
    ))

    # =========================================================================
    # SLIDE 9: Semantic Search and Knowledge Repository
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Semantic Search & Verified Knowledge Repository", "Retrieval Mechanics")

    # Left: Retrieval Diagram (width 6.2 in)
    diag_ret = ASSETS_DIR / "diagram4_retrieval_workflow.png"
    if diag_ret.exists():
        s9.shapes.add_picture(str(diag_ret), Inches(0.8), Inches(1.65), width=Inches(6.2))
    else:
        add_card(s9, Inches(0.8), Inches(1.65), Inches(6.2), Inches(5.2))

    # Right: Mechanics card (width 5.3 in)
    add_card(s9, Inches(7.2), Inches(1.65), Inches(5.333), Inches(5.2))
    tbox = s9.shapes.add_textbox(Inches(7.4), Inches(1.85), Inches(4.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Vector Similarity Mechanics"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(10)

    p1 = tf.add_paragraph()
    p1.text = "• 384-Dimensional Embeddings: Transformed via all-MiniLM-L6-v2 transformer into dense semantic vector representations."
    p1.font.name = FONT_BODY
    p1.font.size = Pt(11.5)
    p1.font.color.rgb = TEXT_MUTED
    p1.space_after = Pt(8)

    p2 = tf.add_paragraph()
    p2.text = "• Cosine Similarity Computation:\n  cos(θ) = (u • v) / (||u|| ||v||)\n  Optimized using normalized matrix dot products in NumPy."
    p2.font.name = FONT_BODY
    p2.font.size = Pt(11.5)
    p2.font.bold = True
    p2.font.color.rgb = BLUE_DEEP
    p2.space_after = Pt(8)

    p3 = tf.add_paragraph()
    p3.text = "• Dual-Layer Hybrid Filtering: Scans only verified (is_verified=1) and active (is_active=1) records matching the classified intent."
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11.5)
    p3.font.color.rgb = TEXT_MUTED
    p3.space_after = Pt(8)

    p4 = tf.add_paragraph()
    p4.text = "• Relevance Thresholding (τ = 0.35): Any candidate scoring below τ triggers safe fallback rather than returning weak matches."
    p4.font.name = FONT_BODY
    p4.font.size = Pt(11.5)
    p4.font.color.rgb = CRIMSON_NITD

    set_notes(s9, (
        "On Slide 9, we examine the semantic retrieval mechanics. "
        "Each verified knowledge entry is indexed as a 384-dimensional dense embedding using `all-MiniLM-L6-v2`. "
        "When a query arrives, we compute normalized cosine similarity against candidate embeddings. "
        "Crucially, we enforce a strict relevance threshold of 0.35: if the highest scoring candidate is weak, "
        "the system rejects it, preventing false context from reaching the language model."
    ))

    # =========================================================================
    # SLIDE 10: Controlled LLM and Grounded Responses
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Controlled LLM & Anti-Hallucination Guardrails", "Grounded Generation")

    # Left: Code panel / Diagram (width 6.2 in)
    code_panel = ASSETS_DIR / "code_stage6_grounded_prompt_builder.png"
    if code_panel.exists():
        s10.shapes.add_picture(str(code_panel), Inches(0.8), Inches(1.65), width=Inches(6.2))
    else:
        add_card(s10, Inches(0.8), Inches(1.65), Inches(6.2), Inches(5.2))

    # Right: Guardrails explanation (width 5.3 in)
    add_card(s10, Inches(7.2), Inches(1.65), Inches(5.333), Inches(5.2))
    tbox = s10.shapes.add_textbox(Inches(7.4), Inches(1.85), Inches(4.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Strict Grounding Safeguards"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(10)

    guardrails = [
        ("Contextual Boundary Enforcement", "The prompt explicitly instructs: 'Answer the question ONLY based on the verified institutional context below. Do NOT assume or invent details.'"),
        ("Zero Extrapolation Policy", "If fees, deadlines, or approvals are not stated in the context, the model is forbidden from guessing them."),
        ("Deterministic Fallback Anchor", "If verified context is absent, the system completely bypasses the LLM and emits a safe, pre-scripted administrative fallback notice."),
        ("Low Generation Temperature (0.2)", "Minimizes stochastic sampling variance, ensuring consistent, factual, reproducible responses across sessions.")
    ]

    for title, desc in guardrails:
        p1 = tf.add_paragraph()
        p1.text = f"• {title}"
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = CRIMSON_NITD
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(6)

    set_notes(s10, (
        "Slide 10 highlights how we control the LLM. "
        "The code panel on the left shows our `PromptBuilder` class from `prompt_builder.py`. "
        "We inject system boundary constraints before the retrieved context chunks. "
        "The language model is explicitly commanded: 'Answer ONLY based on verified institutional context'. "
        "With temperature fixed at 0.2, the LLM acts purely as a linguistic summarizer, not an autonomous policymaker."
    ))

    # =========================================================================
    # SLIDE 11: Unknown Queries and Knowledge Improvement
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Unknown Queries & Knowledge Evolution", "Human-in-the-Loop Governance")

    # Left: Genuine Admin Screenshot (width 6.2 in)
    admin_ui = ASSETS_DIR / "ui_slide11_admin_dashboard.png"
    if admin_ui.exists():
        s11.shapes.add_picture(str(admin_ui), Inches(0.8), Inches(1.65), width=Inches(6.2))
    else:
        add_card(s11, Inches(0.8), Inches(1.65), Inches(6.2), Inches(5.2))

    # Right: The Feedback Loop (width 5.3 in)
    add_card(s11, Inches(7.2), Inches(1.65), Inches(5.333), Inches(5.2))
    tbox = s11.shapes.add_textbox(Inches(7.4), Inches(1.85), Inches(4.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Continuous Improvement Lifecycle"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(10)

    steps_s11 = [
        ("1. Out-of-Scope Query Arrival", "Student submits an unindexed inquiry (e.g., 'convocation gown deposit')."),
        ("2. Circuit-Breaker Activation", "Classification / Retrieval confidence fails threshold (< 0.35). Safe fallback displayed."),
        ("3. Unresolved Query Logging", "Query logged into 'unresolved_queries' with predicted topic, timestamp, and status 'pending'."),
        ("4. Administrator Verification", "Authorized official logs into admin dashboard, reviews triage queue, and writes verified answer."),
        ("5. Search Index Hot Reload", "Vector store regenerates embeddings dynamically. Query resolves immediately in subsequent asks!")
    ]

    for title, desc in steps_s11:
        p1 = tf.add_paragraph()
        p1.text = title
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(12)
        p1.font.bold = True
        p1.font.color.rgb = BLUE_DEEP
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(6)

    set_notes(s11, (
        "Slide 11 demonstrates how CampusAssist improves over time. "
        "On the left is a live screenshot of our implemented Administration Dashboard. "
        "When a student asks an unindexed question, the system does not guess. "
        "It triggers a circuit breaker, logs the question into the review queue, and alerts administrators. "
        "Once verified knowledge is authored and saved, the vector store updates immediately without model retraining."
    ))

    # =========================================================================
    # SLIDE 12: Unique End-to-End Query Demonstration (The Real Walkthrough)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Live Execution Walkthrough: Examination Regulations", "Real-World Query Verification")

    # Left: Genuine Chatbot Screenshot of Examination Query (width 6.2 in)
    walkthrough_ui = ASSETS_DIR / "ui_slide12_query_response.png"
    if walkthrough_ui.exists():
        s12.shapes.add_picture(str(walkthrough_ui), Inches(0.8), Inches(1.65), width=Inches(6.2))
    else:
        add_card(s12, Inches(0.8), Inches(1.65), Inches(6.2), Inches(5.2))

    # Right: Execution Trace Table (width 5.3 in)
    add_card(s12, Inches(7.2), Inches(1.65), Inches(5.333), Inches(5.2))
    tbox = s12.shapes.add_textbox(Inches(7.4), Inches(1.85), Inches(4.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Trace: 'How do I find examination info?'"
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = CRIMSON_NITD
    p.space_after = Pt(8)

    traces = [
        ("1. Input Event Handler", "chat.js: L140–175", "Dispatches async JSON POST to /api/chat with active session_id."),
        ("2. API Validation", "api_routes.py: L81–120", "Sanitizes text, verifies payload schema, invokes ChatService."),
        ("3. Intent Classification", "intent_classifier.py: L164", "Predicted: 'examination_rules' (Confidence: 1.0000)."),
        ("4. Semantic Retrieval", "semantic_search.py: L170", "Retrieved Item ID 8 ('Examination Guidelines & Regs', Score: 1.0000)."),
        ("5. Grounded Synthesis", "prompt_builder.py: L40", "Injects verified rules into Gemini prompt; outputs structured markdown."),
        ("6. Session Persistence", "chat_service.py: L254", "Commits interaction & metadata to SQLite in 10.12 ms latency.")
    ]

    for stage, src, desc in traces:
        p1 = tf.add_paragraph()
        p1.text = f"{stage} [{src}]"
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = BLUE_DEEP
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(10)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(4)

    set_notes(s12, (
        "Slide 12 presents our required unique end-to-end implementation walkthrough. "
        "Instead of hostel leave, we executed: 'How do I find examination information?'. "
        "The screenshot on the left is captured directly from the running web application. "
        "Notice the '🛡️ Verified NIT Record' badge and the structured breakdown of mid-term, end-term, and admit card rules. "
        "On the right, we trace the exact source code execution from `chat.js` line 140 all the way to database commit in 10.12 milliseconds."
    ))

    # =========================================================================
    # SLIDE 13: Actual Code Evidence, Interface, and Testing
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Code Verification & Automated Test Suite", "Technical Grounding & Testing")

    # Left: Code panel / Interface (width 6.2 in)
    code_ret = ASSETS_DIR / "code_stage4_semantic_retrieval.png"
    if code_ret.exists():
        s13.shapes.add_picture(str(code_ret), Inches(0.8), Inches(1.65), width=Inches(6.2))
    else:
        add_card(s13, Inches(0.8), Inches(1.65), Inches(6.2), Inches(5.2))

    # Right: Test Results Card (width 5.3 in)
    add_card(s13, Inches(7.2), Inches(1.65), Inches(5.333), Inches(5.2))
    tbox = s13.shapes.add_textbox(Inches(7.4), Inches(1.85), Inches(4.933), Inches(4.8))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Automated Test Suite Verification"
    p.font.name = FONT_HEADING
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = NAVY_DARK
    p.space_after = Pt(8)

    p_badge = tf.add_paragraph()
    p_badge.text = "150 / 150 TESTS PASSED (100% SUCCESS)"
    p_badge.font.name = FONT_HEADING
    p_badge.font.size = Pt(13)
    p_badge.font.bold = True
    p_badge.font.color.rgb = EMERALD_OK
    p_badge.space_after = Pt(10)

    tests_data = [
        ("tests/test_classifier.py", "Intent & topic prediction accuracy, threshold boundaries, and empty input handling."),
        ("tests/test_retrieval.py", "Normalized cosine similarity math, vector store indexing, and score thresholding."),
        ("tests/test_api.py", "REST schema validation, session cookies, rate-limiting, and error responses."),
        ("tests/test_services.py", "ChatService coordination, circuit breaker trigger, and fallback logging."),
        ("tests/test_admin.py", "Scrypt authentication, role authorization, and audit trail persistence.")
    ]

    for file_name, desc in tests_data:
        p1 = tf.add_paragraph()
        p1.text = f"• {file_name}"
        p1.font.name = FONT_HEADING
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = BLUE_DEEP
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = FONT_BODY
        p2.font.size = Pt(10)
        p2.font.color.rgb = TEXT_MUTED
        p2.space_after = Pt(4)

    p_dur = tf.add_paragraph()
    p_dur.text = "\nExecution Duration: 49.06s across unit & integration fixtures."
    p_dur.font.name = FONT_BODY
    p_dur.font.size = Pt(10.5)
    p_dur.font.bold = True
    p_dur.font.color.rgb = NAVY_DARK

    set_notes(s13, (
        "Slide 13 provides concrete evidence from our automated testing and code audit. "
        "On the left, you can inspect the exact code from `semantic_search.py` implementing filtered retrieval. "
        "On the right, we report the actual execution of our Pytest suite: exactly 150 automated tests executed, "
        "covering classification, retrieval, API contracts, and administration, with zero failures in 49 seconds."
    ))

    # =========================================================================
    # SLIDE 14: Limitations, Evaluation, and Future Scope
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Limitations, Evaluation & Future Roadmap", "Project Boundaries & Next Steps")

    cards_s14 = [
        ("Current System Limitations",
         [
             "Dependence on Human Knowledge Curation: The system is only as fresh as the verified database entries authored by staff.",
             "Cold-Start Slang / Acronyms: Unseen abbreviations require periodic seed dataset expansions.",
             "External API Latency: Cloud LLM calls add 1–2s network latency; local fallback runs instantaneously."
         ],
         CRIMSON_NITD),
        ("Academic Evaluation Plan",
         [
             "Classification Accuracy & F1: Benchmarking intent prediction across 200 synthetic paraphrased student questions.",
             "Retrieval MRR & Precision@K: Evaluating whether the correct policy is returned in the top-1 rank.",
             "Zero-Hallucination Rejection Rate: Testing adversarial queries to ensure the model never invents policies."
         ],
         BLUE_DEEP),
        ("Future Engineering Roadmap",
         [
             "Automated PDF & Notice Ingestion: Extract circulars automatically using layout-aware OCR parsers.",
             "Multilingual Support: Natural translation pipeline for Bengali and Hindi student inquiries.",
             "Student Portal Single Sign-On: Authenticated personalized status checks (grade cards, dues)."
         ],
         EMERALD_OK)
    ]

    col_w14 = Inches(3.7)
    gap14 = Inches(0.25)
    top14 = Inches(1.7)
    card_h14 = Inches(5.1)

    for i, (title, points, color) in enumerate(cards_s14):
        left_pos = Inches(0.8) + i * (col_w14 + gap14)
        add_card(s14, left_pos, top14, col_w14, card_h14)
        
        tbox = s14.shapes.add_textbox(left_pos + Inches(0.2), top14 + Inches(0.25), col_w14 - Inches(0.4), card_h14 - Inches(0.5))
        tf = tbox.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.name = FONT_HEADING
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = color
        p.space_after = Pt(12)

        for pt in points:
            parts = pt.split(":", 1)
            p1 = tf.add_paragraph()
            p1.text = f"• {parts[0]}:"
            p1.font.name = FONT_HEADING
            p1.font.size = Pt(11)
            p1.font.bold = True
            p1.font.color.rgb = NAVY_DARK
            
            if len(parts) > 1:
                p2 = tf.add_paragraph()
                p2.text = f"  {parts[1].strip()}"
                p2.font.name = FONT_BODY
                p2.font.size = Pt(10.5)
                p2.font.color.rgb = TEXT_MUTED
                p2.space_after = Pt(8)

    set_notes(s14, (
        "On Slide 14, we honestly address our project boundaries. "
        "Because our architecture prioritizes truthfulness, it depends directly on administrative curation. "
        "Our formal evaluation plan will measure Classification F1 score, retrieval MRR, and zero-hallucination rate. "
        "Looking forward, we plan to implement automated OCR notice parsing and multilingual support for Bengali and Hindi."
    ))

    # =========================================================================
    # SLIDE 15: Conclusion and Q&A
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    # Background full-bleed
    bg15 = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg15.fill.solid()
    bg15.fill.fore_color.rgb = NAVY_DARK
    bg15.line.fill.background()

    # Top accent line
    bar15 = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.12))
    bar15.fill.solid()
    bar15.fill.fore_color.rgb = CRIMSON_NITD
    bar15.line.fill.background()

    # Center card
    card15 = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(1.2), Inches(10.333), Inches(5.1))
    card15.fill.solid()
    card15.fill.fore_color.rgb = RGBColor(15, 32, 57)
    card15.line.color.rgb = RGBColor(30, 62, 98)

    tbox15 = s15.shapes.add_textbox(Inches(1.8), Inches(1.5), Inches(9.733), Inches(4.5))
    tf15 = tbox15.text_frame
    tf15.word_wrap = True

    p = tf15.paragraphs[0]
    p.text = "PROJECT SYNTHESIS & CONCLUSION"
    p.font.name = FONT_HEADING
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CRIMSON_NITD
    p.space_after = Pt(8)

    p1 = tf15.add_paragraph()
    p1.text = "CampusAssist delivers a robust, domain-specific AI assistant for NIT Durgapur by replacing fragile exact-keyword matching with semantic retrieval, and replacing hallucination-prone generation with strictly grounded, verified institutional records."
    p1.font.name = FONT_BODY
    p1.font.size = Pt(14)
    p1.font.color.rgb = RGBColor(226, 232, 240)
    p1.space_after = Pt(14)

    p2 = tf15.add_paragraph()
    p2.text = "Factual Reliability = Verified Knowledge + Dual-Layer Retrieval + Controlled Guardrails"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = AZURE_ACCENT
    p2.space_after = Pt(24)

    p3 = tf15.add_paragraph()
    p3.text = "Thank You!"
    p3.font.name = FONT_HEADING
    p3.font.size = Pt(32)
    p3.font.bold = True
    p3.font.color.rgb = WHITE
    p3.space_after = Pt(6)

    p4 = tf15.add_paragraph()
    p4.text = "Questions & Technical Discussion\n" \
              "Bittyam Paul  •  Department of Computer Science & Engineering  •  NIT Durgapur"
    p4.font.name = FONT_BODY
    p4.font.size = Pt(13)
    p4.font.color.rgb = RGBColor(148, 163, 184)

    set_notes(s15, (
        "In conclusion, CampusAssist proves that high-stakes institutional AI cannot rely on ungrounded generation. "
        "By enforcing a dual-layer retrieval pipeline and strict anti-hallucination guardrails, "
        "we deliver factual, reliable assistance for NIT Durgapur students. "
        "Thank you very much for your time and guidance. I welcome your questions and discussion."
    ))

    # Save presentation
    output_path = "CampusAssist_Project_Presentation.pptx"
    prs.save(output_path)
    print(f"[+] Presentation saved successfully: {output_path}")
    print(f"[+] Total slides created: {len(prs.slides)}")

if __name__ == "__main__":
    create_deck()

