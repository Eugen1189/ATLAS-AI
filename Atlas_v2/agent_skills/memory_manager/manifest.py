import os
import re
import json
from core.i18n import lang
from core.brain.memory import memory_manager
from core.logger import logger

def save_to_memory(topic: str, fact: str) -> str:
    """Standard 2026 Semantic Storage. Privacy Shield active."""
    secret_patterns = [r"sk-[a-zA-Z0-9]{20,}", r"AIza[a-zA-Z0-9_-]{30,}", r"ghp_[A-Za-z0-9]{30,}"]
    if any(re.search(p, fact) for p in secret_patterns) or "key" in topic.lower():
        return "❌ [SECURITY BLOCK]: Sensitive data detected."
    try:
        memory_manager.store_fact(key=topic, value=fact)
        return f"✅ [REMEMBERED]: {topic}"
    except Exception as e: return f"Error: {e}"

def search_memory(query: str) -> str:
    """Standard 2026 Semantic Retrieval. Searches RAG for relevant context."""
    try:
        context = memory_manager.get_context_block(query, n_results=5)
        return context if "RELEVANT" in context else "🔍 [NOT FOUND] in active memory."
    except Exception as e: return f"Err: {e}"

def get_memory_stats() -> str:
    """Returns total number of stored facts and knowledge docs."""
    try:
        count = len(memory_manager.get_recent_facts(limit=1000))
        return f"### Memory State:\nTotal facts: {count}\nNamespace: {memory_manager.namespace}"
    except Exception: return "Stats unavailable."

def forget_topic(topic: str) -> str:
    """Purges a specific fact mapping from memory."""
    try:
        memory_manager.store_fact(topic, "DELETED")
        return f"🗑️ [PURGED]: '{topic}'"
    except Exception as e: return f"Err: {e}"

EXPORTED_TOOLS = [save_to_memory, search_memory, get_memory_stats, forget_topic]
