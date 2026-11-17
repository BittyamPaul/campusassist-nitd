"""
CampusAssist: NIT Durgapur Knowledge Repository Service.
Authoritative domain information layer enforcing:
Topic -> Intent -> Verified Knowledge.

Guarantees:
- Only verified and active entries are eligible for official NIT-specific responses.
- Versioning is strictly tracked and incremented upon modification.
- Administrative audit logs are recorded for all create, update, deactivate, and verify operations.
- Clearly labelled demo records only.
"""

from typing import Optional, List, Dict, Any
from app.models.db import get_db
from app.models.repositories import (
    get_topic_by_id,
    get_topic_by_slug,
    get_all_topics,
    create_topic as repo_create_topic,
    get_intent_by_id,
    get_intent_by_slug,
    get_intents_by_topic,
    create_intent as repo_create_intent,
    create_knowledge_item as repo_create_knowledge,
    get_knowledge_by_id,
    get_knowledge_by_intent,
    update_knowledge_item as repo_update_knowledge,
    delete_knowledge_item,
    log_audit,
)
from app.services.retrieval.semantic_search import sync_knowledge_retrieval_index


def is_eligible_for_official_response(knowledge_item: Optional[Dict[str, Any]]) -> bool:
    """
    Validation gate: Only verified and active information can be used
    for official NIT-specific responses.
    """
    if not knowledge_item:
        return False
    is_active = bool(knowledge_item.get("is_active", 0))
    status = knowledge_item.get("verification_status", "").lower()
    return is_active and status == "verified"


# ============================================================================
# 1. TOPIC MANAGEMENT
# ============================================================================

def create_topic(
    name: str,
    slug: str,
    description: str = "",
    icon: str = "folder",
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> int:
    """Create a new domain category/topic."""
    db = conn or get_db()
    topic_id = repo_create_topic(
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        is_active=is_active,
        conn=db,
    )
    log_audit(
        actor_username=admin_username,
        action="CREATE_TOPIC",
        target_entity="topic",
        target_id=topic_id,
        changes_summary=f"Created topic '{name}' (slug: {slug})",
        conn=db,
    )
    return topic_id


def get_topic(topic_identifier: Any, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve topic by numeric ID or slug."""
    db = conn or get_db()
    if isinstance(topic_identifier, int) or (isinstance(topic_identifier, str) and topic_identifier.isdigit()):
        return get_topic_by_id(int(topic_identifier), conn=db)
    return get_topic_by_slug(str(topic_identifier), conn=db)


def list_topics(include_inactive: bool = False, conn=None) -> List[Dict[str, Any]]:
    """List topics, optionally including deactivated ones."""
    db = conn or get_db()
    if include_inactive:
        cursor = db.execute("SELECT * FROM topics ORDER BY name ASC")
        return [dict(row) for row in cursor.fetchall()]
    return get_all_topics(is_active=1, conn=db)


def update_topic(
    topic_id: int,
    name: str,
    slug: str,
    description: str,
    icon: str = "folder",
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Update topic properties."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE topics
        SET name = ?, slug = ?, description = ?, icon = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (name.strip(), slug.strip(), description.strip(), icon.strip(), is_active, topic_id))
    db.commit()

    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="UPDATE_TOPIC",
            target_entity="topic",
            target_id=topic_id,
            changes_summary=f"Updated topic #{topic_id} '{name}'",
            conn=db,
        )
        return True
    return False


def deactivate_topic(topic_id: int, admin_username: str = "admin", conn=None) -> bool:
    """Deactivate a topic (soft delete)."""
    db = conn or get_db()
    cursor = db.execute(
        "UPDATE topics SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (topic_id,)
    )
    db.commit()
    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="DEACTIVATE_TOPIC",
            target_entity="topic",
            target_id=topic_id,
            changes_summary=f"Deactivated topic #{topic_id}",
            conn=db,
        )
        return True
    return False


# ============================================================================
# 2. INTENT MANAGEMENT
# ============================================================================

def create_intent(
    topic_id: int,
    name: str,
    slug: str,
    description: str = "",
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> int:
    """Create a new intent linked to a parent topic."""
    db = conn or get_db()
    topic = get_topic_by_id(topic_id, conn=db)
    if not topic:
        raise ValueError(f"Parent topic ID #{topic_id} not found.")

    intent_id = repo_create_intent(
        topic_id=topic_id,
        name=name,
        slug=slug,
        description=description,
        is_active=is_active,
        conn=db,
    )
    log_audit(
        actor_username=admin_username,
        action="CREATE_INTENT",
        target_entity="intent",
        target_id=intent_id,
        changes_summary=f"Created intent '{name}' under topic '{topic['name']}'",
        conn=db,
    )
    return intent_id


def get_intent(intent_identifier: Any, conn=None) -> Optional[Dict[str, Any]]:
    """Retrieve intent by numeric ID or slug."""
    db = conn or get_db()
    if isinstance(intent_identifier, int) or (isinstance(intent_identifier, str) and intent_identifier.isdigit()):
        return get_intent_by_id(int(intent_identifier), conn=db)
    return get_intent_by_slug(str(intent_identifier), conn=db)


def list_intents(
    topic_id: Optional[int] = None,
    include_inactive: bool = False,
    conn=None
) -> List[Dict[str, Any]]:
    """List intents, with optional topic filter and inactive toggle."""
    db = conn or get_db()
    query = """
        SELECT i.*, t.name AS topic_name, t.slug AS topic_slug
        FROM intents i
        JOIN topics t ON i.topic_id = t.id
    """
    clauses = []
    params = []

    if topic_id:
        clauses.append("i.topic_id = ?")
        params.append(topic_id)
    if not include_inactive:
        clauses.append("i.is_active = 1 AND t.is_active = 1")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY t.name ASC, i.name ASC"

    cursor = db.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]


def update_intent(
    intent_id: int,
    name: str,
    slug: str,
    description: str,
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Update intent properties."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE intents
        SET name = ?, slug = ?, description = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (name.strip(), slug.strip(), description.strip(), is_active, intent_id))
    db.commit()

    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="UPDATE_INTENT",
            target_entity="intent",
            target_id=intent_id,
            changes_summary=f"Updated intent #{intent_id} '{name}'",
            conn=db,
        )
        return True
    return False


def deactivate_intent(intent_id: int, admin_username: str = "admin", conn=None) -> bool:
    """Deactivate an intent (soft delete)."""
    db = conn or get_db()
    cursor = db.execute(
        "UPDATE intents SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (intent_id,)
    )
    db.commit()
    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="DEACTIVATE_INTENT",
            target_entity="intent",
            target_id=intent_id,
            changes_summary=f"Deactivated intent #{intent_id}",
            conn=db,
        )
        return True
    return False


# ============================================================================
# 3. KNOWLEDGE ENTRIES MANAGEMENT (Authoritative Repository)
# ============================================================================

def create_knowledge(
    intent_id: int,
    title: str,
    content: str,
    summary: str,
    keywords: str = "",
    source_reference: str = "NIT Durgapur Demo Verified Record",
    contact_authority: str = "",
    official_portal_url: str = "",
    verified_by: str = "NIT Durgapur Demo Verified",
    verification_status: str = "verified",
    is_active: int = 1,
    admin_username: str = "admin",
    topic_id: Optional[int] = None,
    conn=None
) -> int:
    """
    Create a new verified knowledge entry.
    Strictly verifies parent intent and topic existence.
    """
    db = conn or get_db()
    intent = get_intent_by_id(intent_id, conn=db)
    if not intent:
        raise ValueError(f"Intent ID #{intent_id} not found.")

    target_topic_id = topic_id or intent["topic_id"]

    item_id = repo_create_knowledge(
        topic_id=target_topic_id,
        intent_id=intent_id,
        title=title.strip(),
        content=content.strip(),
        summary=summary.strip(),
        keywords=keywords.strip(),
        source_reference=source_reference.strip(),
        contact_authority=contact_authority.strip(),
        official_portal_url=official_portal_url.strip(),
        verified_by=verified_by.strip(),
        verification_status=verification_status,
        version=1,
        is_active=is_active,
        conn=db,
    )

    log_audit(
        actor_username=admin_username,
        action="CREATE_KNOWLEDGE",
        target_entity="knowledge_item",
        target_id=item_id,
        changes_summary=f"Created knowledge '{title}' (v1) under intent '{intent['name']}'",
        conn=db,
    )
    try:
        sync_knowledge_retrieval_index(conn=db)
    except Exception:
        pass
    return item_id


def update_knowledge(
    item_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    keywords: Optional[str] = None,
    source_reference: Optional[str] = None,
    contact_authority: Optional[str] = None,
    official_portal_url: Optional[str] = None,
    verified_by: Optional[str] = None,
    verification_status: Optional[str] = None,
    is_active: Optional[int] = None,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """
    Update an existing knowledge entry.
    Automatically increments version number, updates timestamp, and logs changes.
    """
    db = conn or get_db()
    existing = get_knowledge_by_id(item_id, conn=db)
    if not existing:
        raise ValueError(f"Knowledge entry #{item_id} not found.")

    new_title = title if title is not None else existing["title"]
    new_content = content if content is not None else existing["content"]
    new_summary = summary if summary is not None else existing["summary"]
    new_keywords = keywords if keywords is not None else existing["keywords"]
    new_source = source_reference if source_reference is not None else existing["source_reference"]
    new_authority = contact_authority if contact_authority is not None else existing["contact_authority"]
    new_portal = official_portal_url if official_portal_url is not None else existing["official_portal_url"]
    new_verified_by = verified_by if verified_by is not None else existing["verified_by"]
    new_status = verification_status if verification_status is not None else existing["verification_status"]
    new_active = is_active if is_active is not None else existing["is_active"]

    success = repo_update_knowledge(
        item_id=item_id,
        title=new_title,
        content=new_content,
        summary=new_summary,
        keywords=new_keywords,
        source_reference=new_source,
        contact_authority=new_authority,
        official_portal_url=new_portal,
        verified_by=new_verified_by,
        verification_status=new_status,
        is_active=new_active,
        conn=db,
    )

    if success:
        log_audit(
            actor_username=admin_username,
            action="UPDATE_KNOWLEDGE",
            target_entity="knowledge_item",
            target_id=item_id,
            changes_summary=f"Updated knowledge #{item_id} '{new_title}' (version {existing['version'] + 1})",
            conn=db,
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
        return True
    return False


def retrieve_knowledge(
    item_id: int,
    only_eligible: bool = False,
    conn=None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve knowledge entry by ID.
    If only_eligible=True, strictly checks that item is verified AND active.
    """
    db = conn or get_db()
    item = get_knowledge_by_id(item_id, conn=db)
    if not item:
        return None

    if only_eligible and not is_eligible_for_official_response(item):
        return None

    return item


def retrieve_verified_knowledge_for_intent(
    intent_id: int,
    conn=None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the authoritative active verified knowledge entry for an intent.
    Strictly filters verification_status == 'verified' AND is_active == 1.
    """
    db = conn or get_db()
    item = get_knowledge_by_intent(intent_id, conn=db)
    if item and is_eligible_for_official_response(item):
        return item
    return None


def deactivate_knowledge(
    item_id: int,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Deactivate a knowledge item so it is excluded from assistant responses."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE knowledge_items
        SET is_active = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (item_id,))
    db.commit()

    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="DEACTIVATE_KNOWLEDGE",
            target_entity="knowledge_item",
            target_id=item_id,
            changes_summary=f"Deactivated knowledge item #{item_id}",
            conn=db,
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
        return True
    return False


def activate_knowledge(
    item_id: int,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Activate a deactivated knowledge item."""
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE knowledge_items
        SET is_active = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (item_id,))
    db.commit()

    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="ACTIVATE_KNOWLEDGE",
            target_entity="knowledge_item",
            target_id=item_id,
            changes_summary=f"Activated knowledge item #{item_id}",
            conn=db,
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
        return True
    return False


def verify_knowledge(
    item_id: int,
    verified_by: str = "NIT Durgapur Authorized Reviewer",
    admin_username: str = "admin",
    conn=None
) -> bool:
    """
    Certify a knowledge item as official and verified.
    Updates verification_status, last_verified_at, and verified_by.
    """
    db = conn or get_db()
    cursor = db.execute("""
        UPDATE knowledge_items
        SET verification_status = 'verified',
            verified_by = ?,
            last_verified_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (verified_by.strip(), item_id))
    db.commit()

    if cursor.rowcount > 0:
        log_audit(
            actor_username=admin_username,
            action="VERIFY_KNOWLEDGE",
            target_entity="knowledge_item",
            target_id=item_id,
            changes_summary=f"Marked knowledge #{item_id} as verified by '{verified_by}'",
            conn=db,
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
        return True
    return False


def search_knowledge(
    query_string: str,
    topic_id: Optional[int] = None,
    only_eligible: bool = True,
    limit: int = 10,
    conn=None
) -> List[Dict[str, Any]]:
    """
    Search knowledge repository by matching against title, summary, content, and keywords.
    If only_eligible=True, guarantees only active, verified items are returned.
    """
    db = conn or get_db()
    search_term = f"%{query_string.strip().lower()}%"

    sql = """
        SELECT k.*, i.name AS intent_name, i.slug AS intent_slug,
               t.name AS topic_name, t.slug AS topic_slug
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
        WHERE (
            LOWER(k.title) LIKE ?
            OR LOWER(k.summary) LIKE ?
            OR LOWER(k.content) LIKE ?
            OR LOWER(k.keywords) LIKE ?
            OR LOWER(k.source_reference) LIKE ?
        )
    """
    params = [search_term, search_term, search_term, search_term, search_term]

    if only_eligible:
        sql += " AND k.is_active = 1 AND k.verification_status = 'verified' AND i.is_active = 1 AND t.is_active = 1"

    if topic_id:
        sql += " AND k.topic_id = ?"
        params.append(topic_id)

    sql += " ORDER BY k.version DESC, k.id DESC LIMIT ?"
    params.append(limit)

    cursor = db.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def list_knowledge_entries(
    topic_id: Optional[int] = None,
    intent_id: Optional[int] = None,
    status: Optional[str] = None,
    only_eligible: bool = False,
    conn=None
) -> List[Dict[str, Any]]:
    """Retrieve filtered knowledge entries."""
    db = conn or get_db()
    sql = """
        SELECT k.*, i.name AS intent_name, i.slug AS intent_slug,
               t.name AS topic_name, t.slug AS topic_slug
        FROM knowledge_items k
        JOIN intents i ON k.intent_id = i.id
        JOIN topics t ON k.topic_id = t.id
    """
    clauses = []
    params = []

    if only_eligible:
        clauses.append("k.is_active = 1 AND k.verification_status = 'verified' AND i.is_active = 1 AND t.is_active = 1")
    else:
        if status:
            clauses.append("k.verification_status = ?")
            params.append(status)

    if topic_id:
        clauses.append("k.topic_id = ?")
        params.append(topic_id)

    if intent_id:
        clauses.append("k.intent_id = ?")
        params.append(intent_id)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY t.name ASC, i.name ASC, k.title ASC"
    cursor = db.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]
