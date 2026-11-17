"""
CampusAssist: Public REST API Routes.
Student-facing endpoints for conversation, suggested questions, and feedback.
"""

import uuid
import time
import sqlite3
from flask import Blueprint, request, jsonify
from app.models.repositories import (
    get_all_topics,
    get_all_intents_with_topic,
    get_all_training_queries,
    update_chat_feedback,
    get_conversation_messages,
    get_all_conversations,
    get_conversation,
    create_conversation,
    update_conversation_title,
    delete_conversation,
    delete_all_conversations,
)
from app.services.chat_service import get_chat_pipeline
from app.services.llm.logger_sanitizer import get_sanitized_logger
from app.services.rate_limiter import rate_limit
from app.services.security_utils import sanitize_identifier

logger = get_sanitized_logger(__name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/suggestions", methods=["GET"])
def get_suggestions():
    """Return starter topics and suggested questions for the chat interface."""
    topics = get_all_topics()
    queries = get_all_training_queries()

    # Group sample queries by topic
    suggested_chips = [
        "How can I apply for hostel leave?",
        "I need to go home for two days. What is the procedure?",
        "Can I change my hostel room?",
        "Food quality is bad in hall mess",
        "How to register for odd semester courses?",
        "What is the minimum attendance required at NIT Durgapur?",
        "How to get a bonafide certificate from NIT Durgapur?",
    ]

    return jsonify({
        "status": "success",
        "topics": topics,
        "suggested_questions": suggested_chips,
        "total_sample_queries": len(queries),
    })


@api_bp.route("/topics", methods=["GET"])
def get_topics_list():
    """Retrieve all available verified topics and their intents."""
    topics = get_all_topics()
    intents = get_all_intents_with_topic()

    # Nest intents under topics
    topic_map = {t["id"]: {**t, "intents": []} for t in topics}
    for intent in intents:
        t_id = intent["topic_id"]
        if t_id in topic_map:
            topic_map[t_id]["intents"].append({
                "id": intent["id"],
                "name": intent["name"],
                "slug": intent["slug"],
                "description": intent["description"],
            })

    return jsonify({
        "status": "success",
        "topics": list(topic_map.values())
    })


@api_bp.route("/chat", methods=["POST"])
@rate_limit(limit=60, window_seconds=60, key_prefix="student_chat")
def chat():
    """
    Primary student chat query endpoint.
    Processes query through the complete 14-step backend pipeline:
    Validation -> Student Message Storage -> Intent Classification ->
    Semantic Retrieval -> Confidence Gating -> Controlled LLM Synthesis ->
    Assistant Message Storage (or Unresolved Query Triage).
    """
    data = request.get_json(silent=True) or {}
    query = data.get("query")
    raw_session_id = data.get("session_id")
    session_id = None
    if raw_session_id is not None and str(raw_session_id).strip():
        try:
            session_id = sanitize_identifier(str(raw_session_id).strip(), max_len=64)
        except ValueError as ve:
            return jsonify({"error": "Bad Request", "message": f"Invalid session_id: {ve}"}), 400

    pipeline = get_chat_pipeline()

    try:
        result = pipeline.process_chat(
            query=query,
            session_id=session_id,
        )

        # Student Privacy Shield: Ensure internal triage/administrative fields are never exposed to students
        student_response = {
            "status": result.get("status", "received"),
            "success": result.get("success", True),
            "session_id": result.get("session_id"),
            "conversation_id": result.get("conversation_id"),
            "query": result.get("query"),
            "answer": result.get("answer"),
            "is_verified": result.get("is_verified", False),
            "topic": result.get("topic"),
            "topic_slug": result.get("topic_slug"),
            "intent": result.get("intent"),
            "intent_slug": result.get("intent_slug"),
            "confidence": result.get("confidence"),
            "sources": result.get("sources", []),
            "authority_contact": result.get("authority_contact", ""),
            "official_url": result.get("official_url", ""),
            "knowledge_items": result.get("knowledge_items", []),
            "message_id": result.get("message_id"),
            "chat_log_id": result.get("chat_log_id"),
            "user_message_id": result.get("user_message_id"),
            "latency_seconds": result.get("latency_seconds"),
            "timings_ms": result.get("timings_ms"),
        }
        return jsonify(student_response), 200


    except ValueError as ve:
        logger.warning(f"Bad request to /api/chat: {ve}")
        return jsonify({
            "error": "Bad Request",
            "message": str(ve)
        }), 400

    except sqlite3.Error as sqle:
        logger.error(f"Database error in /api/chat: {sqle}", exc_info=True)
        return jsonify({
            "error": "Service Unavailable",
            "message": "CampusAssist database is temporarily unavailable. Please try again shortly."
        }), 503

    except Exception as e:
        logger.error(f"Unexpected error in /api/chat pipeline: {e}", exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "We encountered an unexpected issue while processing your question. Please try again in a few moments."
        }), 500


@api_bp.route("/conversations", methods=["GET"])
def list_conversations():
    """Retrieve recent conversation sessions with message counts and previews."""
    raw_limit = request.args.get("limit", default=50, type=int)
    try:
        limit = max(1, min(100, int(raw_limit)))
    except (ValueError, TypeError):
        limit = 50
    conversations = get_all_conversations(limit=limit)
    return jsonify({
        "status": "success",
        "total_conversations": len(conversations),
        "conversations": conversations,
    }), 200


@api_bp.route("/conversations", methods=["POST"])
@rate_limit(limit=30, window_seconds=60, key_prefix="student_conv_write")
def create_new_conversation():
    """Explicitly create a new conversation session."""
    data = request.get_json(silent=True) or {}
    raw_title = (data.get("title") or "New Conversation").strip()
    title = raw_title[:100] if raw_title else "New Conversation"
    conv_id = f"session_{uuid.uuid4().hex[:12]}_{int(time.time())}"
    created_id = create_conversation(conv_id, title=title)
    return jsonify({
        "status": "success",
        "conversation_id": created_id,
        "title": title,
    }), 201


@api_bp.route("/conversations/<conversation_id>", methods=["GET"])
def get_single_conversation(conversation_id: str):
    """Retrieve metadata and message count for a specific conversation."""
    try:
        clean_id = sanitize_identifier(conversation_id, max_len=64)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    conv = get_conversation(clean_id)
    if not conv:
        return jsonify({"error": "Not Found", "message": "Conversation not found."}), 404
    messages = get_conversation_messages(clean_id)
    return jsonify({
        "status": "success",
        "conversation": conv,
        "total_messages": len(messages),
        "messages": messages,
    }), 200


@api_bp.route("/conversations/<conversation_id>", methods=["PATCH"])
def rename_conversation(conversation_id: str):
    """Update title of an existing conversation."""
    try:
        clean_id = sanitize_identifier(conversation_id, max_len=64)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:100]
    if not title:
        return jsonify({"error": "Bad Request", "message": "Title cannot be empty."}), 400

    success = update_conversation_title(clean_id, title)
    if not success:
        return jsonify({"error": "Not Found", "message": "Conversation not found."}), 404
    return jsonify({
        "status": "success",
        "conversation_id": clean_id,
        "title": title,
    }), 200


@api_bp.route("/conversations/<conversation_id>", methods=["DELETE"])
def delete_single_conversation(conversation_id: str):
    """Delete a specific conversation and all associated messages."""
    try:
        clean_id = sanitize_identifier(conversation_id, max_len=64)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    success = delete_conversation(clean_id)
    if not success:
        return jsonify({"error": "Not Found", "message": "Conversation not found."}), 404
    return jsonify({
        "status": "success",
        "message": "Conversation deleted successfully.",
        "conversation_id": clean_id,
    }), 200


@api_bp.route("/conversations", methods=["DELETE"])
@rate_limit(limit=10, window_seconds=60, key_prefix="student_conv_clear")
def clear_all_student_conversations():
    """Clear all conversation history."""
    count = delete_all_conversations()
    return jsonify({
        "status": "success",
        "message": "All conversations cleared.",
        "deleted_count": count,
    }), 200


@api_bp.route("/conversations/<conversation_id>/messages", methods=["GET"])
def get_conversation_history(conversation_id: str):
    """Retrieve chronological message history for a specific conversation session."""
    try:
        clean_id = sanitize_identifier(conversation_id, max_len=64)
    except ValueError as ve:
        return jsonify({"error": "Bad Request", "message": str(ve)}), 400

    messages = get_conversation_messages(clean_id)
    return jsonify({
        "status": "success",
        "conversation_id": clean_id,
        "total_messages": len(messages),
        "messages": messages,
    })


@api_bp.route("/feedback", methods=["POST"])
@rate_limit(limit=30, window_seconds=60, key_prefix="student_feedback")
def submit_feedback():
    """Record student feedback (helpful/unhelpful) on an answer."""
    data = request.get_json(silent=True) or {}
    raw_chat_log_id = data.get("chat_log_id")
    feedback = data.get("feedback")

    try:
        chat_log_id = int(raw_chat_log_id)
        if chat_log_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            "error": "Bad Request",
            "message": "Valid positive integer chat_log_id is required."
        }), 400

    if feedback not in ("helpful", "unhelpful"):
        return jsonify({
            "error": "Bad Request",
            "message": "Feedback must be 'helpful' or 'unhelpful'."
        }), 400

    success = update_chat_feedback(chat_log_id, feedback)
    return jsonify({
        "status": "success" if success else "not_found",
        "chat_log_id": chat_log_id,
        "feedback": feedback
    })
