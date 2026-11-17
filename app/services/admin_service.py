"""
CampusAssist: Administrator Service.
Business logic for dashboard analytics, knowledge curation, and unresolved query triage.
"""

from typing import Dict, Any, List, Optional
from app.models.db import get_db
from app.models.repositories import (
    get_chat_stats,
    get_all_topics,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_knowledge_by_id,
    create_knowledge_item,
    update_knowledge_item,
    delete_knowledge_item,
    get_intent_by_id,
    get_unresolved_queries,
    get_unresolved_query_by_id,
    resolve_unresolved_query,
    count_unresolved_queries,
    add_sample_query,
    log_audit,
    get_recent_audit_logs,
    get_recent_knowledge_updates,
    create_topic as repo_create_topic,
    update_topic as repo_update_topic,
    create_intent as repo_create_intent,
    update_intent as repo_update_intent,
)
from app.services.retrieval.semantic_search import sync_knowledge_retrieval_index


def get_dashboard_summary(conn=None) -> Dict[str, Any]:
    """Retrieve key metrics for the admin dashboard."""
    db = conn or get_db()
    stats = get_chat_stats(conn=db)
    topics = get_all_topics(conn=db)
    intents = get_all_intents_with_topic(conn=db)
    recent_audits = get_recent_audit_logs(limit=10, conn=db)
    recent_updates = get_recent_knowledge_updates(limit=5, conn=db)

    return {
        "stats": stats,
        "total_topics": len(topics),
        "total_intents": len(intents),
        "total_knowledge_entries": stats.get("total_knowledge_entries", 0),
        "verified_entries": stats.get("verified_entries", 0),
        "unresolved_queries": stats.get("unresolved_queries", 0),
        "queries_under_review": stats.get("queries_under_review", 0),
        "recent_audits": recent_audits,
        "recent_updates": recent_updates,
    }


def resolve_query_with_new_knowledge(
    unresolved_query_id: int,
    intent_id: int,
    title: str,
    summary: str,
    detailed_procedure: str,
    required_documents: str = "",
    contact_authority: str = "",
    official_portal_url: str = "",
    admin_username: str = "admin",
    admin_notes: str = "",
    keywords: str = "",
    source_reference: str = "NIT Durgapur Verified Admin Record",
    conn=None
) -> int:
    """
    Create a new verified knowledge item and resolve the pending query.
    Also adds the unresolved query text as a sample query for future retrieval.
    """
    db = conn or get_db()
    unresolved = get_unresolved_query_by_id(unresolved_query_id, conn=db)
    if not unresolved:
        raise ValueError("Unresolved query not found")

    intent = get_intent_by_id(intent_id, conn=db)
    if not intent:
        raise ValueError("Intent not found")

    topic_id = intent["topic_id"]

    # 1. Create knowledge item
    content_full = detailed_procedure
    if required_documents:
        content_full += f"\nRequired Documents: {required_documents}"

    k_id = create_knowledge_item(
        topic_id=topic_id,
        intent_id=intent_id,
        title=title,
        content=content_full,
        summary=summary,
        keywords=keywords or unresolved["query_text"],
        source_reference=source_reference,
        contact_authority=contact_authority,
        official_portal_url=official_portal_url,
        verified_by=f"NIT Durgapur Verified (by {admin_username})",
        verification_status="verified",
        version=1,
        is_active=1,
        conn=db,
    )

    # 2. Add original query as a sample query for future retrieval
    add_sample_query(intent_id=intent_id, query_text=unresolved["query_text"], conn=db)

    # 3. Mark query as resolved
    notes = admin_notes or f"Resolved with new verified knowledge ID #{k_id}"
    resolve_unresolved_query(
        query_id=unresolved_query_id,
        resolution_intent_id=intent_id,
        admin_notes=notes,
        reviewed_by=admin_username,
        review_status="resolved",
        conn=db,
    )

    # 4. Audit log
    log_audit(
        actor_username=admin_username,
        action="RESOLVE_WITH_KNOWLEDGE",
        target_entity="unresolved_query",
        target_id=unresolved_query_id,
        changes_summary=f"Created knowledge item #{k_id} and mapped query '{unresolved['query_text']}' to intent #{intent_id}",
        conn=db,
    )

    # 5. Automatically re-index semantic retrieval & update classifier in memory
    try:
        sync_knowledge_retrieval_index(conn=db)
    except Exception:
        pass

    return k_id


def resolve_query_by_mapping_intent(
    unresolved_query_id: int,
    intent_id: int,
    admin_username: str,
    admin_notes: str = "",
    conn=None
) -> bool:
    """
    Map an unresolved query to an existing verified intent as an alternative phrasing.
    """
    db = conn or get_db()
    unresolved = get_unresolved_query_by_id(unresolved_query_id, conn=db)
    if not unresolved:
        raise ValueError("Unresolved query not found")

    # Add query text to existing intent sample queries
    add_sample_query(intent_id=intent_id, query_text=unresolved["query_text"], conn=db)

    # Mark as resolved
    notes = admin_notes or f"Mapped to existing intent #{intent_id} as alternative phrasing"
    resolve_unresolved_query(
        query_id=unresolved_query_id,
        resolution_intent_id=intent_id,
        admin_notes=notes,
        reviewed_by=admin_username,
        review_status="resolved",
        conn=db,
    )

    # Audit log
    log_audit(
        actor_username=admin_username,
        action="MAP_TO_INTENT",
        target_entity="unresolved_query",
        target_id=unresolved_query_id,
        changes_summary=f"Mapped query '{unresolved['query_text']}' to existing intent #{intent_id}",
        conn=db,
    )

    # Automatically re-index semantic retrieval & update classifier in memory
    try:
        sync_knowledge_retrieval_index(conn=db)
    except Exception:
        pass

    return True


# ============================================================================
# TOPICS & INTENTS ADMINISTRATION
# ============================================================================

def admin_create_topic(
    name: str,
    slug: str,
    description: str = "",
    icon: str = "folder",
    admin_username: str = "admin",
    conn=None
) -> int:
    """Create a new domain topic and update index."""
    db = conn or get_db()
    topic_id = repo_create_topic(
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        is_active=1,
        conn=db,
    )
    log_audit(
        actor_username=admin_username,
        action="CREATE_TOPIC",
        target_entity="topic",
        target_id=topic_id,
        changes_summary=f"Created topic '{name}' ({slug})",
    )
    try:
        sync_knowledge_retrieval_index(conn=db)
    except Exception:
        pass
    return topic_id


def admin_update_topic(
    topic_id: int,
    name: str,
    slug: str,
    description: str = "",
    icon: str = "folder",
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Update topic fields and trigger index refresh."""
    db = conn or get_db()
    success = repo_update_topic(
        topic_id=topic_id,
        name=name,
        slug=slug,
        description=description,
        icon=icon,
        is_active=is_active,
        conn=db,
    )
    if success:
        log_audit(
            actor_username=admin_username,
            action="UPDATE_TOPIC",
            target_entity="topic",
            target_id=topic_id,
            changes_summary=f"Updated topic #{topic_id} '{name}'",
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
    return success


def admin_create_intent(
    topic_id: int,
    name: str,
    slug: str,
    description: str = "",
    admin_username: str = "admin",
    sample_queries: Optional[List[str]] = None,
    conn=None
) -> int:
    """Create a new intent, link to topic, add sample queries, and update index."""
    db = conn or get_db()
    intent_id = repo_create_intent(
        topic_id=topic_id,
        name=name,
        slug=slug,
        description=description,
        is_active=1,
        conn=db,
    )
    if sample_queries:
        for q in sample_queries:
            add_sample_query(intent_id=intent_id, query_text=q, conn=db)

    log_audit(
        actor_username=admin_username,
        action="CREATE_INTENT",
        target_entity="intent",
        target_id=intent_id,
        changes_summary=f"Created intent '{name}' ({slug}) under topic #{topic_id}",
    )
    try:
        sync_knowledge_retrieval_index(conn=db)
    except Exception:
        pass
    return intent_id


def admin_update_intent(
    intent_id: int,
    name: str,
    slug: str,
    description: str = "",
    topic_id: Optional[int] = None,
    is_active: int = 1,
    admin_username: str = "admin",
    conn=None
) -> bool:
    """Update intent fields and trigger index refresh."""
    db = conn or get_db()
    success = repo_update_intent(
        intent_id=intent_id,
        name=name,
        slug=slug,
        description=description,
        topic_id=topic_id,
        is_active=is_active,
        conn=db,
    )
    if success:
        log_audit(
            actor_username=admin_username,
            action="UPDATE_INTENT",
            target_entity="intent",
            target_id=intent_id,
            changes_summary=f"Updated intent #{intent_id} '{name}'",
        )
        try:
            sync_knowledge_retrieval_index(conn=db)
        except Exception:
            pass
    return success
