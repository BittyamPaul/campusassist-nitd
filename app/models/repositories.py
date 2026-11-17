"""
CampusAssist Database Repositories.
Data-access layer for users, conversations, messages, topics, intents,
knowledge items, sample queries, unresolved queries, and audit logs.
"""

from typing import List, Optional, Dict, Any
from app.models.db import get_db


# ============================================================================
# 1. USERS & ADMINISTRATORS REPOSITORY
# ============================================================================

def create_user(
    username: str,
    password_hash: str,
    display_name: str,
    role: str = "student",
    is_active: int = 1,
    conn=None
) -> int:
    """Create a user or administrator account."""
    db = conn or get_db()
    cursor = db.execute("""
        INSERT INTO users (username, password_hash, display_name, role, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, (username.strip().lower(), password_hash, display_name.strip(), role, is_active))
    db.commit()
    return cursor.lastrowid


def get_user_by_username(username: str, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by username."""
    db = conn or get_db()
    cursor = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username.strip().lower(),),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve user record by ID."""
    db = conn or get_db()
    cursor = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def update_user_last_login(user_id: int, conn=None) -> bool:
    """Update last login timestamp for user."""
    db = conn or get_db()
    cursor = db.execute(
        "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
        (user_id,)
    )
    db.commit()
    return cursor.rowcount > 0


def get_all_users(role: Optional[str] = None, conn=None) -> List[Dict[str, Any]]:
    """Retrieve users, optionally filtered by role."""
    db = conn or get_db()
    if role:
        cursor = db.execute("SELECT * FROM users WHERE role = ? ORDER BY created_at DESC", (role,))
    else:
        cursor = db.execute("SELECT * FROM users ORDER BY created_at DESC")
    return [dict(row) for row in cursor.fetchall()]


# Backward compatibility aliases for admin authentication
get_admin_by_username = get_user_by_username
get_admin_by_id = get_user_by_id


def create_admin_user(
    username: str,
    password_hash: str,
    display_name: str,
    role: str = "admin",
    conn=None
) -> int:
    """Alias to create an administrator user."""
    return create_user(
        username=username,
        password_hash=password_hash,
        display_name=display_name,
        role=role,
        is_active=1,
        conn=conn,
    )


# ============================================================================
# 2. TOPICS & INTENTS REPOSITORY
# ============================================================================

def get_all_topics(is_active: Optional[int] = 1, with_counts: bool = False, conn=None) -> List[Dict[str, Any]]:
    """Retrieve all knowledge categories/topics, optionally with counts and active filter."""
    db = conn or get_db()
    if with_counts:
        query = """
            SELECT t.*,
                   (SELECT COUNT(*) FROM intents i WHERE i.topic_id = t.id AND (i.is_active = 1 OR ? IS NULL)) AS intent_count,
                   (SELECT COUNT(*) FROM knowledge_items k WHERE k.topic_id = t.id AND (k.is_active = 1 OR ? IS NULL)) AS knowledge_count
            FROM topics t
        """
        params = [is_active, is_active]
        if is_active is not None:
            query += " WHERE t.is_active = ?"
            params.append(is_active)
        query += " ORDER BY t.name ASC"
        cursor = db.execute(query, params)
    else:
        if is_active is not None:
            cursor = db.execute("SELECT * FROM topics WHERE is_active = ? ORDER BY name ASC", (is_active,))
        else:
            cursor = db.execute("SELECT * FROM topics ORDER BY name ASC")
    return [dict(row) for row in cursor.fetchall()]


def get_topic_by_slug(slug: str, conn=None) -> Optional[Dict[str, Any]]:
    """Get a topic by slug."""
    db = conn or get_db()
    cursor = db.execute("SELECT * FROM topics WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_topic_by_id(topic_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Get a topic by ID."""
    db = conn or get_db()
    cursor = db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_topic(
    name: str,
    slug: str,
    description: str = "",
    icon: str = "folder",
    is_active: int = 1,
    conn=None
) -> int:
    """Create a new topic and return its ID."""
    db = conn or get_db()
    cursor = db.execute(
        "INSERT INTO topics (name, slug, description, icon, is_active) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), slug.strip(), description.strip(), icon.strip(), is_active),
    )
    db.commit()
    return cursor.lastrowid


def update_topic(
    topic_id: int,
    name: str,
    slug: str,
    description: str = "",
    icon: str = "folder",
    is_active: int = 1,
    conn=None
) -> bool:
    """Update topic fields."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE topics
        SET name = ?, slug = ?, description = ?, icon = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (name.strip(), slug.strip(), description.strip(), icon.strip(), is_active, topic_id))
    db.commit()
    return cursor.rowcount > 0


def get_intents_by_topic(topic_id: int, is_active: int = 1, conn=None) -> List[Dict[str, Any]]:
    """Retrieve all active intents under a specific topic."""
    db = conn or get_db()
    cursor = db.execute(
        "SELECT * FROM intents WHERE topic_id = ? AND is_active = ? ORDER BY name ASC",
        (topic_id, is_active),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_all_intents_with_topic(is_active: Optional[int] = 1, with_counts: bool = False, conn=None) -> List[Dict[str, Any]]:
    """Retrieve all intents with their topic name, optionally including counts."""
    db = conn or get_db()
    if with_counts:
        query = """
            SELECT i.*, t.name AS topic_name, t.slug AS topic_slug,
                   (SELECT COUNT(*) FROM sample_queries sq WHERE sq.intent_id = i.id) AS query_count,
                   (SELECT COUNT(*) FROM knowledge_items k WHERE k.intent_id = i.id) AS knowledge_count
            FROM intents i
            JOIN topics t ON i.topic_id = t.id
        """
        params = []
        if is_active is not None:
            query += " WHERE i.is_active = ? AND t.is_active = 1"
            params.append(is_active)
        query += " ORDER BY t.name ASC, i.name ASC"
        cursor = db.execute(query, params)
    else:
        if is_active is not None:
            cursor = db.execute("""
                SELECT i.*, t.name AS topic_name, t.slug AS topic_slug
                FROM intents i
                JOIN topics t ON i.topic_id = t.id
                WHERE i.is_active = ? AND t.is_active = 1
                ORDER BY t.name ASC, i.name ASC
            """, (is_active,))
        else:
            cursor = db.execute("""
                SELECT i.*, t.name AS topic_name, t.slug AS topic_slug
                FROM intents i
                JOIN topics t ON i.topic_id = t.id
                ORDER BY t.name ASC, i.name ASC
            """)
    return [dict(row) for row in cursor.fetchall()]


def get_intent_by_slug(slug: str, conn=None) -> Optional[Dict[str, Any]]:
    """Get an intent by its slug."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT i.*, t.name AS topic_name, t.slug AS topic_slug
        FROM intents i
        JOIN topics t ON i.topic_id = t.id
        WHERE i.slug = ?
    """, (slug,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_intent_by_id(intent_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Get an intent by its ID."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT i.*, t.name AS topic_name, t.slug AS topic_slug
        FROM intents i
        JOIN topics t ON i.topic_id = t.id
        WHERE i.id = ?
    """, (intent_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_intent(
    topic_id: int,
    name: str,
    slug: str,
    description: str = "",
    is_active: int = 1,
    conn=None
) -> int:
    """Create a new intent and return its ID."""
    db = conn or get_db()
    cursor = db.execute(
        "INSERT INTO intents (topic_id, name, slug, description, is_active) VALUES (?, ?, ?, ?, ?)",
        (topic_id, name.strip(), slug.strip(), description.strip(), is_active),
    )
    db.commit()
    return cursor.lastrowid


def update_intent(
    intent_id: int,
    name: str,
    slug: str,
    description: str = "",
    topic_id: Optional[int] = None,
    is_active: int = 1,
    conn=None
) -> bool:
    """Update intent fields, optionally reassigning parent topic."""
    db = conn or get_db()
    if topic_id is not None:
        cursor = db.execute("""
            UPDATE intents
            SET name = ?, slug = ?, description = ?, topic_id = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name.strip(), slug.strip(), description.strip(), topic_id, is_active, intent_id))
    else:
        cursor = db.execute("""
            UPDATE intents
            SET name = ?, slug = ?, description = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (name.strip(), slug.strip(), description.strip(), is_active, intent_id))
    db.commit()
    return cursor.rowcount > 0


# ============================================================================
# 3. KNOWLEDGE ITEMS REPOSITORY
# ============================================================================

def get_all_knowledge_items(
    status: Optional[str] = "verified",
    is_active: Optional[int] = 1,
    topic_id: Optional[int] = None,
    search_query: Optional[str] = None,
    conn=None
) -> List[Dict[str, Any]]:
    """Retrieve knowledge items with intent and topic metadata."""
    db = conn or get_db()
    query = """
        SELECT k.*, i.name AS intent_name, i.slug AS intent_slug,
               t.name AS topic_name, t.slug AS topic_slug
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
        WHERE 1=1
    """
    params = []
    if is_active is not None:
        query += " AND k.is_active = ?"
        params.append(int(is_active))
    if status:
        query += " AND k.verification_status = ?"
        params.append(status)
    if topic_id is not None:
        query += " AND k.topic_id = ?"
        params.append(int(topic_id))
    if search_query:
        query += " AND (k.title LIKE ? OR k.summary LIKE ? OR k.content LIKE ? OR k.keywords LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term, term, term])
    query += " ORDER BY t.name ASC, i.name ASC, k.title ASC"

    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def get_knowledge_by_intent(intent_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve verified active knowledge item for a given intent."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT k.*, i.name AS intent_name, i.slug AS intent_slug,
               t.name AS topic_name, t.slug AS topic_slug
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
        WHERE k.intent_id = ? AND k.verification_status = 'verified' AND k.is_active = 1
        ORDER BY k.version DESC, k.id DESC
        LIMIT 1
    """, (intent_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_knowledge_by_id(item_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve a single knowledge item by its ID."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT k.*, i.name AS intent_name, i.slug AS intent_slug,
               t.name AS topic_name, t.slug AS topic_slug
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
        WHERE k.id = ?
    """, (item_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_knowledge_item(
    topic_id: int,
    intent_id: int,
    title: str,
    content: str,
    summary: str,
    keywords: str = "",
    source_reference: str = "",
    contact_authority: str = "",
    official_portal_url: str = "",
    verified_by: str = "NIT Durgapur Verified Source",
    verification_status: str = "verified",
    version: int = 1,
    is_active: int = 1,
    conn=None
) -> int:
    """Insert a verified knowledge item."""
    db = conn or get_db()
    cursor = db.execute("""
        INSERT INTO knowledge_items (
            topic_id, intent_id, title, content, summary,
            keywords, source_reference, contact_authority, official_portal_url,
            verified_by, verification_status, version, is_active, last_verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        topic_id, intent_id, title.strip(), content.strip(), summary.strip(),
        keywords.strip(), source_reference.strip(), contact_authority.strip(), official_portal_url.strip(),
        verified_by.strip(), verification_status, version, is_active
    ))
    db.commit()
    return cursor.lastrowid


def update_knowledge_item(
    item_id: int,
    title: str,
    content: str,
    summary: str,
    keywords: str,
    source_reference: str,
    contact_authority: str,
    official_portal_url: str,
    verified_by: str,
    verification_status: str = "verified",
    is_active: int = 1,
    conn=None
) -> bool:
    """Update an existing knowledge item and increment its version."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE knowledge_items
        SET title = ?, content = ?, summary = ?, keywords = ?,
            source_reference = ?, contact_authority = ?, official_portal_url = ?,
            verified_by = ?, verification_status = ?, is_active = ?,
            version = version + 1,
            last_verified_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        title.strip(), content.strip(), summary.strip(), keywords.strip(),
        source_reference.strip(), contact_authority.strip(), official_portal_url.strip(),
        verified_by.strip(), verification_status, is_active, item_id
    ))
    db.commit()
    return cursor.rowcount > 0


def delete_knowledge_item(item_id: int, conn=None) -> bool:
    """Delete a knowledge item."""
    db = conn or get_db()
    cursor = db.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))
    db.commit()
    return cursor.rowcount > 0


# ============================================================================
# 4. SAMPLE QUERIES REPOSITORY
# ============================================================================

def add_sample_query(intent_id: int, query_text: str, conn=None) -> int:
    """Add an alternative query phrasing for intent retrieval."""
    db = conn or get_db()
    cursor = db.execute(
        "INSERT INTO sample_queries (intent_id, query_text) VALUES (?, ?)",
        (intent_id, query_text.strip()),
    )
    db.commit()
    return cursor.lastrowid


def get_sample_queries_by_intent(intent_id: int, conn=None) -> List[str]:
    """Get all sample query strings for an intent."""
    db = conn or get_db()
    cursor = db.execute(
        "SELECT query_text FROM sample_queries WHERE intent_id = ?",
        (intent_id,),
    )
    return [row["query_text"] for row in cursor.fetchall()]


def get_all_training_queries(conn=None) -> List[Dict[str, Any]]:
    """Get all sample queries with their intent and topic details."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT sq.id, sq.query_text, sq.intent_id,
               i.name AS intent_name, i.slug AS intent_slug,
               t.id AS topic_id, t.name AS topic_name, t.slug AS topic_slug
        FROM sample_queries sq
        JOIN intents i ON sq.intent_id = i.id
        JOIN topics t ON i.topic_id = t.id
        WHERE i.is_active = 1 AND t.is_active = 1
        ORDER BY sq.id ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# 5. CONVERSATIONS & MESSAGES REPOSITORY
# ============================================================================

def create_conversation(
    conversation_id: str,
    user_id: Optional[int] = None,
    title: str = "New Conversation",
    conn=None
) -> str:
    """Create a new conversational session record."""
    db = conn or get_db()
    db.execute("""
        INSERT OR IGNORE INTO conversations (id, user_id, title)
        VALUES (?, ?, ?)
    """, (conversation_id, user_id, title.strip()))
    db.commit()
    return conversation_id


def get_conversation(conversation_id: str, conn=None) -> Optional[Dict[str, Any]]:
    """Get conversation session details."""
    db = conn or get_db()
    cursor = db.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_user_conversations(user_id: int, limit: int = 20, conn=None) -> List[Dict[str, Any]]:
    """Get all conversations for a user."""
    return get_all_conversations(limit=limit, user_id=user_id, conn=conn)


def get_all_conversations(
    limit: int = 50,
    user_id: Optional[int] = None,
    conn=None
) -> List[Dict[str, Any]]:
    """
    Retrieve recent conversations with message counts and last message preview.
    If user_id is provided, filters by user; otherwise returns all recent sessions.
    """
    db = conn or get_db()
    query = """
        SELECT c.*,
               COUNT(m.id) AS message_count,
               (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_message,
               (SELECT created_at FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC, id DESC LIMIT 1) AS last_message_at
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
    """
    params = []
    if user_id is not None:
        query += " WHERE c.user_id = ?"
        params.append(user_id)
    query += " GROUP BY c.id ORDER BY c.updated_at DESC, c.id DESC LIMIT ?"
    params.append(limit)

    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def update_conversation_title(conversation_id: str, title: str, conn=None) -> bool:
    """Update title of a conversation."""
    db = conn or get_db()
    cursor = db.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title.strip(), conversation_id)
    )
    db.commit()
    return cursor.rowcount > 0


def delete_conversation(conversation_id: str, conn=None) -> bool:
    """Delete a conversation and all its messages."""
    db = conn or get_db()
    db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor = db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    db.commit()
    return cursor.rowcount > 0


def delete_all_conversations(user_id: Optional[int] = None, conn=None) -> int:
    """Delete all conversations and their messages (optionally scoped to a user)."""
    db = conn or get_db()
    if user_id is not None:
        cursor = db.execute("SELECT id FROM conversations WHERE user_id = ?", (user_id,))
        conv_ids = [row["id"] for row in cursor.fetchall()]
        if not conv_ids:
            return 0
        placeholders = ",".join("?" for _ in conv_ids)
        db.execute(f"DELETE FROM messages WHERE conversation_id IN ({placeholders})", conv_ids)
        del_cursor = db.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", conv_ids)
        db.commit()
        return del_cursor.rowcount
    else:
        db.execute("DELETE FROM messages")
        del_cursor = db.execute("DELETE FROM conversations")
        db.commit()
        return del_cursor.rowcount



def create_message(
    conversation_id: str,
    role: str,
    content: str,
    matched_intent_id: Optional[int] = None,
    matched_knowledge_id: Optional[int] = None,
    confidence_score: float = 0.0,
    is_verified: bool = False,
    feedback: Optional[str] = None,
    conn=None
) -> int:
    """Record an individual message inside a conversation."""
    db = conn or get_db()
    # Ensure conversation exists
    create_conversation(conversation_id, conn=db)

    cursor = db.execute("""
        INSERT INTO messages (
            conversation_id, role, content,
            matched_intent_id, matched_knowledge_id,
            confidence_score, is_verified, feedback
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        conversation_id, role, content.strip(),
        matched_intent_id, matched_knowledge_id,
        confidence_score, 1 if is_verified else 0, feedback
    ))

    # Update conversation's updated_at
    db.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    db.commit()
    return cursor.lastrowid


def get_conversation_messages(conversation_id: str, conn=None) -> List[Dict[str, Any]]:
    """Retrieve full chronological message history for a conversation."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT m.*, i.name AS intent_name, k.title AS knowledge_title
        FROM messages m
        LEFT JOIN intents i ON m.matched_intent_id = i.id
        LEFT JOIN knowledge_items k ON m.matched_knowledge_id = k.id
        WHERE m.conversation_id = ?
        ORDER BY m.created_at ASC, m.id ASC
    """, (conversation_id,))
    return [dict(row) for row in cursor.fetchall()]


def update_message_feedback(message_id: int, feedback: str, conn=None) -> bool:
    """Update feedback on a specific message."""
    db = conn or get_db()
    cursor = db.execute(
        "UPDATE messages SET feedback = ? WHERE id = ?",
        (feedback, message_id)
    )
    db.commit()
    return cursor.rowcount > 0


# Helper for backward compatibility with existing chat_logs callers
def log_chat_interaction(
    session_id: str,
    user_query: str,
    matched_intent_id: Optional[int],
    matched_knowledge_id: Optional[int],
    confidence_score: float,
    is_verified_match: bool,
    response_text: str,
    conn=None
) -> int:
    """Records query as user message and response as assistant message."""
    db = conn or get_db()
    create_conversation(session_id, conn=db)
    create_message(session_id, "user", user_query, conn=db)
    msg_id = create_message(
        session_id, "assistant", response_text,
        matched_intent_id=matched_intent_id,
        matched_knowledge_id=matched_knowledge_id,
        confidence_score=confidence_score,
        is_verified=is_verified_match,
        conn=db
    )
    return msg_id


def update_chat_feedback(chat_log_id: int, feedback: str, conn=None) -> bool:
    """Alias for message feedback."""
    return update_message_feedback(chat_log_id, feedback, conn=conn)


# ============================================================================
# 6. UNRESOLVED QUERIES REPOSITORY
# ============================================================================

VALID_UNRESOLVED_STATUSES = {"unresolved", "under_review", "verified", "rejected", "closed"}

STATUS_ALIASES = {
    "pending": "unresolved",
    "reviewed": "under_review",
    "resolved": "verified",
    "ignored": "rejected",
}

REVERSE_STATUS_ALIASES = {
    "unresolved": "pending",
    "under_review": "reviewed",
    "verified": "resolved",
    "rejected": "ignored",
    "closed": "closed",
}


def normalize_status(status: Optional[str]) -> str:
    """Normalize status string to canonical unresolved workflow status."""
    if not status:
        return "unresolved"
    s = status.strip().lower()
    return STATUS_ALIASES.get(s, s)


def log_unresolved_query(
    original_question: Optional[str] = None,
    predicted_topic: Optional[str] = None,
    predicted_intent: Optional[str] = None,
    confidence: float = 0.0,
    retrieval_info: Optional[str] = None,
    conversation_id: Optional[str] = None,
    classification_confidence: Optional[float] = None,
    retrieval_confidence: Optional[float] = None,
    status: str = "unresolved",
    conn=None,
    query_text: Optional[str] = None,
    detected_topic: Optional[str] = None,
    max_confidence: Optional[float] = None,
    review_status: Optional[str] = None,
) -> int:
    """
    Log an unanswered/unverified question to the review queue with full triage metadata:
    - question
    - predicted topic
    - predicted intent
    - classification confidence
    - retrieval confidence
    - timestamp (created_at)
    - conversation reference (conversation_id)
    - status ('unresolved', 'under_review', 'verified', 'rejected', 'closed')
    """
    db = conn or get_db()
    if conversation_id:
        create_conversation(conversation_id, conn=db)

    question = (original_question or query_text or "").strip()
    topic = predicted_topic or detected_topic
    class_conf = classification_confidence if classification_confidence is not None else (
        confidence if max_confidence is None else max_confidence
    )
    ret_conf = retrieval_confidence if retrieval_confidence is not None else 0.0
    overall_conf = max(class_conf, ret_conf) if max_confidence is None else max_confidence

    raw_status = status or review_status or "unresolved"
    norm_status = normalize_status(raw_status)
    if norm_status not in VALID_UNRESOLVED_STATUSES:
        raise ValueError(
            f"Invalid status '{raw_status}'. Allowed statuses are: {sorted(VALID_UNRESOLVED_STATUSES)}"
        )

    legacy_status = REVERSE_STATUS_ALIASES.get(norm_status, "pending")

    cursor = db.execute("""
        INSERT INTO unresolved_queries (
            original_question, conversation_id, predicted_topic, predicted_intent,
            classification_confidence, retrieval_confidence, confidence,
            retrieval_info, status, review_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        question, conversation_id, topic, predicted_intent,
        class_conf, ret_conf, overall_conf,
        retrieval_info, norm_status, legacy_status
    ))
    db.commit()
    return cursor.lastrowid


def get_unresolved_queries(
    review_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    conn=None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retrieve unresolved queries with optional status filter."""
    db = conn or get_db()
    filter_val = status or review_status
    query = """
        SELECT u.*, i.name AS resolution_intent_name,
               u.original_question AS query_text,
               u.original_question AS question,
               u.confidence AS max_confidence,
               u.status AS status,
               u.review_status AS review_status,
               u.conversation_id AS conversation_reference
        FROM unresolved_queries u
        LEFT JOIN intents i ON u.resolution_intent_id = i.id
    """
    params = []
    if filter_val:
        norm = normalize_status(filter_val)
        legacy = REVERSE_STATUS_ALIASES.get(norm, filter_val)
        query += " WHERE u.status = ? OR u.review_status = ? OR u.status = ? OR u.review_status = ?"
        params.extend([norm, norm, legacy, legacy])
    query += " ORDER BY u.created_at DESC, u.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def get_unresolved_query_by_id(query_id: int, conn=None) -> Optional[Dict[str, Any]]:
    """Get an unresolved query by ID."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT u.*,
               u.original_question AS query_text,
               u.original_question AS question,
               u.confidence AS max_confidence,
               u.status AS status,
               u.review_status AS review_status,
               u.conversation_id AS conversation_reference
        FROM unresolved_queries u WHERE id = ?
    """, (query_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def update_unresolved_query_status(
    query_id: int,
    new_status: str,
    admin_notes: Optional[str] = None,
    reviewed_by: Optional[str] = None,
    resolution_intent_id: Optional[int] = None,
    conn=None,
) -> bool:
    """
    Update status of an unresolved query with validation against allowed status transitions.
    Allowed statuses: 'unresolved', 'under_review', 'verified', 'rejected', 'closed'
    """
    db = conn or get_db()
    norm_status = normalize_status(new_status)
    if norm_status not in VALID_UNRESOLVED_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Allowed statuses are: {sorted(VALID_UNRESOLVED_STATUSES)}"
        )

    legacy_status = REVERSE_STATUS_ALIASES.get(norm_status, norm_status)
    reviewer = reviewed_by or "admin"

    cursor = db.execute("""
        UPDATE unresolved_queries
        SET status = ?,
            review_status = ?,
            admin_notes = COALESCE(?, admin_notes),
            reviewed_by = COALESCE(?, reviewed_by),
            resolution_intent_id = COALESCE(?, resolution_intent_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (norm_status, legacy_status, admin_notes, reviewer, resolution_intent_id, query_id))

    if cursor.rowcount > 0:
        log_audit(
            actor_username=reviewer,
            action=f"UPDATE_STATUS_{norm_status.upper()}",
            target_entity="unresolved_query",
            target_id=query_id,
            changes_summary=f"Changed status to '{norm_status}'. Notes: {admin_notes or 'None'}",
            conn=db,
        )
    db.commit()
    return cursor.rowcount > 0


def resolve_unresolved_query(
    query_id: int,
    resolution_intent_id: Optional[int],
    admin_notes: str,
    reviewed_by: Optional[str] = None,
    review_status: str = "resolved",
    conn=None,
    resolved_by: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    """Mark an unresolved query as resolved, reviewed, or ignored (or verified, rejected, closed)."""
    db = conn or get_db()
    reviewer = reviewed_by or resolved_by or "admin"
    raw_status = status or review_status or "resolved"
    norm_status = normalize_status(raw_status)
    legacy_status = REVERSE_STATUS_ALIASES.get(norm_status, norm_status)

    cursor = db.execute("""
        UPDATE unresolved_queries
        SET resolution_intent_id = ?,
            admin_notes = ?,
            reviewed_by = ?,
            status = ?,
            review_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (resolution_intent_id, admin_notes, reviewer, norm_status, legacy_status, query_id))
    db.commit()
    return cursor.rowcount > 0


def count_unresolved_queries(
    review_status: str = "unresolved",
    conn=None,
    status: Optional[str] = None,
) -> int:
    """Count unresolved queries matching a given status or review_status."""
    db = conn or get_db()
    effective_status = status or review_status
    norm = normalize_status(effective_status)
    legacy = REVERSE_STATUS_ALIASES.get(norm, effective_status)

    cursor = db.execute(
        "SELECT COUNT(*) AS count FROM unresolved_queries WHERE status = ? OR review_status = ? OR status = ? OR review_status = ?",
        (norm, norm, legacy, legacy)
    )
    row = cursor.fetchone()
    return row["count"] if row else 0


# ============================================================================
# 7. AUDIT LOGS REPOSITORY
# ============================================================================

def log_audit(
    actor_username: Optional[str] = None,
    action: str = "",
    target_entity: Optional[str] = None,
    target_id: Optional[int] = None,
    changes_summary: Optional[str] = None,
    actor_role: str = "admin",
    conn=None,
    admin_username: Optional[str] = None,
    target_type: Optional[str] = None,
    details: Optional[str] = None,
) -> int:
    """Record an administrative or system audit entry."""
    db = conn or get_db()
    username = actor_username or admin_username or "admin"
    entity = target_entity or target_type or "system"
    summary = changes_summary or details or ""

    cursor = db.execute("""
        INSERT INTO audit_logs (
            actor_username, actor_role, action,
            target_entity, target_id, changes_summary
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (username, actor_role, action, entity, target_id, summary))
    db.commit()
    return cursor.lastrowid


def get_recent_audit_logs(
    limit: int = 25,
    action_filter: Optional[str] = None,
    target_entity: Optional[str] = None,
    conn=None
) -> List[Dict[str, Any]]:
    """Fetch recent audit log items with optional filtering."""
    db = conn or get_db()
    query = """
        SELECT id, actor_username, actor_username AS admin_username,
               actor_role, action, target_entity, target_entity AS target_type,
               target_id, changes_summary, changes_summary AS details, created_at
        FROM audit_logs
        WHERE 1=1
    """
    params = []
    if action_filter:
        query += " AND action = ?"
        params.append(action_filter)
    if target_entity:
        query += " AND target_entity = ?"
        params.append(target_entity)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# 8. ANALYTICS & STATS REPOSITORY
# ============================================================================

def get_recent_knowledge_updates(limit: int = 5, conn=None) -> List[Dict[str, Any]]:
    """Retrieve the most recently updated or created knowledge entries."""
    db = conn or get_db()
    cursor = db.execute("""
        SELECT k.id, k.title, k.verification_status, k.is_active, k.version, k.updated_at,
               i.name AS intent_name, t.name AS topic_name
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
        ORDER BY k.updated_at DESC, k.id DESC
        LIMIT ?
    """, (limit,))
    return [dict(row) for row in cursor.fetchall()]


def get_chat_stats(conn=None) -> Dict[str, Any]:
    """Compute aggregate analytical statistics for the admin dashboard."""
    db = conn or get_db()

    # 1. Consolidated message queries (1 query instead of 2)
    msg_row = db.execute("""
        SELECT 
            COUNT(CASE WHEN role = 'user' THEN 1 END) AS total_queries,
            COUNT(CASE WHEN role = 'assistant' AND is_verified = 1 THEN 1 END) AS verified_queries
        FROM messages
    """).fetchone()
    total_queries = msg_row["total_queries"] if msg_row else 0
    verified_queries = msg_row["verified_queries"] if msg_row else 0

    # 2. Consolidated unresolved query counts (1 query instead of 2)
    unres_row = db.execute("""
        SELECT 
            COUNT(CASE WHEN review_status IN ('pending', 'unresolved') THEN 1 END) AS pending_unresolved,
            COUNT(CASE WHEN review_status IN ('under_review', 'reviewed') THEN 1 END) AS queries_under_review
        FROM unresolved_queries
    """).fetchone()
    pending_unresolved = unres_row["pending_unresolved"] if unres_row else 0
    queries_under_review = unres_row["queries_under_review"] if unres_row else 0

    # 3. Consolidated knowledge entry counts (1 query instead of 2)
    know_row = db.execute("""
        SELECT 
            COUNT(*) AS total_knowledge_entries,
            COUNT(CASE WHEN verification_status = 'verified' AND is_active = 1 THEN 1 END) AS verified_entries
        FROM knowledge_items
    """).fetchone()
    total_knowledge_entries = know_row["total_knowledge_entries"] if know_row else 0
    verified_entries = know_row["verified_entries"] if know_row else 0

    resolution_rate = round((verified_queries / total_queries * 100), 1) if total_queries > 0 else 100.0

    return {
        "total_queries": total_queries,
        "verified_queries": verified_queries,
        "pending_unresolved": pending_unresolved,
        "unresolved_queries": pending_unresolved,
        "queries_under_review": queries_under_review,
        "total_knowledge": verified_entries,
        "total_knowledge_entries": total_knowledge_entries,
        "verified_entries": verified_entries,
        "resolution_rate": resolution_rate,
    }

