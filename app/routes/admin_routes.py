"""
CampusAssist: Administrative REST API Routes.
Secure endpoints for dashboard analytics, knowledge CRUD, and unresolved query triage.
"""

from flask import Blueprint, request, jsonify, session
from app.services.auth_service import (
    authenticate_admin,
    login_admin_session,
    logout_admin_session,
    is_admin_authenticated,
    admin_api_required,
    admin_api_role_required,
)
from app.services.admin_service import (
    get_dashboard_summary,
    resolve_query_with_new_knowledge,
    resolve_query_by_mapping_intent,
    admin_create_topic,
    admin_update_topic,
    admin_create_intent,
    admin_update_intent,
)
from app.models.repositories import (
    get_all_topics,
    get_topic_by_id,
    get_all_intents_with_topic,
    get_all_knowledge_items,
    get_knowledge_by_id,
    create_knowledge_item,
    update_knowledge_item,
    delete_knowledge_item,
    get_intent_by_id,
    get_unresolved_queries,
    get_unresolved_query_by_id,
    update_unresolved_query_status,
    resolve_unresolved_query,
    get_recent_audit_logs,
    log_audit,
)
from app.services.retrieval.semantic_search import sync_knowledge_retrieval_index
from app.services.rate_limiter import rate_limit
from app.services.security_utils import is_safe_portal_url, validate_slug

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_bp.route("/login", methods=["POST"])
@rate_limit(limit=15, window_seconds=60, key_prefix="admin_api_login")
def api_admin_login():
    """Authenticate administrator credentials via JSON API."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    admin = authenticate_admin(username, password)
    if not admin:
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid administrator credentials."
        }), 401

    login_admin_session(admin)
    return jsonify({
        "status": "success",
        "message": "Authentication successful.",
        "admin": {
            "id": admin["id"],
            "username": admin["username"],
            "display_name": admin["display_name"],
            "role": admin["role"],
        }
    }), 200


@admin_bp.route("/logout", methods=["POST"])
def api_admin_logout():
    """Terminate administrator session via API."""
    logout_admin_session()
    return jsonify({
        "status": "success",
        "message": "Successfully logged out."
    }), 200


@admin_bp.route("/me", methods=["GET"])
@admin_api_required
def api_admin_me():
    """Return profile details for current authenticated administrator."""
    return jsonify({
        "status": "success",
        "admin": {
            "id": session.get("admin_id"),
            "username": session.get("admin_username"),
            "display_name": session.get("admin_display_name"),
            "role": session.get("admin_role"),
        }
    }), 200


@admin_bp.route("/stats", methods=["GET"])
@admin_bp.route("/metrics", methods=["GET"])
@admin_bp.route("/dashboard", methods=["GET"])
@admin_api_required
def get_stats():
    """Retrieve administrative metrics."""
    summary = get_dashboard_summary()
    return jsonify({"status": "success", "data": summary})


@admin_bp.route("/taxonomy", methods=["GET"])
@admin_api_required
def get_taxonomy_route():
    """Retrieve full hierarchical taxonomy of topics with child intents."""
    topics = get_all_topics(with_counts=True)
    all_intents = get_all_intents_with_topic()
    intents_by_topic = {}
    for intent in all_intents:
        intents_by_topic.setdefault(intent["topic_id"], []).append(intent)
    taxonomy_tree = []
    for t in topics:
        t_dict = dict(t)
        t_dict["intents"] = intents_by_topic.get(t["id"], [])
        taxonomy_tree.append(t_dict)
    return jsonify({
        "status": "success",
        "count": len(taxonomy_tree),
        "data": taxonomy_tree,
        "taxonomy": taxonomy_tree,
    })


# ============================================================================
# TOPICS API
# ============================================================================

@admin_bp.route("/topics", methods=["GET"])
@admin_api_required
def list_topics_route():
    """List all domain topics with counts."""
    include_all = request.args.get("all", "false").lower() in ("true", "1")
    is_active = None if include_all else 1
    topics = get_all_topics(is_active=is_active, with_counts=True)
    return jsonify({"status": "success", "count": len(topics), "data": topics})


@admin_bp.route("/topics/<int:topic_id>", methods=["GET"])
@admin_api_required
def get_topic_route(topic_id):
    """Retrieve single topic details."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        return jsonify({"error": "Not Found", "message": "Topic not found"}), 404
    return jsonify({"status": "success", "data": topic})


@admin_bp.route("/topics", methods=["POST"])
@admin_api_required
def create_topic_route():
    """Create a new domain topic."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or "").strip()
    if not name or not slug:
        return jsonify({"error": "Bad Request", "message": "name and slug are required"}), 400

    try:
        slug = validate_slug(slug)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    admin_username = session.get("admin_username", "admin")
    topic_id = admin_create_topic(
        name=name,
        slug=slug,
        description=(data.get("description") or "").strip(),
        icon=(data.get("icon") or "folder").strip(),
        admin_username=admin_username,
    )
    return jsonify({
        "status": "success",
        "id": topic_id,
        "topic_id": topic_id,
        "message": f"Topic '{name}' created."
    }), 201


@admin_bp.route("/topics/<int:topic_id>", methods=["PUT"])
@admin_api_required
def update_topic_route(topic_id):
    """Update an existing topic."""
    data = request.get_json() or {}
    existing = get_topic_by_id(topic_id)
    if not existing:
        return jsonify({"error": "Not Found", "message": "Topic not found"}), 404

    admin_username = session.get("admin_username", "admin")
    success = admin_update_topic(
        topic_id=topic_id,
        name=data.get("name", existing["name"]).strip(),
        slug=data.get("slug", existing["slug"]).strip(),
        description=data.get("description", existing.get("description", "")).strip(),
        icon=data.get("icon", existing.get("icon", "folder")).strip(),
        is_active=int(data.get("is_active", existing.get("is_active", 1))),
        admin_username=admin_username,
    )
    return jsonify({"status": "success", "message": f"Topic #{topic_id} updated."})


# ============================================================================
# INTENTS API
# ============================================================================

@admin_bp.route("/intents", methods=["GET"])
@admin_api_required
def list_intents_route():
    """List all intents with topic associations and counts."""
    include_all = request.args.get("all", "false").lower() in ("true", "1")
    is_active = None if include_all else 1
    intents = get_all_intents_with_topic(is_active=is_active, with_counts=True)
    return jsonify({"status": "success", "count": len(intents), "data": intents})


@admin_bp.route("/intents/<int:intent_id>", methods=["GET"])
@admin_api_required
def get_intent_route(intent_id):
    """Retrieve single intent details."""
    intent = get_intent_by_id(intent_id)
    if not intent:
        return jsonify({"error": "Not Found", "message": "Intent not found"}), 404
    return jsonify({"status": "success", "data": intent})


@admin_bp.route("/intents", methods=["POST"])
@admin_api_required
def create_intent_route():
    """Create a new intent associated with a topic."""
    data = request.get_json() or {}
    topic_id = data.get("topic_id")
    name = (data.get("name") or "").strip()
    slug = (data.get("slug") or "").strip()
    if not topic_id or not name or not slug:
        return jsonify({"error": "Bad Request", "message": "topic_id, name, and slug are required"}), 400

    try:
        slug = validate_slug(slug)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    admin_username = session.get("admin_username", "admin")
    intent_id = admin_create_intent(
        topic_id=int(topic_id),
        name=name,
        slug=slug,
        description=(data.get("description") or "").strip(),
        admin_username=admin_username,
    )
    return jsonify({
        "status": "success",
        "id": intent_id,
        "intent_id": intent_id,
        "message": f"Intent '{name}' created."
    }), 201


@admin_bp.route("/intents/<int:intent_id>", methods=["PUT"])
@admin_api_required
def update_intent_route(intent_id):
    """Update an existing intent and optionally reassign its topic."""
    data = request.get_json() or {}
    existing = get_intent_by_id(intent_id)
    if not existing:
        return jsonify({"error": "Not Found", "message": "Intent not found"}), 404

    admin_username = session.get("admin_username", "admin")
    topic_id = int(data["topic_id"]) if "topic_id" in data and data["topic_id"] is not None else None

    success = admin_update_intent(
        intent_id=intent_id,
        name=data.get("name", existing["name"]).strip(),
        slug=data.get("slug", existing["slug"]).strip(),
        description=data.get("description", existing.get("description", "")).strip(),
        topic_id=topic_id,
        is_active=int(data.get("is_active", existing.get("is_active", 1))),
        admin_username=admin_username,
    )
    return jsonify({"status": "success", "message": f"Intent #{intent_id} updated."})


# ============================================================================
# KNOWLEDGE ITEMS API
# ============================================================================

@admin_bp.route("/knowledge", methods=["GET"])
@admin_api_required
def list_knowledge():
    """List knowledge items with flexible status, active, and search filters."""
    status = request.args.get("status")
    if status in ("all", ""):
        status = None
    is_active_val = request.args.get("is_active")
    is_active = int(is_active_val) if is_active_val is not None and is_active_val != "all" else None
    topic_id = request.args.get("topic_id", type=int)
    search = request.args.get("search") or request.args.get("q")
    items = get_all_knowledge_items(status=status, is_active=is_active, topic_id=topic_id, search_query=search)
    return jsonify({"status": "success", "count": len(items), "data": items})


@admin_bp.route("/knowledge/<int:item_id>", methods=["GET"])
@admin_api_required
def get_knowledge_detail(item_id):
    """Get single knowledge item details."""
    item = get_knowledge_by_id(item_id)
    if not item:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404
    return jsonify({"status": "success", "data": item})


@admin_bp.route("/knowledge", methods=["POST"])
@admin_api_required
def add_knowledge():
    """Create a new verified knowledge item."""
    data = request.get_json() or {}
    intent_id = data.get("intent_id")
    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()
    content = (data.get("content") or data.get("detailed_procedure") or "").strip()

    if not intent_id or not title or not summary or not content:
        return jsonify({
            "error": "Bad Request",
            "message": "intent_id, title, summary, and content are required."
        }), 400

    intent = get_intent_by_id(int(intent_id))
    if not intent:
        return jsonify({"error": "Bad Request", "message": "Specified intent does not exist"}), 400

    portal_url = (data.get("official_portal_url") or "").strip()
    if portal_url and not is_safe_portal_url(portal_url):
        return jsonify({
            "error": "Bad Request",
            "message": "Invalid official_portal_url. Only http://, https://, or relative paths are allowed."
        }), 400

    admin_username = session.get("admin_username", "admin")
    item_id = create_knowledge_item(
        topic_id=intent["topic_id"],
        intent_id=int(intent_id),
        title=title,
        content=content,
        summary=summary,
        keywords=data.get("keywords", ""),
        source_reference=data.get("source_reference", "NIT Durgapur Verified Admin Record"),
        contact_authority=data.get("contact_authority", ""),
        official_portal_url=data.get("official_portal_url", ""),
        verified_by=data.get("verified_by", f"NIT Durgapur Verified ({admin_username})"),
        verification_status=data.get("verification_status", "verified"),
        version=1,
        is_active=1,
    )

    log_audit(
        actor_username=admin_username,
        action="CREATE_KNOWLEDGE",
        target_entity="knowledge_item",
        target_id=item_id,
        changes_summary=f"Created knowledge item '{title}' under intent #{intent_id}",
    )

    try:
        sync_knowledge_retrieval_index()
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "id": item_id,
        "knowledge_id": item_id,
        "message": "Knowledge item created."
    }), 201


@admin_bp.route("/knowledge/<int:item_id>", methods=["PUT"])
@admin_api_required
def modify_knowledge(item_id):
    """Update an existing knowledge item."""
    data = request.get_json() or {}
    existing = get_knowledge_by_id(item_id)
    if not existing:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404

    portal_url = data.get("official_portal_url", existing["official_portal_url"])
    if portal_url and not is_safe_portal_url(str(portal_url).strip()):
        return jsonify({
            "error": "Bad Request",
            "message": "Invalid official_portal_url. Only http://, https://, or relative paths are allowed."
        }), 400

    admin_username = session.get("admin_username", "admin")
    content = data.get("content") or data.get("detailed_procedure") or existing["content"]
    success = update_knowledge_item(
        item_id=item_id,
        title=data.get("title", existing["title"]),
        content=content,
        summary=data.get("summary", existing["summary"]),
        keywords=data.get("keywords", existing.get("keywords", "")),
        source_reference=data.get("source_reference", existing.get("source_reference", "")),
        contact_authority=data.get("contact_authority", existing["contact_authority"]),
        official_portal_url=data.get("official_portal_url", existing["official_portal_url"]),
        verified_by=data.get("verified_by", existing["verified_by"]),
        verification_status=data.get("verification_status", existing["verification_status"]),
        is_active=int(data.get("is_active", existing["is_active"])),
    )

    log_audit(
        actor_username=admin_username,
        action="UPDATE_KNOWLEDGE",
        target_entity="knowledge_item",
        target_id=item_id,
        changes_summary=f"Updated knowledge item '{existing['title']}' (new version {existing['version'] + 1})",
    )

    try:
        sync_knowledge_retrieval_index()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Knowledge item updated."})


@admin_bp.route("/knowledge/<int:item_id>", methods=["DELETE"])
@admin_api_required
def remove_knowledge(item_id):
    """Delete a knowledge item."""
    existing = get_knowledge_by_id(item_id)
    if not existing:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404

    admin_username = session.get("admin_username", "admin")
    delete_knowledge_item(item_id)

    log_audit(
        actor_username=admin_username,
        action="DELETE_KNOWLEDGE",
        target_entity="knowledge_item",
        target_id=item_id,
        changes_summary=f"Deleted knowledge item '{existing['title']}'",
    )

    try:
        sync_knowledge_retrieval_index()
    except Exception:
        pass

    return jsonify({"status": "success", "message": "Knowledge item deleted."})


@admin_bp.route("/knowledge/<int:item_id>/deactivate", methods=["POST"])
@admin_api_required
def deactivate_knowledge_route(item_id):
    """Deactivate a knowledge item so it is excluded from official responses."""
    admin_username = session.get("admin_username", "admin")
    from app.services.knowledge_service import deactivate_knowledge
    success = deactivate_knowledge(item_id, admin_username=admin_username)
    if not success:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404
    return jsonify({"status": "success", "message": f"Knowledge item #{item_id} deactivated."})


@admin_bp.route("/knowledge/<int:item_id>/activate", methods=["POST"])
@admin_api_required
def activate_knowledge_route(item_id):
    """Activate a deactivated knowledge item."""
    admin_username = session.get("admin_username", "admin")
    from app.services.knowledge_service import activate_knowledge
    success = activate_knowledge(item_id, admin_username=admin_username)
    if not success:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404
    return jsonify({"status": "success", "message": f"Knowledge item #{item_id} activated."})


@admin_bp.route("/knowledge/<int:item_id>/verify", methods=["POST", "PUT"])
@admin_api_required
def verify_knowledge_route(item_id):
    """Certify and mark knowledge item as verified."""
    data = request.get_json(silent=True) or {}
    admin_username = session.get("admin_username", "admin")
    verified_by = data.get("verified_by") or f"NIT Durgapur Verified ({admin_username})"
    from app.services.knowledge_service import verify_knowledge
    success = verify_knowledge(item_id, verified_by=verified_by, admin_username=admin_username)
    if not success:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404
    return jsonify({"status": "success", "message": f"Knowledge item #{item_id} marked verified."})


@admin_bp.route("/knowledge/<int:item_id>/toggle-active", methods=["POST"])
@admin_api_required
def toggle_active_knowledge_route(item_id):
    """Toggle is_active flag for a knowledge item."""
    item = get_knowledge_by_id(item_id)
    if not item:
        return jsonify({"error": "Not Found", "message": "Knowledge item not found"}), 404
    admin_username = session.get("admin_username", "admin")
    from app.services.knowledge_service import activate_knowledge, deactivate_knowledge
    if item["is_active"]:
        deactivate_knowledge(item_id, admin_username=admin_username)
        new_active = 0
    else:
        activate_knowledge(item_id, admin_username=admin_username)
        new_active = 1
    return jsonify({
        "status": "success",
        "is_active": new_active,
        "message": f"Knowledge #{item_id} active status updated."
    })


@admin_bp.route("/knowledge/search", methods=["GET"])
@admin_api_required
def search_knowledge_route():
    """Search knowledge repository items."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Bad Request", "message": "Query parameter 'q' required"}), 400
    only_eligible = request.args.get("only_eligible", "false").lower() in ("true", "1")
    from app.services.knowledge_service import search_knowledge
    results = search_knowledge(q, only_eligible=only_eligible)
    return jsonify({"status": "success", "count": len(results), "data": results})


@admin_bp.route("/unresolved", methods=["GET"])
@admin_api_required
def list_unresolved():
    """List unresolved student queries with optional status filtering and search."""
    status = request.args.get("status")
    search = (request.args.get("search") or request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 100))
    queries = get_unresolved_queries(review_status=status if status != "all" else None, limit=limit)
    if search:
        search_lower = search.lower()
        queries = [
            q for q in queries
            if search_lower in (q.get("query_text") or "").lower()
            or search_lower in (q.get("predicted_topic") or "").lower()
            or search_lower in (q.get("predicted_intent") or "").lower()
        ]
    return jsonify({
        "status": "success",
        "count": len(queries),
        "data": queries,
        "unresolved_queries": queries,
    })


@admin_bp.route("/unresolved/<int:query_id>", methods=["GET"])
@admin_api_required
def get_unresolved_detail(query_id: int):
    """Retrieve full inspection details for an unresolved student query."""
    query = get_unresolved_query_by_id(query_id)
    if not query:
        return jsonify({"error": "Not Found", "message": "Unresolved query not found"}), 404
    return jsonify({"status": "success", "data": query})


@admin_bp.route("/unresolved/<int:query_id>/resolve", methods=["POST"])
@admin_api_required
def resolve_query(query_id):
    """Resolve an unverified student query."""
    data = request.get_json() or {}
    action = data.get("action") or ("new_knowledge" if data.get("title") else "map_intent")
    admin_username = session.get("admin_username", "admin")
    created_knowledge_id = None

    if action == "map_intent":
        intent_id = data.get("intent_id")
        if not intent_id:
            return jsonify({"error": "Bad Request", "message": "intent_id is required"}), 400
        resolve_query_by_mapping_intent(
            unresolved_query_id=query_id,
            intent_id=int(intent_id),
            admin_username=admin_username,
            admin_notes=data.get("notes", ""),
        )
    elif action == "new_knowledge":
        intent_id = data.get("intent_id")
        title = data.get("title")
        summary = data.get("summary")
        procedure = data.get("detailed_procedure") or data.get("content")
        if not all([intent_id, title, summary, procedure]):
            return jsonify({"error": "Bad Request", "message": "All knowledge fields required"}), 400
        portal_url = (data.get("official_portal_url") or "").strip()
        if portal_url and not is_safe_portal_url(portal_url):
            return jsonify({
                "error": "Bad Request",
                "message": "Invalid official_portal_url. Only http://, https://, or relative paths are allowed."
            }), 400
        created_knowledge_id = resolve_query_with_new_knowledge(
            unresolved_query_id=query_id,
            intent_id=int(intent_id),
            title=title,
            summary=summary,
            detailed_procedure=procedure,
            required_documents=data.get("required_documents", ""),
            contact_authority=data.get("contact_authority", ""),
            official_portal_url=data.get("official_portal_url", ""),
            admin_username=admin_username,
            admin_notes=data.get("notes", ""),
            keywords=data.get("keywords", ""),
            source_reference=data.get("source_reference", "NIT Durgapur Verified Admin Record"),
        )
    elif action == "ignore":
        resolve_unresolved_query(
            query_id=query_id,
            resolution_intent_id=None,
            admin_notes=data.get("notes", "Dismissed by admin"),
            reviewed_by=admin_username,
            review_status="ignored",
        )
    else:
        return jsonify({"error": "Bad Request", "message": "Invalid action"}), 400

    resp = {"status": "success", "message": "Query successfully triaged."}
    if created_knowledge_id is not None:
        resp["knowledge_item_id"] = created_knowledge_id
    return jsonify(resp)


@admin_bp.route("/unresolved/<int:query_id>/status", methods=["POST"])
@admin_api_required
def update_query_status(query_id: int):
    """Transition the status of an unresolved student query."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "Bad Request", "message": "Field 'status' is required."}), 400

    admin_username = session.get("admin_username", "admin")
    notes = data.get("notes") or data.get("admin_notes", "")

    try:
        success = update_unresolved_query_status(
            query_id=query_id,
            new_status=new_status,
            admin_notes=notes,
            reviewed_by=admin_username,
        )
        if not success:
            return jsonify({"error": "Not Found", "message": "Unresolved query not found."}), 404
        return jsonify({
            "status": "success",
            "message": f"Query status successfully updated to '{new_status}'.",
            "query_id": query_id,
            "new_status": new_status,
        }), 200
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400


@admin_bp.route("/audit", methods=["GET"])
@admin_api_required
def list_audit_logs():
    """List recent administrative audit entries with optional action/entity filter."""
    limit = int(request.args.get("limit", 50))
    action_filter = request.args.get("action")
    entity_filter = request.args.get("entity") or request.args.get("target_entity")
    logs = get_recent_audit_logs(limit=limit, action_filter=action_filter, target_entity=entity_filter)
    return jsonify({"status": "success", "count": len(logs), "data": logs})


@admin_bp.route("/sync", methods=["POST"])
@admin_api_required
def sync_index_route():
    """Trigger in-memory semantic vector store and classifier re-indexing."""
    count = sync_knowledge_retrieval_index()
    return jsonify({
        "status": "success",
        "message": f"Semantic knowledge index re-indexed successfully. {count} verified items indexed.",
        "indexed_count": count,
    })
