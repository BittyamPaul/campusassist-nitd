"""
CampusAssist: Code Panel Generator
Generates clean, legible code evidence panels for the academic proposal.
"""

import os
import matplotlib.pyplot as plt

os.makedirs("docs/proposal_assets", exist_ok=True)

panels = [
    {
        "filename": "docs/proposal_assets/code_stage1_frontend_submission.png",
        "title": "Stage 1: Frontend Submission & Event Handling (app/static/js/chat.js)",
        "source": "app/static/js/chat.js",
        "start": 140,
        "end": 175,
    },
    {
        "filename": "docs/proposal_assets/code_stage2_api_endpoint.png",
        "title": "Stage 2: Backend REST Endpoint & Rate Limiting (app/routes/api_routes.py)",
        "source": "app/routes/api_routes.py",
        "start": 81,
        "end": 120,
    },
    {
        "filename": "docs/proposal_assets/code_stage3_intent_classification.png",
        "title": "Stage 3: Stemmed TF-IDF Intent Classification (app/services/classifier/intent_classifier.py)",
        "source": "app/services/classifier/intent_classifier.py",
        "start": 164,
        "end": 204,
    },
    {
        "filename": "docs/proposal_assets/code_stage4_semantic_retrieval.png",
        "title": "Stage 4: Semantic Retrieval Coordination (app/services/retrieval/semantic_search.py)",
        "source": "app/services/retrieval/semantic_search.py",
        "start": 170,
        "end": 208,
    },
    {
        "filename": "docs/proposal_assets/code_stage5_vector_store_dotproduct.png",
        "title": "Stage 5: In-Memory NumPy Dot Product Cosine Search (app/services/retrieval/vector_store.py)",
        "source": "app/services/retrieval/vector_store.py",
        "start": 113,
        "end": 156,
    },
    {
        "filename": "docs/proposal_assets/code_stage6_grounded_prompt_builder.png",
        "title": "Stage 6: Bounded Grounded Prompt Builder (app/services/llm/prompt_builder.py)",
        "source": "app/services/llm/prompt_builder.py",
        "start": 40,
        "end": 80,
    },
    {
        "filename": "docs/proposal_assets/code_stage7_circuit_breaker_triage.png",
        "title": "Stage 7: Zero-Hallucination Circuit Breaker & Triage (app/services/chat_service.py)",
        "source": "app/services/chat_service.py",
        "start": 309,
        "end": 350,
    },
    {
        "filename": "docs/proposal_assets/code_stage8_response_persistence.png",
        "title": "Stage 8: Assistant Message DB Persistence & Telemetry (app/services/chat_service.py)",
        "source": "app/services/chat_service.py",
        "start": 254,
        "end": 298,
    },
]

for p in panels:
    with open(p["source"], "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    
    selected = all_lines[p["start"]-1 : p["end"]]
    numbered_lines = [f"{p['start']+i:3d} | {line.rstrip()[:95]}" for i, line in enumerate(selected)]
    code_text = "\n".join(numbered_lines)

    # Render figure
    fig_height = max(5, len(numbered_lines) * 0.22 + 1.2)
    fig, ax = plt.subplots(figsize=(11, fig_height), dpi=220)
    ax.set_facecolor("#1e293b")
    fig.patch.set_facecolor("#1e293b")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Header bar
    ax.text(2, 95, p["title"], fontsize=10.5, fontweight="bold", color="#38bdf8", family="monospace")
    ax.plot([0, 100], [91, 91], color="#334155", lw=1)

    # Code body
    ax.text(2, 87, code_text, fontsize=8.2, color="#f1f5f9", family="monospace", va="top")

    plt.tight_layout()
    plt.savefig(p["filename"], bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"Generated code panel: {p['filename']}")

print("All code evidence panels generated successfully!")
