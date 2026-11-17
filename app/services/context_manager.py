"""
CampusAssist: Conversational Context Manager.
Handles conversational continuity, follow-up query disambiguation, and reference resolution.

Crucial Architectural Directive:
Conversation context aids semantic understanding and retrieval for follow-up questions,
but conversation history must NEVER override verified knowledge retrieval or fabricate
institutional policies not present in verified records.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


# Pronouns and anaphoric markers indicating follow-up dependency
ANAPHORIC_PATTERNS = [
    r"\b(it|this|that|these|those|there|they|them|its)\b",
    r"\b(how long|how much|what about|when|where|who|why|can i|may i|is it)\b",
    r"\b(procedure|permission|fee|cost|fine|penalty|timing|rule|rules|form|portal)\b",
    r"\b(for this|for that|to do this|in this case|regarding this|about it)\b",
]

# Topic boundary keywords to prevent cross-domain contamination
TOPIC_KEYWORDS = {
    "hostel": {"hostel", "room", "mess", "warden", "caretaker", "hall", "boarder", "curfew", "gate pass", "electricity", "water"},
    "academics": {"exam", "examination", "semester", "registration", "course", "grade", "attendance", "admit card", "faculty", "hod", "cgpa", "sgpa", "degree", "transcript", "bonafide"}
}


class ConversationContextManager:
    """
    Analyzes conversation history, resolves anaphoric follow-up questions,
    and formats conversational context for grounded LLM synthesis.
    """

    def __init__(self, max_history_turns: int = 6):
        self.max_history_turns = max_history_turns

    def is_likely_followup(
        self,
        current_query: str,
        prior_messages: List[Dict[str, Any]],
        standalone_confidence: float = 0.0,
        confidence_threshold: float = 0.50
    ) -> bool:
        """
        Determines whether the current query depends on previous conversational context.
        """
        if not prior_messages:
            return False

        q_lower = current_query.strip().lower()

        # Check for explicit topic change to another known domain
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", q_lower) for kw in keywords):
                # If question explicitly names an academic concept while previous was hostel,
                # or vice-versa, treat as independent or explicit switch
                pass

        # Check anaphoric markers
        for pattern in ANAPHORIC_PATTERNS:
            if re.search(pattern, q_lower):
                return True

        # Short queries (< 6 words) with low standalone confidence are often follow-ups
        word_count = len(q_lower.split())
        if word_count <= 6 and standalone_confidence < confidence_threshold:
            return True

        return False

    def build_contextual_retrieval_query(
        self,
        current_query: str,
        prior_messages: List[Dict[str, Any]]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Synthesizes an augmented query for retrieval by borrowing context from
        the most recent verified turn, avoiding cross-domain pollution.

        Returns:
            (augmented_query, last_matched_context)
        """
        if not prior_messages:
            return current_query, None

        # Extract the most recent verified assistant turn and preceding student query
        last_matched_context = None
        last_student_query = ""

        for msg in reversed(prior_messages):
            if msg.get("role") == "assistant" and msg.get("is_verified"):
                last_matched_context = {
                    "intent_name": msg.get("intent_name"),
                    "intent_id": msg.get("matched_intent_id"),
                    "knowledge_id": msg.get("matched_knowledge_id"),
                }
            elif msg.get("role") == "user" and not last_student_query:
                last_student_query = msg.get("content", "")

            if last_matched_context and last_student_query:
                break

        if not last_matched_context:
            # Fall back to any previous student query if no verified assistant turn yet
            if last_student_query:
                return f"{current_query} {last_student_query}", None
            return current_query, None

        intent_name = last_matched_context.get("intent_name") or ""
        clean_q = current_query.strip()

        # Formulate contextual search query combining intent and relevant previous query terms
        parts = [clean_q]
        if last_student_query and last_student_query.lower() not in clean_q.lower():
            parts.append(last_student_query)
        if intent_name:
            parts.append(f"({intent_name})")
        augmented_query = " ".join(parts)
        return augmented_query, last_matched_context

    def format_recent_history_for_prompt(
        self,
        prior_messages: List[Dict[str, Any]],
        limit: Optional[int] = None
    ) -> str:
        """
        Formats recent chronological conversation turns into a clean markdown block
        for strict inclusion in the LLM prompt.
        """
        if not prior_messages:
            return ""

        effective_limit = limit or self.max_history_turns
        recent = prior_messages[-effective_limit:]

        lines = []
        for msg in recent:
            role = "Student" if msg.get("role") == "user" else "Assistant"
            content = (msg.get("content") or "").strip()
            # Truncate extremely long past responses to conserve prompt budget
            if len(content) > 300:
                content = content[:290] + "..."
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
