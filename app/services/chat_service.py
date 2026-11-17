"""
CampusAssist: Core Backend Chat Pipeline Service.
Orchestrates the complete 14-step student query resolution workflow:
1. Receive question
2. Validate input
3. Store student message
4. Process query
5. Determine topic
6. Determine intent
7. Generate embedding
8. Perform semantic retrieval
9. Evaluate retrieval confidence
10. Determine information sufficiency
11. If sufficient: send verified context to controlled LLM
12. Generate answer
13. Store assistant response
14. Return structured response

If no reliable verified information exists:
1. Do not invent an NIT answer
2. Generate safe fallback response
3. Store unresolved query for admin review
4. Return safe response
"""

import uuid
import time
from typing import Optional, Dict, Any, List

from config import Config
from app.models.db import get_db
from app.models.repositories import (
    create_conversation,
    get_conversation,
    update_conversation_title,
    create_message,
    get_conversation_messages,
    log_unresolved_query,
)
from app.services.classifier.intent_classifier import (
    SemanticIntentClassifier,
    get_classifier,
    ClassificationResult,
)
from app.services.retrieval.semantic_search import (
    SemanticRetrievalEngine,
    get_retrieval_engine,
    RetrievalResult,
)
from app.services.llm.service import (
    LLMService,
    get_llm_service,
    GroundedResponse,
)
from app.services.llm.prompt_builder import PromptBuilder
from app.services.context_manager import ConversationContextManager
from app.services.llm.logger_sanitizer import get_sanitized_logger

logger = get_sanitized_logger(__name__)

MAX_QUERY_LENGTH = 1500


class ChatPipelineService:
    """
    Modular, decoupled service coordinating conversational state,
    semantic classification, vector retrieval, grounded LLM generation,
    and unresolved triage.
    """

    def __init__(
        self,
        classifier: Optional[SemanticIntentClassifier] = None,
        retrieval_engine: Optional[SemanticRetrievalEngine] = None,
        llm_service: Optional[LLMService] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        context_manager: Optional[ConversationContextManager] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.classifier = classifier or get_classifier()
        self.retrieval_engine = retrieval_engine or get_retrieval_engine()
        self.llm_service = llm_service or get_llm_service()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.context_manager = context_manager or ConversationContextManager()
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else Config.CONFIDENCE_THRESHOLD
        )

    def validate_input(self, query: Any) -> str:
        """
        Validates student query input.
        Raises ValueError with friendly student message if invalid, empty, or exceeds length limit.
        """
        if query is None:
            raise ValueError("Question cannot be null and is required. Please provide a question.")

        if not isinstance(query, str):
            raise ValueError("Question must be a string. Please provide a valid text question.")

        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Question cannot be empty. Please enter your query.")

        if len(clean_query) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Question is too long and exceeds maximum allowed length ({MAX_QUERY_LENGTH} characters). "
                f"Your query is {len(clean_query)} characters; please shorten it."
            )

        return clean_query

    def process_chat(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[int] = None,
        conn=None,
    ) -> Dict[str, Any]:
        """
        Executes the full 14-step backend chat workflow.
        Guarantees zero institutional policy hallucination and graceful degradation.
        """
        db = conn or get_db()
        start_time = time.perf_counter()


        # Step 1 & 2: Receive Question & Validate Input
        clean_query = self.validate_input(query)

        # Step 3: Session & Conversation Setup
        active_session_id = (session_id or "").strip()
        if not active_session_id:
            active_session_id = f"session_{uuid.uuid4().hex[:12]}_{int(time.time())}"

        prior_messages = []
        user_msg_id = None
        try:
            prior_messages = get_conversation_messages(active_session_id, conn=db)
            is_first_message = len(prior_messages) == 0
            clean_title = clean_query[:42] + ("..." if len(clean_query) > 42 else "")
            create_conversation(
                conversation_id=active_session_id,
                user_id=user_id,
                title=clean_title,
                conn=db,
            )
            if is_first_message:
                update_conversation_title(active_session_id, clean_title, conn=db)

            # Step 4: Store Student Message
            user_msg_id = create_message(
                conversation_id=active_session_id,
                role="user",
                content=clean_query,
                conn=db,
            )
            logger.info(f"Received query in session '{active_session_id}' (msg #{user_msg_id}): '{clean_query[:60]}'")
        except Exception as db_err:
            logger.error(f"Database warning during session/message setup: {db_err}", exc_info=True)

        try:
            # Step 5 & 6: Determine Topic & Intent
            t_clf_start = time.perf_counter()
            classification: ClassificationResult = self.classifier.classify(clean_query, conn=db)
            clf_duration_ms = round((time.perf_counter() - t_clf_start) * 1000, 2)
            topic_name = classification.topic_name
            topic_slug = classification.topic_slug
            intent_name = classification.intent_name
            intent_slug = classification.intent_slug
            classifier_confidence = classification.confidence

            # Step 7 & 8: Generate Embedding & Perform Semantic Retrieval
            t_ret_start = time.perf_counter()
            retrieved_items: List[RetrievalResult] = self.retrieval_engine.retrieve(
                query=clean_query,
                top_k=3,
                threshold=self.confidence_threshold,
                conn=db,
            )

            # Step 8a: High-confidence classifier assisted retrieval
            if not retrieved_items and classification.is_confident and classification.intent_id:
                relaxed_thresh = min(self.confidence_threshold, 0.30)
                candidate_items = self.retrieval_engine.retrieve(
                    query=clean_query,
                    top_k=3,
                    threshold=relaxed_thresh,
                    topic_id=classification.topic_id,
                    conn=db,
                )
                if candidate_items:
                    matching_intent_items = [ci for ci in candidate_items if ci.intent_id == classification.intent_id]
                    if matching_intent_items:
                        retrieved_items = matching_intent_items

            # Step 8b: Contextual Follow-up Disambiguation
            if prior_messages and (
                len(retrieved_items) == 0
                or not classification.is_confident
                or self.context_manager.is_likely_followup(clean_query, prior_messages, classifier_confidence, self.confidence_threshold)
            ):
                context_query, last_ctx = self.context_manager.build_contextual_retrieval_query(clean_query, prior_messages)
                if context_query != clean_query:
                    logger.info(f"Synthesized contextual follow-up query: '{context_query}' (original: '{clean_query}')")
                    context_retrieved = self.retrieval_engine.retrieve(
                        query=context_query,
                        top_k=3,
                        threshold=min(self.confidence_threshold, 0.45),
                        conn=db,
                    )
                    if context_retrieved:
                        if not retrieved_items or context_retrieved[0].similarity_score > retrieved_items[0].similarity_score:
                            retrieved_items = context_retrieved
                            top_item = retrieved_items[0]
                            topic_name = top_item.topic_name
                            topic_slug = top_item.topic_slug
                            intent_name = top_item.intent_name
                            intent_slug = top_item.intent_slug
                            classifier_confidence = max(classifier_confidence, top_item.similarity_score)

            ret_duration_ms = round((time.perf_counter() - t_ret_start) * 1000, 2)

            # Format recent history for prompt
            conversation_context_str = self.context_manager.format_recent_history_for_prompt(prior_messages)

            # Step 9 & 10: Evaluate Retrieval Confidence & Information Sufficiency
            is_sufficient = len(retrieved_items) > 0

            # Step 11 & 12: Branch Based on Information Sufficiency
            if is_sufficient:
                # === SUFFICIENT VERIFIED KNOWLEDGE ===
                top_item = retrieved_items[0]
                retrieval_score = top_item.similarity_score
                combined_confidence = max(retrieval_score, classifier_confidence) if classification.is_confident else retrieval_score

                logger.info(
                    f"Sufficient verified match for '{clean_query[:50]}': "
                    f"[{top_item.intent_name}] '{top_item.title}' (score: {combined_confidence:.4f})"
                )

                t_llm_start = time.perf_counter()
                grounded_resp: GroundedResponse = self.llm_service.generate_grounded_response(
                    query=clean_query,
                    topic_name=top_item.topic_name,
                    intent_name=top_item.intent_name,
                    retrieved_items=retrieved_items,
                    confidence_score=combined_confidence,
                    conversation_context=conversation_context_str,
                )
                llm_duration_ms = round((time.perf_counter() - t_llm_start) * 1000, 2)

                # Step 13: Store Assistant Response
                assistant_msg_id = None
                try:
                    assistant_msg_id = create_message(
                        conversation_id=active_session_id,
                        role="assistant",
                        content=grounded_resp.answer,
                        matched_intent_id=top_item.intent_id,
                        matched_knowledge_id=top_item.item_id,
                        confidence_score=combined_confidence,
                        is_verified=True,
                        conn=db,
                    )
                except Exception as save_err:
                    logger.error(f"Failed to persist assistant message: {save_err}", exc_info=True)

                total_latency = time.perf_counter() - start_time
                total_duration_ms = round(total_latency * 1000, 2)
                logger.info(
                    f"Performance [{clean_query[:35]}]: Total {total_duration_ms:.1f}ms "
                    f"(Classification: {clf_duration_ms}ms, Retrieval: {ret_duration_ms}ms, LLM: {llm_duration_ms}ms)"
                )

                # Step 14: Return Complete Structured Response
                return {
                    "status": "received",
                    "success": True,
                    "session_id": active_session_id,
                    "conversation_id": active_session_id,
                    "query": clean_query,
                    "answer": grounded_resp.answer,
                    "is_verified": True,
                    "topic": top_item.topic_name,
                    "topic_slug": top_item.topic_slug,
                    "intent": top_item.intent_name,
                    "intent_slug": top_item.intent_slug,
                    "confidence": round(combined_confidence, 4),
                    "sources": grounded_resp.sources,
                    "authority_contact": grounded_resp.authority_contact,
                    "official_url": grounded_resp.official_url,
                    "knowledge_items": [item.to_dict() for item in retrieved_items],
                    "message_id": assistant_msg_id,
                    "chat_log_id": assistant_msg_id,
                    "user_message_id": user_msg_id,
                    "model_used": grounded_resp.model_used,
                    "latency_seconds": round(total_latency, 4),
                    "timings_ms": {
                        "classification": clf_duration_ms,
                        "retrieval": ret_duration_ms,
                        "llm": llm_duration_ms,
                        "total": total_duration_ms,
                    },
                }


            else:
                # === INSUFFICIENT / UNVERIFIED KNOWLEDGE (CIRCUIT BREAKER) ===
                logger.info(
                    f"No verified match met threshold {self.confidence_threshold:.2f} for '{clean_query[:50]}'. "
                    f"Generating safe response and recording unresolved query."
                )

                fallback_resp: GroundedResponse = self.prompt_builder.build_unverified_fallback_response(
                    student_question=clean_query,
                    topic_name=topic_name,
                    intent_name=intent_name,
                )

                best_retrieval_conf = retrieved_items[0].similarity_score if retrieved_items else 0.0
                predicted_triage_topic = topic_name or "General"
                predicted_triage_intent = intent_name
                if not intent_name and classification.candidates:
                    predicted_triage_intent = classification.candidates[0].intent_name

                unresolved_id = None
                try:
                    unresolved_id = log_unresolved_query(
                        original_question=clean_query,
                        conversation_id=active_session_id,
                        predicted_topic=predicted_triage_topic,
                        predicted_intent=predicted_triage_intent,
                        classification_confidence=classifier_confidence,
                        retrieval_confidence=best_retrieval_conf,
                        confidence=max(classifier_confidence, best_retrieval_conf),
                        retrieval_info=f"Confidence below threshold ({self.confidence_threshold:.2f}).",
                        status="unresolved",
                        conn=db,
                    )
                except Exception as unres_err:
                    logger.error(f"Failed to log unresolved query: {unres_err}", exc_info=True)

                assistant_msg_id = None
                try:
                    assistant_msg_id = create_message(
                        conversation_id=active_session_id,
                        role="assistant",
                        content=fallback_resp.answer,
                        matched_intent_id=None,
                        matched_knowledge_id=None,
                        confidence_score=classifier_confidence,
                        is_verified=False,
                        conn=db,
                    )
                except Exception as save_err:
                    logger.error(f"Failed to persist fallback assistant message: {save_err}", exc_info=True)

                total_latency = time.perf_counter() - start_time
                total_duration_ms = round(total_latency * 1000, 2)
                logger.info(
                    f"Performance [Unverified - {clean_query[:35]}]: Total {total_duration_ms:.1f}ms "
                    f"(Classification: {clf_duration_ms}ms, Retrieval: {ret_duration_ms}ms, Fallback Synthesis: 0ms)"
                )

                return {
                    "status": "received",
                    "success": True,
                    "session_id": active_session_id,
                    "conversation_id": active_session_id,
                    "query": clean_query,
                    "answer": fallback_resp.answer,
                    "is_verified": False,
                    "topic": topic_name,
                    "topic_slug": topic_slug,
                    "intent": intent_name,
                    "intent_slug": intent_slug,
                    "confidence": round(classifier_confidence, 4),
                    "sources": fallback_resp.sources,
                    "authority_contact": fallback_resp.authority_contact,
                    "official_url": fallback_resp.official_url,
                    "knowledge_items": [],
                    "unresolved_query_id": unresolved_id,
                    "message_id": assistant_msg_id,
                    "chat_log_id": assistant_msg_id,
                    "user_message_id": user_msg_id,
                    "model_used": fallback_resp.model_used,
                    "latency_seconds": round(total_latency, 4),
                    "timings_ms": {
                        "classification": clf_duration_ms,
                        "retrieval": ret_duration_ms,
                        "llm": 0.0,
                        "total": total_duration_ms,
                    },
                }


        except Exception as pipeline_err:
            logger.error(f"Pipeline processing error for query '{clean_query[:50]}': {pipeline_err}", exc_info=True)
            return {
                "status": "degraded",
                "success": True,
                "session_id": active_session_id,
                "conversation_id": active_session_id,
                "query": clean_query,
                "answer": (
                    "I'm temporarily having difficulty accessing the verified NIT Durgapur guidelines. "
                    "Please try asking your question again in a moment, or contact the relevant department or "
                    "Dean (Student Welfare) office directly."
                ),
                "is_verified": False,
                "topic": "General",
                "topic_slug": "general",
                "intent": "Unresolved Inquiry",
                "intent_slug": "unresolved_inquiry",
                "confidence": 0.0,
                "sources": [],
                "authority_contact": "Dean (Student Welfare) / Academic Section",
                "official_url": "https://nitdgp.ac.in",
                "knowledge_items": [],
                "latency_seconds": round(time.time() - start_time, 4),
            }


# Global singleton instance
_global_chat_pipeline: Optional[ChatPipelineService] = None


def get_chat_pipeline(force_reload: bool = False) -> ChatPipelineService:
    """Retrieve or initialize the global ChatPipelineService singleton."""
    global _global_chat_pipeline
    if _global_chat_pipeline is None or force_reload:
        _global_chat_pipeline = ChatPipelineService()
    return _global_chat_pipeline
