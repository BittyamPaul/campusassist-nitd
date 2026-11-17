# CampusAssist Architecture & Engineering Guide

**Domain-Specific AI Student Assistant for National Institute of Technology Durgapur**  
*Department of Computer Science & Engineering*  
*Project Owner: Bittyam Paul*

---

## 1. System Vision & Core Guarantees

CampusAssist is engineered to resolve a critical challenge in campus AI assistants: **preventing policy hallucination**.

Unlike generic chatbots that guess or summarize third-party websites, CampusAssist strictly binds institution-specific answers to an authoritative, human-verified **NIT Durgapur Knowledge Repository**.

### Core Tenet: Intent Mapping Over Exact Keyword Matching
Students express identical needs with completely different words:
- *"How can I apply for hostel leave?"*
- *"I want to go home for two days. What should I do?"*
- *"Can I leave the hostel this weekend?"*
- *"What permission do I need to go home?"*

All of the above map to the single intent: `hostel -> hostel_leave`.

---

## 2. Component Diagram

```
                        CAMPUSASSIST ARCHITECTURE
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              CLIENT LAYER                              │
 │   Student Chat UI (Vanilla JS/CSS)  │  Admin Portal (Bootstrap-free)   │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP (REST & SSR)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                             BACKEND LAYER                              │
 │   Flask Application Factory (create_app)                               │
 │   ├── Main Routes: /, /admin/*                                         │
 │   ├── API Routes: /api/chat, /api/suggestions, /api/feedback          │
 │   └── Admin API: /api/admin/knowledge, /api/admin/unresolved, /stats  │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
 ┌──────────────────────────────────────┐     ┌─────────────────────────────────┐
 │       RETRIEVAL & AI PIPELINE        │     │         STORAGE LAYER           │
 │ 1. Query Normalization               │     │ SQLite (campusassist.db)        │
 │ 2. Vectorization / Embeddings        │     │ ├── topics                      │
 │ 3. Cosine Similarity Matching        │     │ ├── intents                     │
 │ 4. Confidence Threshold Circuit      │◄───►│ ├── knowledge_items (verified)  │
 │ 5. Controlled LLM / Grounded Prompt  │     │ ├── sample_queries (training)   │
 │ 6. Unresolved Query Logger           │     │ ├── unresolved_queries (triage) │
 └──────────────────────────────────────┘     │ ├── admin_users                 │
                                              │ ├── chat_logs                   │
                                              │ └── audit_logs                  │
                                              └─────────────────────────────────┘
```

---

## 3. Safe Fallback & Continuous Improvement Loop

```
Student Query
      │
      ▼
Semantic Similarity Match
      │
      ├────────────────────────────────────┐
      ▼ (Confidence >= Threshold)          ▼ (Confidence < Threshold)
 Authoritative Knowledge Retrieved       Safe Fallback Response Returned
      │                                    │
      ▼                                    ▼
 Controlled LLM Synthesizer              Query Logged to unresolved_queries Queue
      │                                    │
      ▼                                    ▼
 Natural Language Answer to Student      Admin Reviews & Triages in Portal
                                           │
                                           ├── Option A: Link to existing intent
                                           └── Option B: Publish new verified rule
                                           │
                                           ▼
                                         Knowledge Repository Updated
                                         (Future similar queries immediately resolve)
```
