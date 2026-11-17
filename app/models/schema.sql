-- ==========================================================
-- CampusAssist: NIT Durgapur Domain Assistant Database Schema
-- Complete Relational Specification with Constraints & Indexes
-- ==========================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------
-- 1. USERS & ADMINISTRATORS TABLE
-- Supports authentication, authorization, and role management
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('superadmin', 'admin', 'reviewer', 'student')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- 2. TOPICS TABLE
-- High-level domain categories (e.g., Hostel, Academics)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT DEFAULT 'folder',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- 3. INTENTS TABLE
-- Specific user intentions under each topic
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS intents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- 4. VERIFIED KNOWLEDGE ITEMS TABLE
-- Authoritative, human-verified NIT Durgapur institutional information
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    intent_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT NOT NULL,
    keywords TEXT,
    source_reference TEXT,
    contact_authority TEXT,
    official_portal_url TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified' CHECK(verification_status IN ('verified', 'draft', 'archived', 'rejected')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    version INTEGER NOT NULL DEFAULT 1,
    verified_by TEXT NOT NULL,
    last_verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- 5. SAMPLE QUERIES TABLE
-- Alternative user phrasings for training semantic search
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sample_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL,
    query_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_id) REFERENCES intents(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------
-- 6. CONVERSATIONS TABLE
-- Tracks conversational sessions
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    title TEXT DEFAULT 'New Conversation',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------
-- 7. MESSAGES TABLE
-- Individual messages within conversations
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    matched_intent_id INTEGER,
    matched_knowledge_id INTEGER,
    confidence_score REAL DEFAULT 0.0,
    is_verified INTEGER DEFAULT 0 CHECK(is_verified IN (0, 1)),
    feedback TEXT DEFAULT NULL CHECK(feedback IN ('helpful', 'unhelpful', NULL)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_intent_id) REFERENCES intents(id) ON DELETE SET NULL,
    FOREIGN KEY (matched_knowledge_id) REFERENCES knowledge_items(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------
-- 8. UNRESOLVED QUERIES TABLE
-- Queue for sub-threshold student questions awaiting staff review
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS unresolved_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_question TEXT NOT NULL,
    conversation_id TEXT,
    predicted_topic TEXT,
    predicted_intent TEXT,
    classification_confidence REAL DEFAULT 0.0,
    retrieval_confidence REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    retrieval_info TEXT,
    status TEXT NOT NULL DEFAULT 'unresolved' CHECK(status IN ('unresolved', 'under_review', 'verified', 'rejected', 'closed', 'pending', 'reviewed', 'resolved', 'ignored')),
    review_status TEXT NOT NULL DEFAULT 'unresolved' CHECK(review_status IN ('unresolved', 'under_review', 'verified', 'rejected', 'closed', 'pending', 'reviewed', 'resolved', 'ignored')),
    resolution_intent_id INTEGER,
    admin_notes TEXT,
    reviewed_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    FOREIGN KEY (resolution_intent_id) REFERENCES intents(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------
-- 9. AUDIT LOGS TABLE
-- Traceability for all knowledge updates, reviews, and admin actions
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_username TEXT NOT NULL,
    actor_role TEXT DEFAULT 'admin',
    action TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id INTEGER,
    changes_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- INDEXES FOR HIGH RETRIEVAL PERFORMANCE
-- ----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_intents_topic ON intents(topic_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_intent ON knowledge_items(intent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_items(topic_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_lookup ON knowledge_items(is_active, verification_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_updated ON knowledge_items(updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_sample_queries_intent ON sample_queries(intent_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv_created ON messages(conversation_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role_verified ON messages(role, is_verified);
CREATE INDEX IF NOT EXISTS idx_unresolved_status ON unresolved_queries(status);
CREATE INDEX IF NOT EXISTS idx_unresolved_review_status ON unresolved_queries(review_status);
CREATE INDEX IF NOT EXISTS idx_unresolved_conv ON unresolved_queries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_logs(target_entity, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_username);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);

