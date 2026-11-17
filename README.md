# CampusAssist: AI-Powered Student Assistant for NIT Durgapur

> **Official Institutional Domain Assistant**  
> Department of Computer Science & Engineering, National Institute of Technology Durgapur  
> Project Owner: **Bittyam Paul**

---

## 1. Project Title
**CampusAssist — Domain-Specific AI Assistant for the National Institute of Technology Durgapur**

---

## 2. Project Description
**CampusAssist** is an intelligent, authoritative, and hallucination-resistant conversational assistant designed specifically for students, faculty, and administrative staff of the **National Institute of Technology Durgapur (NIT Durgapur)**. 

Unlike general-purpose conversational chatbots that guess institutional policies or confabulate deadlines, CampusAssist operates under a strict **Verification Hierarchy**: it synthesizes natural-language answers **exclusively** from human-verified institute records stored in a local SQLite Knowledge Repository. If an official answer is not verified or falls below confidence thresholds, the system activates a fail-safe circuit breaker, refuses to fabricate information, and routes the question to an administrative review triage queue for staff verification.

---

## 3. Problem Statement
1. **Hallucination & Policy Invention**: Commercial LLMs (ChatGPT, Gemini, Claude) lack internal access to localized, up-to-date NIT Durgapur circulars. When asked about hostel curfews, mess rebates, or supplementary exam rules, generic models hallucinate rules or quote regulations from other IITs/NITs.
2. **Linguistic Diversity & Slang**: Engineering students express identical institutional questions in hundreds of different colloquial forms (*"Can I go home this weekend?"*, *"Warden permission for night out"*, *"Hostel gate pass procedure"*). Traditional keyword search fails when students use conversational phrasing.
3. **Scattered Institutional Information**: Official procedures are scattered across PDFs, department noticeboards, hostel caretaker desks, and ERP portals (Chanakya). Freshmen and senior students alike waste hours tracking down basic procedural steps.
4. **No Feedback Loop**: When students cannot find an answer on institute portals, their queries go unrecorded. Administrative departments have no systematic visibility into the common ambiguities students face.

---

## 4. Proposed Solution
CampusAssist solves these challenges through a **Domain-Grounded Retrieval-Augmented Generation (RAG)** architecture:
- **Zero Institutional Fabrication**: The Large Language Model (LLM) is constrained by system prompts and programmatic circuit breakers to act solely as a natural-language synthesizer. It cannot invent rules.
- **Semantic Understanding**: Dense vector embeddings and intent classification map multi-phrased questions to canonical institute topics and intents without requiring exact keyword matches.
- **Closed-Loop Administrative Triage**: Unknown and low-confidence queries are automatically cataloged in an administrative dashboard. Staff can verify the official procedure in one click, instantly re-indexing the semantic search engine so future students receive authoritative answers immediately.
- **100% Offline Resilience**: If internet connectivity drops or cloud AI services fail, CampusAssist automatically falls back to an offline local TF-IDF dense embedding engine and a deterministic response synthesizer.

---

## 5. Core Concepts Explained (CSE Student Reference)

If you are a Computer Science student reviewing this codebase, the following concepts define how CampusAssist operates:

```
+---------------------------------------------------------------------------------------+
|                                    CORE TAXONOMY                                      |
|                                                                                       |
|   [ Topic: Hostel Life ]                                                              |
|        │                                                                              |
|        ├── [ Intent: hostel_leave ] ──> [ Knowledge Item: Gate Pass & Leave Rules ]   |
|        │                                 ├── Canonical Procedure                      |
|        │                                 ├── Required Documents                       |
|        │                                 ├── Authority Contact                        |
|        │                                 └── Official Portal Link                     |
|        └── [ Intent: room_change ]   ──> [ Knowledge Item: Mutual Swap Rules ]        |
+---------------------------------------------------------------------------------------+
```

### 🏷️ Topic
A **Topic** is a high-level operational domain within the institute (e.g., `Hostel Life`, `Academics & Examination`, `Campus Facilities`). In the database, topics act as the primary category for organizing intents and permissions.

### 🎯 Intent
An **Intent** represents the specific objective or underlying goal of a student's query (e.g., `hostel_leave`, `course_registration`, `grade_card`, `mess_complaint`). Multiple different student questions (*"How do I take leave?"*, *"Can I visit home for 2 days?"*) map to the exact same intent.

### 🔍 Semantic Search
Unlike lexical search (which checks if words like "hostel" or "leave" appear verbatim), **Semantic Search** projects text into high-dimensional vector space. It calculates the **cosine similarity** between the student's query vector and indexed knowledge vectors. This allows the system to recognize that *"I need to go home for my sister's wedding"* is semantically identical to *"Hostel Leave Application Procedure"*.

### 📚 Knowledge Repository
The **Knowledge Repository** is the relational database of authoritative, human-verified NIT Durgapur records. Each entry includes:
- Canonical Title and Summary
- Step-by-Step Procedure
- Required Documents
- Responsible Authority (Warden, Dean Academic, Chief Warden)
- Official Portal URL (e.g., Chanakya ERP)
- Verification metadata (Admin username, verification timestamp, active toggle)

### 🧬 Embedding
An **Embedding** is an array of floating-point numbers (a dense vector) that mathematically encodes the semantic meaning of a piece of text. 
- In **Cloud Mode**, CampusAssist uses Google Gemini's `models/text-embedding-004` (768 dimensions).
- In **Offline Mode**, CampusAssist uses a custom domain-fitted TF-IDF dense vectorizer with sublinear term-frequency scaling and token suffix stemming (zero external network dependency).

### 🧩 Retrieved Context
The **Retrieved Context** is the set of verified knowledge snippets retrieved from the vector store that pass the similarity threshold gate ($\ge 0.50$). This context is injected into the LLM prompt as the **sole source of truth**.

### 🤖 LLM (Large Language Model)
The **LLM** (Google Gemini 2.5 Flash / 1.5 Flash) acts as a strict synthesizer. It translates structured institutional records into polite, clear, student-friendly explanations. Under CampusAssist's prompt directives, the LLM is explicitly forbidden from introducing outside facts. If the cloud API is unavailable, the `DeterministicFallbackProvider` generates formatted answers without an LLM.

### ❓ Unknown Query
When a student question achieves a retrieval similarity score below the threshold ($< 0.50$), it is categorized as an **Unknown Query**. The system triggers a circuit breaker: it delivers a polite unverified notice to the student and silently writes the query to the triage table with predicted intent and classification confidence.

### 🛡️ Admin Verification
**Admin Verification** is the human-in-the-loop workflow. Institute administrators inspect unresolved queries in the admin portal, enter or edit the official policy, set `verification_status = 'verified'`, and trigger in-memory re-indexing.

---

## 6. Features
- **Student Conversational Interface**:
  - Natural multi-turn dialogue with conversation history persistence.
  - Contextual follow-up understanding (*"What is the hostel leave procedure?"* $\rightarrow$ *"How long can I take it for?"*).
  - High-contrast accessible design (WCAG AA compliant Slate palette).
  - Responsive mobile drawer with backdrop blur and touch optimization.
  - Keyboard navigation (`Enter` to submit, `Shift + Enter` for newlines, `Escape` to close drawers/alerts).
  - Helpful / Unhelpful student feedback buttons on assistant responses.
  - Verified source attribution pills, contact authorities, and official portal links.
- **Administrative Portal**:
  - Secure PBKDF2 password hashing and session management.
  - Analytical metrics (total queries, verification resolution rate, knowledge counts).
  - Knowledge Base CRUD (create, edit, verify, activate/deactivate, version tracking).
  - Unresolved query queue with triage workflow (Under Review $\rightarrow$ Verified $\rightarrow$ Closed).
  - Real-time in-memory index synchronization (knowledge updates become searchable instantly).
  - Complete tamper-evident audit logging of all administrative modifications.
- **Security & Reliability**:
  - Zero institutional policy fabrication (circuit breaker for unknown queries).
  - Anti-CSRF synchronizer tokens on web forms.
  - Sliding-window rate limiting on login and chat endpoints.
  - Sanitized error handlers with zero stack trace or internal path leakage.
  - Comprehensive input bounds validation and path traversal sanitization.
  - Redaction of API keys and passwords from application logs.
- **High-Performance Architecture**:
  - SQLite Write-Ahead Logging (WAL) and memory cache PRAGMAs.
  - Composite indexes on message history, conversation timestamps, and audit records.
  - In-memory bounded LRU caches for embeddings, intent classification, and retrieval.
  - Sub-microsecond component timing instrumentation.

---

## 7. Architecture Diagram

```
                              STUDENT BROWSER
                     (HTML5 / CSS3 / Vanilla JavaScript)
                                     │
                                     │  HTTPS / JSON
                                     ▼
                     ┌───────────────────────────────┐
                     │         FLASK ROUTER          │
                     │  (api_routes.py / main_routes)│
                     │  - Sliding Rate Limiter       │
                     │  - CSRF Token Validation      │
                     │  - Input Bounds Sanitizer     │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │      CHAT PIPELINE SERVICE    │
                     │       (chat_service.py)       │
                     └───────┬───────────────┬───────┘
                             │               │
             ┌───────────────┘               └───────────────┐
             ▼                                               ▼
┌─────────────────────────┐                     ┌─────────────────────────┐
│  INTENT CLASSIFIER      │                     │ CONTEXT MANAGER         │
│  (intent_classifier.py) │                     │ (context_manager.py)    │
│  - Stem Tokenizer       │                     │ - Multi-turn History    │
│  - Sublinear TF-IDF     │                     │ - Follow-up Resolution  │
│  - Calibrated Confidence│                     └─────────────────────────┘
└────────────┬────────────┘                                  │
             │                                               ▼
             ▼                                  ┌─────────────────────────┐
┌─────────────────────────┐                     │ SEMANTIC RETRIEVAL      │
│ EMBEDDING PROVIDER      │────────────────────>│ (semantic_search.py)    │
│ - Gemini Embeddings     │  Dense Vector (1D)  │ - In-Memory Vector Store│
│ - Local TF-IDF Dense    │                     │ - Cosine Similarity     │
│ - Bounded Vector Cache  │                     │ - Threshold Gating (0.5)│
└─────────────────────────┘                     └────────────┬────────────┘
                                                             │
                             ┌───────────────────────────────┴───────────────────────────────┐
                             │                                                               │
                             ▼ (Score >= 0.50: Sufficient)                                   ▼ (Score < 0.50: Insufficient)
              ┌─────────────────────────────┐                                 ┌─────────────────────────────┐
              │     CONTROLLED LLM SERVICE  │                                 │     CIRCUIT BREAKER         │
              │  - Strict Grounding Prompt  │                                 │  - Safe Fallback Generator  │
              │  - Verified Context Only    │                                 │  - Zero Hallucination Notice│
              │  - Gemini 2.5 Flash / Local │                                 │  - Log to Unresolved Table  │
              └──────────────┬──────────────┘                                 └──────────────┬──────────────┘
                             │                                                               │
                             └───────────────────────────────┬───────────────────────────────┘
                                                             │
                                                             ▼
                                              ┌─────────────────────────────┐
                                              │     SQLITE REPOSITORY       │
                                              │  (campusassist.db - WAL)    │
                                              │  - Messages & Conversations │
                                              │  - Verified Knowledge Items │
                                              │  - Unresolved Queries Queue │
                                              │  - Audit Logs & Users       │
                                              └─────────────────────────────┘
```

---

## 8. Complete Student Query Workflow (14 Steps)

```
Student Question 
  │
  ├─ 1. Receive query via POST /api/chat
  ├─ 2. Validate input bounds (non-empty, string type, <= 1500 chars)
  ├─ 3. Initialize or resume persistent conversational session (UUID)
  ├─ 4. Store student message in SQLite 'messages' table
  ├─ 5. Preprocess query (lowercase, expand contractions, strip punctuation)
  ├─ 6. Classify Topic and Intent with calibrated confidence scoring
  ├─ 7. Generate L2-normalized dense embedding vector (with cache check)
  ├─ 8. Perform cosine similarity search across in-memory vector store
  ├─ 8b. If low confidence, evaluate prior turns for contextual follow-up
  ├─ 9. Gate retrieved candidates by confidence threshold (threshold = 0.50)
  ├─ 10. Check information sufficiency:
  │      ├─ SUFFICIENT (Score >= 0.50):
  │      │    ├─ 11. Format grounded prompt containing ONLY verified knowledge
  │      │    ├─ 12. Synthesize student answer using controlled LLM
  │      │    └─ 13. Persist assistant message with verified=1
  │      └─ INSUFFICIENT (Score < 0.50):
  │           ├─ 11. Activate zero-hallucination circuit breaker
  │           ├─ 12. Construct friendly unverified notice with contact guidance
  │           └─ 13. Log question to 'unresolved_queries' triage queue
  └─ 14. Return structured JSON with answer, sources, portal URLs, and latency timings
```

---

## 9. Unknown-Query Workflow

When a student asks an unseeded or out-of-domain question (e.g., *"How do I register for a drone workshop?"*):

```
Student Question: "How do I register for a drone workshop?"
                       │
                       ▼
          Semantic Similarity Score = 0.22 (< 0.50)
                       │
                       ▼
          [ ZERO-HALLUCINATION CIRCUIT BREAKER ]
                       │
         ┌─────────────┴────────────────┐
         ▼                              ▼
[ Friendly Student Notice ]    [ Unresolved Query Logged ]
"We could not confirm verified   - Original question
 NIT Durgapur records for this    - Predicted topic & intent
 specific request. Your question - Confidence score
 has been forwarded to staff."   - Session reference
                                 - Status: 'unresolved'
```

Students never see raw database errors, internal confidence numbers, or administrative flags.

---

## 10. Knowledge Improvement Workflow

When an administrator reviews and resolves a pending query:

```
                  ADMINISTRATOR PORTAL
                           │
  1. Inspect Unresolved Query in Queue
  2. Verify Official NIT Durgapur Procedure
  3. Enter Canonical Title, Procedure, Documents & Portal URL
  4. Click "Verify & Add Knowledge"
                           │
                           ▼
              [ KNOWLEDGE REPOSITORY ]
    - Insert new record into 'knowledge_items'
    - Mark verification_status = 'verified', is_active = 1
    - Add original question as 'sample_query'
    - Record entry in 'audit_logs'
                           │
                           ▼
          [ AUTOMATIC IN-MEMORY RE-INDEXING ]
    - Clear vector cache & classification cache
    - Generate new embeddings for knowledge & sample queries
    - Rebuild contiguous vector dot-product matrix
    - Retrain intent classifier in RAM
                           │
                           ▼
                   FUTURE STUDENTS
   Differently worded queries now retrieve verified knowledge instantly!
```

---

## 11. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Backend Framework** | Python 3.11 / Flask | Lightweight, modular application factory, fast startup. |
| **Database** | SQLite 3 (WAL mode) | Zero external database server to manage; concurrent readers/writers via WAL. |
| **Vector Search** | In-Memory Vector Store / NumPy | Sub-millisecond matrix dot products without heavy vector DB dependencies. |
| **Local Embeddings** | scikit-learn (TF-IDF Dense) | Fully offline, deterministic vector representation with token stemming. |
| **Cloud Embeddings** | Google Gemini `text-embedding-004` | High-quality 768-dimensional semantic embeddings. |
| **Language Model** | Google Gemini 2.5 Flash / 1.5 Flash | High-speed, cost-effective, strictly grounded generation. |
| **Local LLM Fallback** | Deterministic Rule Synthesizer | 100% offline fallback when API key is unset or network drops. |
| **Security** | Werkzeug PBKDF2 / secrets / HMAC | Production-grade password hashing, session tokens, and timing-safe checks. |
| **Frontend** | HTML5 / CSS3 / Vanilla JavaScript | High performance, zero compilation steps, no bulky frontend frameworks. |
| **Testing** | pytest / pytest-mock | Automated test suite covering 18 test files and 150 test cases. |

---

## 12. Directory Structure

```
campusassist-nitd/
├── .env.example                  # Environment configuration template
├── config.py                     # Centralized application settings & security guards
├── manage_admin.py               # Administrator management CLI tool
├── pytest.ini                    # Pytest test discovery configuration
├── requirements.txt              # Production and test Python dependencies
├── run.py                        # Web application entry point
├── seed_db.py                    # Database creation & demo knowledge seeder
├── README.md                     # Comprehensive documentation
│
├── app/                          # Core application package
│   ├── __init__.py               # Application factory, security headers & error handlers
│   ├── models/                   # Database access layer
│   │   ├── db.py                 # SQLite connection manager, PRAGMAs & migrations
│   │   ├── repositories.py       # SQL repository functions (CRUD, stats, conversations)
│   │   └── schema.sql            # Relational schema (tables, foreign keys & indexes)
│   ├── routes/                   # HTTP controller blueprints
│   │   ├── admin_routes.py       # Admin web views and REST APIs
│   │   ├── api_routes.py         # Student chat, conversation & feedback APIs
│   │   └── main_routes.py        # Web views (Student chat & Admin login)
│   ├── services/                 # Business logic services
│   │   ├── admin_service.py      # Dashboard analytics & triage workflow
│   │   ├── auth_decorators.py    # RBAC route protection decorators
│   │   ├── auth_service.py       # Admin authentication & session security
│   │   ├── chat_service.py       # 14-step chat pipeline orchestrator
│   │   ├── context_manager.py    # Multi-turn conversational follow-up resolver
│   │   ├── csrf.py               # Anti-CSRF token generator & verifier
│   │   ├── knowledge_service.py  # Knowledge item lifecycle manager
│   │   ├── rate_limiter.py       # Sliding-window in-memory rate limiter
│   │   ├── security_utils.py     # Safe URL validation & identifier sanitizers
│   │   ├── classifier/           # Topic & intent classification
│   │   │   └── intent_classifier.py # Stem-aware classifier with caching
│   │   ├── embeddings/           # Embedding providers
│   │   │   ├── base.py           # Abstract BaseEmbeddingProvider
│   │   │   ├── gemini_provider.py# Google Gemini embedding provider with cache
│   │   │   └── local_provider.py # Offline TF-IDF dense provider with cache
│   │   ├── llm/                  # Language model services
│   │   │   ├── logger_sanitizer.py # Secret and API key redacting logger
│   │   │   ├── prompt_builder.py # Grounding system prompt builder
│   │   │   ├── providers.py      # Gemini API, Mock, and Deterministic providers
│   │   │   └── service.py        # LLM service orchestrator & timeout failover
│   │   └── retrieval/            # Semantic vector retrieval
│   │       ├── search.py         # SearchResult & RetrievalResult data structures
│   │       ├── semantic_search.py# Semantic retrieval engine with caching
│   │       └── vector_store.py   # In-memory NumPy vector store
│   ├── static/                   # Static assets
│   │   ├── css/                  # Base styles, chat styles & admin styles
│   │   ├── js/                   # Chat UI controller & Admin portal logic
│   │   └── images/               # Institute SVG logo
│   └── templates/                # Jinja2 HTML templates
│       ├── base.html             # Master layout with responsive navbar & footer
│       ├── chat.html             # Student chat layout with suggestion chips
│       └── admin/                # Admin portal views (login, dashboard, knowledge, triage)
│
├── data/                         # Persistent database assets
│   ├── campusassist.db           # SQLite database file
│   └── seed_knowledge.json       # Seed data for Hostel & Academics
│
└── tests/                        # Comprehensive automated test suite (150 tests)
    ├── test_admin_auth.py
    ├── test_admin_dashboard.py
    ├── test_admin_retrieval_sync.py
    ├── test_chat_pipeline.py
    ├── test_comprehensive_suite.py
    ├── test_conversation_management.py
    ├── test_database_layer.py
    ├── test_error_handling.py
    ├── test_intent_classifier.py
    ├── test_knowledge_repository.py
    ├── test_llm_service.py
    ├── test_performance_optimization.py
    ├── test_phase1_database.py
    ├── test_security_audit.py
    ├── test_semantic_retrieval.py
    ├── test_server_boot.py
    ├── test_student_interface.py
    └── test_unknown_query_workflow.py
```

---

## 13. Installation

### Prerequisites
- Python 3.10 or higher (Tested on Python 3.11.9)
- Git

### Setup Steps
```powershell
# 1. Clone the repository
git clone https://github.com/bittyam/campusassist-nitd.git
cd campusassist-nitd

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create local environment file
copy .env.example .env
```

---

## 14. Environment Variables

Configure `.env` as required:

| Variable | Default Value | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | *(Built-in Dev Key)* | Secret key for session encryption. **Required in production.** |
| `FLASK_ENV` | `development` | Environment mode (`development`, `production`, `testing`). |
| `DATABASE_PATH` | `data/campusassist.db` | Relative or absolute path to the SQLite database file. |
| `CONFIDENCE_THRESHOLD` | `0.55` | Similarity score threshold ($0.0$ to $1.0$). Below this, queries trigger circuit breaker. |
| `LLM_PROVIDER` | `gemini` (or `deterministic`) | Provider to use: `gemini` (cloud) or `deterministic` (100% offline). |
| `LLM_MODEL` | `gemini-1.5-flash` | Gemini model name for grounded answer synthesis. |
| `GEMINI_API_KEY` | `""` | Google Gemini API key. If left blank, offline fallback activates automatically. |
| `ADMIN_INITIAL_USERNAME`| `admin` | Username for seed administrator provisioning. |
| `ADMIN_INITIAL_PASSWORD`| `""` | Initial password (if left blank, auto-generates a secure random password). |
| `SESSION_COOKIE_SECURE` | `False` | Enforce HTTPS cookies (set to `True` in production). |

---

## 15. Database Setup

CampusAssist uses a normalized SQLite relational schema configured with Write-Ahead Logging (WAL) for high concurrency.

Initialize tables and apply schema:
```powershell
python seed_db.py
```
This command automatically:
1. Creates `data/campusassist.db`.
2. Applies `app/models/schema.sql`.
3. Creates all composite performance indexes.
4. Provisions the initial administrator account.
5. Populates verified initial knowledge and sample queries from `data/seed_knowledge.json`.

---

## 16. Knowledge Repository Setup

Verified institutional records are maintained in `data/seed_knowledge.json`. Each entry defines:
- Canonical topic and intent taxonomy.
- Human-verified procedures, required documents, authority contacts, and portal links.
- Sample query variations for intent training.

To re-seed or reload initial knowledge:
```powershell
python seed_db.py
```

To add or modify knowledge in production, use the **Administrator Dashboard** (`/admin/knowledge`) or the REST API. Knowledge added through the admin interface becomes searchable immediately without restarting the application.

---

## 17. Embedding Setup

CampusAssist supports dual embedding providers:

### Mode A: Google Gemini API (Recommended for Cloud Deployment)
- Set `GEMINI_API_KEY=AIzaSy...` in your `.env`.
- Uses `models/text-embedding-004` to generate 768-dimensional normalized vectors.
- Embeddings are cached in memory (512-entry FIFO cache) to prevent duplicate API calls.

### Mode B: Local Dense Vectorizer (100% Offline)
- If `GEMINI_API_KEY` is not provided, CampusAssist automatically falls back to `LocalEmbeddingProvider`.
- Uses sublinear TF-IDF vectorization with token stemming fitted on the institute knowledge corpus.
- Zero network requests; runs entirely on CPU with microsecond latency.

---

## 18. LLM Configuration

CampusAssist uses an isolated provider architecture:
- **Cloud LLM (`gemini`)**: Calls the Gemini API with structured system instructions forbidding policy fabrication. Requests timeout after 15 seconds.
- **Failover to Deterministic Synthesizer**: If the Gemini API key is missing, network fails, quota is exhausted (HTTP 429), or a response is blocked by safety filters, CampusAssist automatically routes the retrieved context to `DeterministicFallbackProvider`. Students always receive an accurate, formatted answer grounded in verified snippets.

---

## 19. Running Locally

Start the development server:
```powershell
python run.py
```

The application will launch at:
- **Student Assistant Interface**: `http://127.0.0.1:5000/`
- **Administrator Portal**: `http://127.0.0.1:5000/admin/login`
- **System Health Endpoint**: `http://127.0.0.1:5000/api/health`

---

## 20. Admin Setup & CLI Management

Administrators can be managed via the command line with `manage_admin.py`:

```powershell
# List existing administrative users
python manage_admin.py list

# Create a new administrator with auto-generated secure password
python manage_admin.py create --username registrar --role admin --display-name "Academic Registrar" --generate-password

# Create an administrator with explicit password
python manage_admin.py create --username warden_hall1 --role admin --password "StrongPassword123!"

# Reset password for an existing administrator
python manage_admin.py reset-password --username admin
```

*Note: Default administrative passwords are never committed to version control.*

---

## 21. Testing

The codebase includes an extensive automated test suite covering all layers:

```powershell
# Run the complete test suite (150 tests across 18 modules)
pytest tests/ -q

# Run with verbose output and test names
pytest tests/ -v

# Run the comprehensive subsystem and semantic invariance suite
pytest tests/test_comprehensive_suite.py -v

# Run the performance and benchmark test suite
pytest tests/test_performance_optimization.py -v -s
```

### Test Coverage Highlights
- **Semantic Understanding**: Verifies that multi-phrased queries (*"How do I apply for hostel leave?"* and *"I want to go home for two days, what permission do I need?"*) resolve to the identical intent (`hostel_leave`) and retrieve the exact same verified record.
- **Circuit Breaker**: Confirms out-of-domain queries return unverified fallback notices without inventing policies.
- **Security Audit**: Validates open redirect protection, CSRF validation, rate limiting, and zero traceback disclosure.

---

## 22. Troubleshooting

| Symptom / Error | Root Cause | Solution |
|---|---|---|
| **Port 5000 Already in Use** (`OSError: [Errno 98] Address already in use`) | Another instance of Flask or a background process is holding port 5000. | Terminate the existing process via Task Manager (Windows) or `kill $(lsof -t -i:5000)` (Linux/macOS), or run `python run.py` on a different port. |
| **`sqlite3.OperationalError: database is locked`** | Multiple processes writing simultaneously without WAL mode or an external DB viewer holds a write transaction open. | CampusAssist applies `PRAGMA journal_mode = WAL;` and `busy_timeout = 5000` automatically. Close any external SQLite GUI tools (e.g. DB Browser for SQLite) holding open locks. |
| **Gemini API Error / HTTP 429 Rate Limit** | Invalid Gemini API key, network timeout, or exhausted quota. | CampusAssist automatically fails over to `DeterministicFallbackProvider` and `LocalEmbeddingProvider`. To run 100% offline, leave `GEMINI_API_KEY=` blank in `.env` or set `LLM_PROVIDER=deterministic`. |
| **`RuntimeError: Production security error: FLASK_SECRET_KEY MUST be set`** | Running with `FLASK_ENV=production` without setting a custom secret key in `.env`. | Set a cryptographically secure random string for `FLASK_SECRET_KEY` in `.env` (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`). |
| **Forgot Admin Password** | Lost credentials for local administrator accounts. | Run `python manage_admin.py reset-password --username admin` to set a new password via the secure CLI. |
| **ModuleNotFoundError** | Dependencies not installed in the active virtual environment. | Verify virtual environment is active (`venv\Scripts\activate` or `source venv/bin/activate`) and run `pip install -r requirements.txt`. |
| **CSS / JS Changes Not Reflected** | Browser caching old static assets. | Perform a hard refresh (`Ctrl + F5` or `Cmd + Shift + R`) or open an Incognito window. |

---

## 23. Security & Privacy Controls
- **Zero Traceback Disclosure**: Global error handlers catch 400, 401, 403, 404, 413, 429, and 500 exceptions, returning friendly sanitized responses with zero stack trace or internal path leakage.
- **Password Security**: Passwords hashed using PBKDF2 with SHA-256 (`werkzeug.security.generate_password_hash`).
- **Session Protection**: Sessions configured with `HttpOnly`, `SameSite=Lax`, with an 8-hour lifetime. In production environments, `Secure` cookie flag is enforced.
- **Sliding-Window Rate Limiter**: In-memory sliding-window limiter enforcing 15 req/min on authentication and 60 req/min on student chat endpoints. Returns HTTP 429 with `Retry-After` header.
- **CSRF Defense**: State-changing web forms protected by cryptographic synchronizer tokens generated via `secrets.token_hex(32)`.
- **SQL Injection Prevention**: 100% of SQLite database queries use parameterized SQL bindings (`?`).
- **Secret Redaction**: Custom logging filter intercepts log records and redacts API keys, passwords, and tokens before writing to disk or console.

---

## 24. Limitations
1. **Scope Limited to Verified Records**: CampusAssist will not guess or extrapolate answers for unseeded domains. If a policy is not in the Knowledge Repository, it engages the unverified circuit breaker.
2. **Static Knowledge Updates**: While knowledge updates become searchable immediately without code changes, official changes to institute rules still require administrative staff to review and update the repository.
3. **Single Institute Scope**: Designed specifically for NIT Durgapur regulations; adapting to another university requires modifying the seed taxonomy and knowledge items.

---

## 25. Future Scope & Roadmap
1. **Direct Chanakya ERP Integration**: Authenticated student login to pull personalized fee payment status and registered course grades directly into the conversation.
2. **Automated Document OCR Ingestion**: Automatic parsing of scanned institute notices and circular PDFs with administrative approval queues.
3. **Multilingual Support**: Real-time Hindi and Bengali language translation for student queries and responses.
4. **Push Notifications**: Optional email or Telegram alerts to hostel wardens when unresolved emergency or maintenance queries are filed.

---

## 26. Important REST API Endpoints Reference

### 🎓 Student Endpoints

#### `POST /api/chat`
Process a student question through the 14-step retrieval and synthesis pipeline.
- **Request Body**:
  ```json
  {
    "query": "How can I apply for hostel leave?",
    "session_id": "session_abc123_1789300000"
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "status": "received",
    "success": true,
    "conversation_id": "session_abc123_1789300000",
    "query": "How can I apply for hostel leave?",
    "answer": "To apply for hostel leave at NIT Durgapur, follow these steps...",
    "is_verified": true,
    "topic": "Hostel Life",
    "intent": "Hostel Leave Application",
    "confidence": 0.8842,
    "sources": ["NIT Durgapur Hall Residence Rules Handbook"],
    "authority_contact": "Chief Warden / Respective Hall Wardens",
    "official_url": "https://nitdgp.ac.in",
    "latency_seconds": 0.0421,
    "timings_ms": {
      "classification": 0.05,
      "retrieval": 0.08,
      "llm": 12.4,
      "total": 13.5
    }
  }
  ```

#### `GET /api/suggestions`
Returns suggested prompts and explore cards for the student home screen.

#### `GET /api/conversations?limit=30`
Retrieves recent conversation sessions with last message preview and message counts.

#### `GET /api/conversations/<id>/messages`
Retrieves chronological message history for a conversation session.

#### `DELETE /api/conversations/<id>`
Deletes a conversation session and all associated messages.

#### `POST /api/feedback`
Records student satisfaction feedback (`helpful` or `unhelpful`) on an assistant message.
- **Request Body**:
  ```json
  {
    "message_id": 42,
    "feedback": "helpful"
  }
  ```

#### `GET /api/health`
Health check endpoint returning system status and timestamp.

---

### ⚙️ Administrator Endpoints (Protected)

*All admin endpoints require active administrator session authentication.*

#### `POST /api/admin/login`
Authenticates administrator credentials and establishes session.

#### `GET /api/admin/dashboard`
Returns analytical statistics, resolution rate, and recent audit logs.

#### `GET /api/admin/knowledge`
Lists, searches, and filters knowledge entries.

#### `POST /api/admin/knowledge`
Creates a new verified knowledge entry and automatically triggers in-memory re-indexing.

#### `PUT /api/admin/knowledge/<id>`
Updates an existing knowledge entry (increments version and re-indexes).

#### `GET /api/admin/unresolved`
Retrieves pending student queries awaiting staff review.

#### `POST /api/admin/unresolved/<id>/status`
Updates review status of an unresolved query (`under_review`, `verified`, `rejected`, `closed`).

#### `GET /api/admin/audit`
Retrieves recent administrative action audit trail logs.

---

*Developed for the students and administration of NIT Durgapur.*

