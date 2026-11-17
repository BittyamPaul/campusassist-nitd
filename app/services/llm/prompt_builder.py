"""
CampusAssist: Grounded Prompt Builder.
Constructs strictly bounded prompts that guarantee the LLM remains an interface
synthesizer rather than the source of truth for NIT Durgapur policies.

Enforces:
SYSTEM INSTRUCTIONS + STUDENT QUESTION + TOPIC + INTENT + RETRIEVED VERIFIED NIT INFORMATION
"""

from typing import List, Optional, Dict, Any

from app.services.llm.generator import GroundedResponse
from app.services.retrieval.search import RetrievalResult


DEFAULT_SYSTEM_INSTRUCTIONS = """You are CampusAssist, the official AI student assistant for the National Institute of Technology Durgapur (NIT Durgapur).
Your purpose is to help students, faculty, and campus boarders navigate institute procedures with extreme accuracy.

CRITICAL OPERATIONAL & GROUNDING DIRECTIVES:
1. SOLE SOURCE OF TRUTH: The RETRIEVED VERIFIED NIT INFORMATION provided below is your ONLY source of truth for institutional rules.
2. STRICT GROUNDING: Answer using ONLY the supplied verified information.
3. ZERO FABRICATION: Do NOT invent institutional policies, hall rules, attendance percentages, or disciplinary actions.
4. NO ASSUMPTIONS: Do NOT assume or extrapolate missing rules, deadlines, fees, or procedural steps.
5. NO HALLUCINATED CONTACTS: Do NOT fabricate phone numbers, email addresses, office locations, or portal URLs. Use only those explicitly listed in the verified context.
6. UNCONFIRMED INFORMATION: If the student's question cannot be fully answered using the provided verified information, you MUST clearly state: "This specific detail cannot be confirmed from official NIT Durgapur verified records."
7. CITATION & GUIDANCE: Clearly cite the official source reference, responsible administrative authority, and official portal URL provided in the verified context.
8. TONE: Professional, supportive, clear, and structured (use step-by-step numbers or bullet points where appropriate)."""


class PromptBuilder:
    """Builds structured, strictly grounded prompts for LLM completion."""

    def __init__(self, system_instructions: str = DEFAULT_SYSTEM_INSTRUCTIONS):
        self.system_instructions = system_instructions.strip()

    def get_system_instructions(self) -> str:
        """Returns the base system instructions."""
        return self.system_instructions

    def build_prompt(
        self,
        student_question: str,
        topic_name: Optional[str] = None,
        intent_name: Optional[str] = None,
        retrieved_items: Optional[List[RetrievalResult]] = None,
        conversation_context: Optional[str] = None,
    ) -> str:
        """
        Assembles the strictly grounded prompt adhering to the architectural specification:
        SYSTEM INSTRUCTIONS + STUDENT QUESTION + TOPIC + INTENT + [CONVERSATION HISTORY] + RETRIEVED VERIFIED NIT INFORMATION
        """
        parts = []

        # 1. System Instructions Header
        parts.append("### SYSTEM INSTRUCTIONS")
        parts.append(self.system_instructions)
        parts.append("")

        # 2. Student Question
        parts.append("### STUDENT QUESTION")
        parts.append(f'"{student_question.strip()}"')
        parts.append("")

        # 3. Topic & Intent Classification
        parts.append("### TOPIC & INTENT CLASSIFICATION")
        parts.append(f"Domain Topic: {topic_name or 'General Campus Assistance'}")
        parts.append(f"Classified Intent: {intent_name or 'General Information'}")
        parts.append("")

        # 4. Recent Conversational Context (if follow-up question)
        if conversation_context and conversation_context.strip():
            parts.append("### CONVERSATION HISTORY (RECENT TURNS)")
            parts.append(conversation_context.strip())
            parts.append(
                "> **CONVERSATION HISTORY GROUNDING CONSTRAINT**:\n"
                "> Prior conversation turns are provided ONLY for conversational continuity (resolving references like 'it', 'this', or follow-up scope).\n"
                "> You must NEVER use prior conversation turns to invent, extrapolate, or assume new rules, policies, fees, or permissions.\n"
                "> All factual answers MUST be 100% grounded in the RETRIEVED VERIFIED NIT INFORMATION below.\n"
                "> If the verified records do not specify the detail requested in the follow-up, explicitly state that it is not specified in the verified records."
            )
            parts.append("")

        # 4. Retrieved Verified NIT Information
        parts.append("### RETRIEVED VERIFIED NIT INFORMATION (AUTHORITATIVE)")
        if not retrieved_items:
            parts.append("[NO VERIFIED RECORDS FOUND FOR THIS QUERY]")
        else:
            for idx, item in enumerate(retrieved_items, start=1):
                parts.append(f"--- Record #{idx}: {item.title} ---")
                parts.append(f"Verification Status: {item.verification_status.upper()} (v{item.version})")
                if item.summary:
                    parts.append(f"Official Summary: {item.summary}")
                parts.append(f"Official Content / Procedure:\n{item.content}")
                if item.keywords:
                    parts.append(f"Relevant Keywords: {item.keywords}")
                if item.source_reference:
                    parts.append(f"Official Document Reference: {item.source_reference}")
                if item.contact_authority:
                    parts.append(f"Responsible Authority: {item.contact_authority}")
                if item.official_portal_url:
                    parts.append(f"Official Institute Portal: {item.official_portal_url}")
                parts.append("")

        # 5. Response Directives
        parts.append("### RESPONSE DIRECTIVES")
        parts.append(
            "- Synthesize a helpful, direct response to the student's question using ONLY the verified records above.\n"
            "- List the exact procedural steps if a procedure is described.\n"
            "- Conclude with the responsible authority and portal link for student follow-up.\n"
            "- If any part of the question is not covered in the verified records, explicitly state that it cannot be confirmed."
        )

        return "\n".join(parts)

    def build_unverified_fallback_response(
        self,
        student_question: str,
        topic_name: Optional[str] = None,
        intent_name: Optional[str] = None,
    ) -> GroundedResponse:
        """
        Constructs a safe, transparent fallback response when no verified records match the query.
        Prevents calling the LLM into a hallucination trap.
        """
        category_hint = f" regarding **{topic_name}**" if topic_name else ""
        intent_hint = f" ({intent_name})" if intent_name else ""

        answer = (
            f"I cannot provide an official verified answer for your question{category_hint}{intent_hint} "
            f"because no matching authoritative record was found in the NIT Durgapur Knowledge Repository.\n\n"
            "**What you can do:**\n"
            "1. Please consult the **Chief Warden Office**, your **Hall Warden / Caretaker**, or the **Academic Section** directly.\n"
            "2. Visit the official institute website at [https://nitdgp.ac.in](https://nitdgp.ac.in) for official circulars and notices.\n"
            "3. Your question has been recorded for administrator review to update the verified knowledge base."
        )

        return GroundedResponse(
            answer=answer,
            is_verified=False,
            confidence_score=0.0,
            topic_name=topic_name,
            intent_name=intent_name,
            sources=["NIT Durgapur Verified Repository (No Match)"],
            authority_contact="NIT Durgapur Administration / Academic Section / Chief Warden Office",
            official_url="https://nitdgp.ac.in",
            model_used="safe_fallback_circuit_breaker",
            latency_seconds=0.0,
        )
