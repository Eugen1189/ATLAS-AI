import re
from core.brain.memory import memory_manager

from core.skills.wrapper import agent_tool

@agent_tool
def save_to_memory(topic: str, fact: str, **kwargs) -> str:
    """Saves a fact to semantic storage. Privacy shield active."""
    secret_patterns = [r"sk-[a-zA-Z0-9]{20,}", r"AIza[a-zA-Z0-9_-]{30,}", r"ghp_[A-Za-z0-9]{30,}"]
    if any(re.search(p, fact) for p in secret_patterns) or "key" in topic.lower():
        return "❌ [SECURITY BLOCK]: Sensitive data detected."
    try:
        memory_manager.store_fact(key=topic, value=fact)
        return f"✅ [REMEMBERED]: {topic}"
    except Exception as e: return f"Error: {e}"

@agent_tool
def search_memory(query: str, **kwargs) -> str:
    """Searches RAG memory for relevant context based on query."""
    try:
        context = memory_manager.get_context_block(query, n_results=5)
        return context if "RELEVANT" in context else "🔍 [NOT FOUND] in active memory."
    except Exception as e: return f"Err: {e}"

@agent_tool
def get_memory_stats(**kwargs) -> str:
    """Returns total number of stored facts and knowledge docs."""
    try:
        count = len(memory_manager.get_recent_facts(limit=1000))
        return f"### Memory State:\nTotal facts: {count}\nNamespace: {memory_manager.namespace}"
    except Exception: return "Stats unavailable."

@agent_tool
def forget_topic(topic: str, **kwargs) -> str:
    """Purges a specific fact mapping from memory."""
    try:
        memory_manager.store_fact(topic, "DELETED")
        return f"🗑️ [PURGED]: '{topic}'"
    except Exception as e: return f"Err: {e}"

EXPORTED_TOOLS = [save_to_memory, search_memory, get_memory_stats, forget_topic]

