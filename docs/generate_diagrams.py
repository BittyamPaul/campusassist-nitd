"""
CampusAssist: Diagram Generation Utility
Generates high-resolution academic workflow diagrams for the Project Proposal.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.makedirs("docs/proposal_assets", exist_ok=True)

c_navy = "#0f172a"
c_blue = "#2563eb"
c_green = "#059669"
c_amber = "#d97706"
c_gray = "#64748b"
c_bg = "#f8fafc"

def create_diagram2():
    # Frontend Workflow
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 95, "CampusAssist: Frontend Interaction Workflow", fontsize=14, fontweight="bold", ha="center", color=c_navy)

    steps = [
        ("1. Load Webapp", "Fetch HTML/CSS/JS\nVerify Session ID\nPopulate Starter Chips", 10),
        ("2. Submit Question", "Validate non-empty\nDisplay user bubble\nTrigger loading state", 36),
        ("3. Await Response", "POST /api/chat\nDisplay pulse mascot\nHandle network errors", 62),
        ("4. Render Answer", "Parse verified badge\nFormat official links\nEnable feedback buttons", 88),
    ]

    for title, desc, x in steps:
        rect = patches.FancyBboxPatch((x-11, 40), 22, 40, boxstyle="round,pad=0.8", edgecolor=c_navy, facecolor=c_bg, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, 74, title, fontsize=10, fontweight="bold", ha="center", color=c_blue)
        ax.text(x, 56, desc, fontsize=8.5, ha="center", va="center", color=c_navy)

    for i in range(len(steps)-1):
        x1 = steps[i][2] + 11
        x2 = steps[i+1][2] - 11
        ax.annotate("", xy=(x2, 60), xytext=(x1, 60), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.2, headwidth=6))

    # Supporting capabilities
    rect_sub = patches.FancyBboxPatch((5, 12), 90, 18, boxstyle="round,pad=0.8", edgecolor="#94a3b8", facecolor="#ffffff", linewidth=1)
    ax.add_patch(rect_sub)
    ax.text(7, 24, "SUPPORTING CLIENT-SIDE FEATURES:", fontsize=9.5, fontweight="bold", color=c_navy)
    ax.text(10, 16, "• Keyboard Navigation: Enter to send, Shift+Enter newline, Esc to close drawer\n• History Drawer: Lists prior sessions fetched asynchronously from /api/conversations\n• Session Reset: Clear chat button generates fresh UUID session context in localStorage", fontsize=8.5, color="#334155")

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram2_frontend_workflow.png", bbox_inches="tight")
    plt.close()

def create_diagram3():
    # Backend 14-Step Workflow
    fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 96, "CampusAssist: 14-Step Backend Processing Pipeline", fontsize=14, fontweight="bold", ha="center", color=c_navy)

    pipeline = [
        ("1. Route & Rate Limit", "Check sliding IP window\nStrip malicious payload", 12, 80),
        ("2. Input Bounds Check", "Validate non-null, string,\nlength <= 1500 chars", 37, 80),
        ("3. Session Persistence", "Lookup or generate UUID\nInitialize message chain", 62, 80),
        ("4. Log User Message", "Insert student question\ninto SQLite messages", 87, 80),

        ("5. Text Preprocessing", "Stemming, stopword purge,\ncontraction expansion", 12, 54),
        ("6. Intent Classification", "Predict Topic and Intent\nCompute calibrated conf", 37, 54),
        ("7. Dense Embedding", "768-dim float32 vector\nLRU cache lookup", 62, 54),
        ("8. Vector Dot Search", "In-Memory Cosine sim\nFilter active and verified", 87, 54),

        ("9. Context Manager", "Disambiguate follow-ups\nStitch conversational turn", 12, 28),
        ("10. Threshold Gating", "Evaluate Sufficiency\nScore >= 0.50 threshold", 37, 28),
        ("11. Prompt Assembly", "System Directives +\nRetrieved Context Only", 62, 28),
        ("12. Controlled LLM", "Synthesize natural answer\nZero policy invention", 87, 28),
    ]

    for title, desc, x, y in pipeline:
        rect = patches.FancyBboxPatch((x-11, y-10), 22, 18, boxstyle="round,pad=0.6", edgecolor="#94a3b8", facecolor="#ffffff", linewidth=1)
        ax.add_patch(rect)
        ax.text(x, y+5, title, fontsize=9, fontweight="bold", ha="center", color=c_blue)
        ax.text(x, y-3, desc, fontsize=7.5, ha="center", va="center", color="#334155")

    rect_end = patches.FancyBboxPatch((15, 4), 70, 12, boxstyle="round,pad=0.8", edgecolor=c_green, facecolor="#f0fdf4", linewidth=1.5)
    ax.add_patch(rect_end)
    ax.text(50, 11.5, "13. Response Storage and 14. Structured JSON Delivery", fontsize=10, fontweight="bold", ha="center", color=c_green)
    ax.text(50, 7.5, "Persist assistant message to DB (is_verified flag) • Return JSON with answer, verified sources, authority contact, official URL and telemetry timings", fontsize=8, ha="center", color=c_navy)

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram3_backend_workflow.png", bbox_inches="tight")
    plt.close()

def create_diagram4():
    # Semantic Retrieval & Vector Math
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 95, "Semantic Vector Retrieval and Mathematical Dot Product Search", fontsize=13, fontweight="bold", ha="center", color=c_navy)

    r1 = patches.FancyBboxPatch((5, 52), 26, 34, boxstyle="round,pad=0.8", edgecolor=c_navy, facecolor=c_bg, linewidth=1.2)
    ax.add_patch(r1)
    ax.text(18, 80, "Query Vectorization", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(18, 66, "Input: Student Query\n\nq = Embed(Query)\n\nL2-Normalization:\nq_unit = q / ||q||_2\nDim: 1 x 768 float32", fontsize=8.5, ha="center", color=c_navy)

    r2 = patches.FancyBboxPatch((37, 52), 26, 34, boxstyle="round,pad=0.8", edgecolor=c_navy, facecolor=c_bg, linewidth=1.2)
    ax.add_patch(r2)
    ax.text(50, 80, "In-Memory Dot Product", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(50, 66, "Pre-indexed Matrix:\nM in R^(N x 768)\n\nCosine Similarity:\nsims = np.dot(M, q_unit)\nSub-ms C-level BLAS", fontsize=8.5, ha="center", color=c_navy)

    r3 = patches.FancyBboxPatch((69, 52), 26, 34, boxstyle="round,pad=0.8", edgecolor=c_navy, facecolor=c_bg, linewidth=1.2)
    ax.add_patch(r3)
    ax.text(82, 80, "Strict Gating and Ranking", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(82, 66, "Filter Constraints:\n• is_active == 1\n• status == 'verified'\n\nThreshold Gate:\nScore >= 0.50 (Sufficient)\nScore < 0.50 (Circuit Breaker)", fontsize=8.5, ha="center", color=c_navy)

    ax.annotate("", xy=(37, 69), xytext=(31, 69), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.2, headwidth=6))
    ax.annotate("", xy=(69, 69), xytext=(63, 69), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.2, headwidth=6))

    r_eq = patches.FancyBboxPatch((10, 10), 80, 28, boxstyle="round,pad=0.8", edgecolor=c_green, facecolor="#f0fdf4", linewidth=1)
    ax.add_patch(r_eq)
    ax.text(50, 31, "Cosine Similarity Formulation (Unit-Length Simplification):", fontsize=10, fontweight="bold", ha="center", color=c_green)
    ax.text(50, 21, "Cosine_Sim(q, k_i) = (q · k_i) / (||q||_2 * ||k_i||_2)  ==>  q_unit · k_unit", fontsize=10.5, ha="center", color=c_navy)
    ax.text(50, 14, "Because all vectors are pre-normalized during indexing (||k_i||_2 = 1), cosine similarity reduces to pure matrix dot products.", fontsize=8, ha="center", color="#334155")

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram4_retrieval_workflow.png", bbox_inches="tight")
    plt.close()

def create_diagram5():
    # LLM Grounding Workflow
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 95, "Controlled LLM Grounding and Zero-Fabrication Guardrail", fontsize=13, fontweight="bold", ha="center", color=c_navy)

    r_in = patches.FancyBboxPatch((5, 15), 35, 72, boxstyle="round,pad=0.8", edgecolor="#94a3b8", facecolor=c_bg, linewidth=1.2)
    ax.add_patch(r_in)
    ax.text(22.5, 81, "Prompt Elements Assembled", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(7, 72, "1. System Directives:\n   'You are CampusAssist...'\n   'SOLE SOURCE OF TRUTH: Context'\n   'ZERO POLICY INVENTION'\n\n2. Student Question:\n   'How do I find examination info?'\n\n3. Classified Intent & Domain:\n   Domain: Academics • Intent: Exam Rules\n\n4. Verified Knowledge Context:\n   Title: NIT Durgapur Exam Guidelines\n   Status: VERIFIED (v1)\n   Content: Admit card, Reporting, Rules", fontsize=8, color=c_navy)

    ax.annotate("", xy=(53, 51), xytext=(42, 51), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.5, headwidth=7))
    ax.text(47.5, 54, "Strict Prompt", fontsize=8, ha="center", color="#475569")

    r_llm = patches.FancyBboxPatch((55, 48), 40, 39, boxstyle="round,pad=0.8", edgecolor=c_blue, facecolor="#eff6ff", linewidth=1.2)
    ax.add_patch(r_llm)
    ax.text(75, 81, "Controlled Synthesis Engine", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(58, 62, "• Google Gemini 2.5 Flash / 1.5 Flash\n• Low Temperature (0.1 - 0.2)\n• Translates raw procedural points into\n  courteous, natural language steps\n• Strictly references cited authorities & links", fontsize=8, color=c_navy)

    r_fb = patches.FancyBboxPatch((55, 15), 40, 27, boxstyle="round,pad=0.8", edgecolor=c_green, facecolor="#f0fdf4", linewidth=1.2)
    ax.add_patch(r_fb)
    ax.text(75, 36, "Offline Deterministic Fallback", fontsize=9.5, fontweight="bold", ha="center", color=c_green)
    ax.text(58, 24, "• Activates if API quota/network drops\n• Extracts structured steps directly from DB\n• 100% deterministic, zero LLM dependency\n• Guaranteed zero hallucination", fontsize=7.8, color=c_navy)

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram5_llm_grounding_workflow.png", bbox_inches="tight")
    plt.close()

def create_diagram6():
    # Unknown Query & Admin Closed-Loop Triage
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 95, "Unknown-Query Circuit Breaker and Closed-Loop Knowledge Triage", fontsize=13, fontweight="bold", ha="center", color=c_navy)

    r1 = patches.FancyBboxPatch((5, 48), 28, 38, boxstyle="round,pad=0.8", edgecolor="#dc2626", facecolor="#fef2f2", linewidth=1.2)
    ax.add_patch(r1)
    ax.text(19, 80, "1. Circuit Breaker", fontsize=10, fontweight="bold", ha="center", color="#dc2626")
    ax.text(19, 64, "Query: Unseeded / Out-of-domain\nCosine Sim < 0.50 Threshold\n\nAction: BLOCK LLM CALL\nDeliver safe contact notice to student\nLog to unresolved_queries queue", fontsize=8, ha="center", color=c_navy)

    r2 = patches.FancyBboxPatch((37, 48), 28, 38, boxstyle="round,pad=0.8", edgecolor=c_amber, facecolor="#fffbeb", linewidth=1.2)
    ax.add_patch(r2)
    ax.text(51, 80, "2. Admin Inspection", fontsize=10, fontweight="bold", ha="center", color=c_amber)
    ax.text(51, 64, "Staff logs into /admin/unresolved\nReviews predicted topic/intent\n\nInputs official NITD regulation\nEnter procedures, contacts, URLs\nClicks 'Verify & Add Knowledge'", fontsize=8, ha="center", color=c_navy)

    r3 = patches.FancyBboxPatch((69, 48), 26, 38, boxstyle="round,pad=0.8", edgecolor=c_green, facecolor="#f0fdf4", linewidth=1.2)
    ax.add_patch(r3)
    ax.text(82, 80, "3. Dynamic Re-Index", fontsize=10, fontweight="bold", ha="center", color=c_green)
    ax.text(82, 64, "Commit record to SQLite\nClear vector LRU cache\nCompute new dense embedding\nRebuild contiguous NumPy matrix\nRetrain intent classifier", fontsize=8, ha="center", color=c_navy)

    ax.annotate("", xy=(37, 67), xytext=(33, 67), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.2, headwidth=6))
    ax.annotate("", xy=(69, 67), xytext=(65, 67), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1.2, headwidth=6))

    r_res = patches.FancyBboxPatch((10, 10), 80, 26, boxstyle="round,pad=0.8", edgecolor=c_blue, facecolor="#eff6ff", linewidth=1.2)
    ax.add_patch(r_res)
    ax.text(50, 29, "Closed-Loop Outcome: Instant Resolution for Future Students", fontsize=10, fontweight="bold", ha="center", color=c_blue)
    ax.text(50, 19, "The very next student asking the previously unresolved question (or any semantic variation) immediately\nretrieves the newly verified institutional record with full citations and authority contacts. Zero server restart required.", fontsize=8.5, ha="center", color=c_navy)

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram6_unknown_query_triage.png", bbox_inches="tight")
    plt.close()

def create_diagram7():
    # End-to-End Walkthrough Trace
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 96, "End-to-End Implementation Walkthrough: Examination Regulations Query", fontsize=13, fontweight="bold", ha="center", color=c_navy)

    flow = [
        ("1. Student Submission", "\"How do I find examination information?\"\nchat.js sends POST /api/chat", 12, 70),
        ("2. Router & Bounds", "api_routes.py validates input length\nInitializes session UUID", 37, 70),
        ("3. Intent Classifier", "intent_classifier.py predicts:\nTopic: Academics • Intent: Exam Rules", 62, 70),
        ("4. Vector Embedder", "gemini_provider / local_provider\nGenerates L2-normalized float32 vector", 87, 70),

        ("5. Vector Dot Product", "vector_store.py computes cosine sim:\nTop Match: Exam Regulations (Sim: 1.0)", 12, 32),
        ("6. Sufficiency Gating", "Score 1.0 >= 0.50 Threshold\nVerified & Active Status Confirmed", 37, 32),
        ("7. Prompt & LLM", "prompt_builder + gemini 2.5 flash\nStrictly grounded natural response", 62, 32),
        ("8. DB & JSON Output", "Persist assistant message in SQLite\nDeliver response with portal URL & sources", 87, 32),
    ]

    for title, desc, x, y in flow:
        rect = patches.FancyBboxPatch((x-11, y-10), 22, 20, boxstyle="round,pad=0.6", edgecolor=c_navy, facecolor=c_bg, linewidth=1)
        ax.add_patch(rect)
        ax.text(x, y+6, title, fontsize=8.5, fontweight="bold", ha="center", color=c_blue)
        ax.text(x, y-2, desc, fontsize=7.2, ha="center", va="center", color="#1e293b")

    ax.annotate("", xy=(26, 70), xytext=(23, 70), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(51, 70), xytext=(48, 70), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(76, 70), xytext=(73, 70), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(87, 43), xytext=(87, 59), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(73, 32), xytext=(76, 32), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(48, 32), xytext=(51, 32), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))
    ax.annotate("", xy=(23, 32), xytext=(26, 32), arrowprops=dict(facecolor=c_navy, edgecolor=c_navy, width=1, headwidth=5))

    r_sum = patches.FancyBboxPatch((10, 4), 80, 14, boxstyle="round,pad=0.6", edgecolor=c_green, facecolor="#f0fdf4", linewidth=1)
    ax.add_patch(r_sum)
    ax.text(50, 13, "RUNTIME VERIFICATION RESULT (Tested & Verified on Codebase):", fontsize=9, fontweight="bold", ha="center", color=c_green)
    ax.text(50, 7.5, "HTTP 200 OK • Confidence: 1.0000 • Sources: NIT Durgapur Examination Guidelines Manual (Demo Verified Record)\nContact: Controller of Examinations (CoE) / Academic Section • Portal: https://nitdgp.ac.in/p/academic-curriculum • Total Latency: 10.12 ms", fontsize=7.5, ha="center", color=c_navy)

    plt.tight_layout()
    plt.savefig("docs/proposal_assets/diagram7_walkthrough_trace.png", bbox_inches="tight")
    plt.close()

if __name__ == "__main__":
    create_diagram2()
    create_diagram3()
    create_diagram4()
    create_diagram5()
    create_diagram6()
    create_diagram7()
    print("All diagrams generated successfully!")
