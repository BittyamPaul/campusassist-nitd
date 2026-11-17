"""
CampusAssist: Service Layer Package.
Exports knowledge repository, classifier, retrieval, LLM, and chat pipeline services.
"""

from app.services.chat_service import ChatPipelineService, get_chat_pipeline

__all__ = [
    "ChatPipelineService",
    "get_chat_pipeline",
]
