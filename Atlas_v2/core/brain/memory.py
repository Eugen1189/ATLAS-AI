import os
import json
import requests
import threading
from datetime import datetime
from core.logger import logger

class MemoryManager:
    """
    Manages the long-term project context and facts for AXIS.
    Prevents 'Amnesia' by storing and retrieving key project metadata.
    Now includes ReflectionEngine for episodic memory generation.
    """
    def __init__(self, namespace="default"):
        # Path: Atlas_v2/../memories/facts.json
        self.memories_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "memories"
        ))
        os.makedirs(self.memories_dir, exist_ok=True)
        self.namespace = namespace
        
        # Namespaced Facts
        self.facts_file = os.path.join(self.memories_dir, f"facts_{namespace}.json")
        
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.llm_model = os.getenv("AXIS_MODEL", "qwen2.5-coder:7b") # For reflection
        
        self.facts = self._load_facts()

        # --- RAG Memory (Namespaced) ---
        try:
            from core.brain.vector_store import VectorStore
            from core.brain.rag_retriever import RAGRetriever
            from core.brain.code_indexer import CodeIndexer
            self.vector_store = VectorStore(namespace=namespace)
            self.rag = RAGRetriever(vector_store=self.vector_store)
            self.indexer = CodeIndexer(vector_store=self.vector_store)
            logger.info("memory.rag_initialized",
                        namespace=namespace,
                        available=self.rag.is_available)
        except Exception as e:
            logger.warning("memory.rag_init_failed", error=str(e))
            self.vector_store = None
            self.rag = None

    def switch_namespace(self, new_namespace: str):
        """Switches the memory context to a different project/namespace."""
        if new_namespace == self.namespace:
            return
        logger.info("memory.switching_namespace", old=self.namespace, new=new_namespace)
        self.__init__(namespace=new_namespace)

    def _load_facts(self) -> dict:
        if not os.path.exists(self.facts_file):
            return {}
        try:
            with open(self.facts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("memory.load_error", error=str(e))
            return {}

    def store_fact(self, key: str, value: str):

        """Stores a fact in the long-term context (JSON + Vector Store)."""
        # 1. Update JSON (Structured Metadata)
        self.facts[key] = {
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_facts()
        logger.info("memory.fact_stored", key=key)
        
        # 2. Update Vector Store (Semantic Retrieval)
        if self.rag and self.rag.is_available:
            try:
                self.vector_store.upsert_documents([{
                    "text": f"[FACT] {key}: {value}",
                    "source": f"fact::{key}",
                    "chunk_index": 0,
                    "metadata": {"type": "fact", "key": key}
                }])
            except Exception as e:
                logger.warning("memory.rag_fact_store_error", error=str(e))

    def reindex_file(self, filepath: str):
        """Immediately re-indexes a file to keep RAG context fresh (v2.8.6)."""
        if hasattr(self, 'indexer') and self.indexer:
            try:
                # Resolve to absolute path to match indexer's expectations
                abs_path = os.path.abspath(filepath)
                count = self.indexer.index_file(abs_path, force=True)
                if count > 0:
                    logger.info("memory.auto_indexing_success", path=filepath, chunks=count)
            except Exception as e:
                logger.warning("memory.auto_indexing_failed", path=filepath, error=str(e))

    def _save_facts(self):
        try:
            with open(self.facts_file, "w", encoding="utf-8") as f:
                json.dump(self.facts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("memory.save_error", error=str(e))

    def get_context_for_prompt(self, limit: int = 10, query: str = None) -> str:
        """
        Generates a text block of known facts using RAG.
        Falls back to recent facts if RAG is unavailable.
        """
        if not query and not self.facts:
            return ""

        blocks = []
        
        # 1. Primary: Semantic Search via RAG
        if self.rag and self.rag.is_available and query:
            rag_block = self.rag.get_context_block(query, n_results=limit)
            if rag_block:
                blocks.append(f"### 🧠 SEMANTIC MEMORY (RAG):\n{rag_block}")

        # 2. Fallback/Supplement: Recent Human-Readable Facts
        recent_facts = self.get_recent_facts(limit=5)
        if recent_facts:
            fact_block = "### 🧠 CORE FACTS & PREFERENCES:\n"
            for key, data in recent_facts:
                fact_block += f"- [{key}]: {data['value']}\n"
            blocks.append(fact_block)
        
        return "\n".join(blocks)

    def get_context_block(self, query: str, n_results: int = 5) -> str:
        """Alias for skill-level search_memory tool."""
        return self.get_context_for_prompt(limit=n_results, query=query)

    def get_recent_facts(self, limit: int = 5) -> list:
        """Returns a list of tuples (key, data) sorted by timestamp."""
        return sorted(self.facts.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)[:limit]

    # ==========================================
    # --- NEW: REFLECTION ENGINE (v2.8.0) ---
    # ==========================================

    def get_morning_briefing(self) -> str:
        """Returns the most recent events to inject into the first prompt of a session."""
        if not self.facts:
            return ""
        
        # Get 3 most recent facts
        recent_facts = sorted(self.facts.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True)[:3]
        
        briefing = "### 🌅 EPISODIC RECALL (Recent Events):\n"
        briefing += "Before starting, here is what you did recently:\n"
        for key, data in recent_facts:
            briefing += f"- {data['value']} ({data['timestamp']})\n"
        
        return briefing

    # ==========================================
    # --- NEW: SEMANTIC CACHING (RAG 2.0) ---
    # ==========================================

    def get_semantic_cache(self, query: str, threshold: float = 0.95) -> dict | None:
        """
        Checks if a similar terminal command was executed before (v2.8.9).
        If similarity > threshold, returns the cached tool/plan data.
        """
        if not self.rag or not self.vector_store:
            return None
            
        matches = self.vector_store.query(query, n_results=1, collections=["cache"])
        if matches and matches[0]["score"] >= threshold:
            try:
                data = json.loads(matches[0]["metadata"]["action_data"])
                logger.info("memory.cache_hit", query=query[:30], score=matches[0]["score"])
                return data
            except Exception as e:
                logger.error("memory.cache_parse_error", error=str(e))
        return None

    def store_semantic_cache(self, query: str, action_data: dict | list):
        """Stores a successful Command -> Plan/Tool mapping in ChromaDB."""
        if not self.vector_store:
            return
            
        try:
            # We use the hash of the query as the source for deterministic updates
            import hashlib
            query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
            
            self.vector_store.upsert_documents([{
                "text": query.lower().strip(),
                "source": f"cache::{query_hash}",
                "metadata": {
                    "action_data": json.dumps(action_data),
                    "type": "cache_entry"
                }
            }], category="cache")
            logger.debug("memory.cache_stored", query=query[:30])
        except Exception as e:
            logger.warning("memory.cache_store_failed", error=str(e))

    def reflect_on_session(self, session_history: list):
        """
        Background process that analyzes a conversation transcript and extracts
        facts, preferences, and events automatically.
        """
        if len(session_history) < 4:
            return  # Too short to reflect

        def _reflection_worker():
            logger.info("memory.reflection_started", reason="Analyzing session transcript")
            
            # Format history (truncate large tool outputs)
            transcript = ""
            for msg in session_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if len(content) > 1000:
                    content = content[:300] + "...[truncated tool output]"
                transcript += f"[{role.upper()}]: {content}\n"
            prompt = f"""
            You are the Memory Synthesizer for AXIS.
            Analyze the following conversation transcript between the COMMANDER (User) and AXIS (Assistant).
            Your task is to extract user preferences, rules, future plans, and technical facts.
            CRITICAL: Pay special attention to direct commands like "запам'ятай" (remember), "відтепер" (from now on), or any rules about how AXIS should behave.

            Format your output EXACTLY as a JSON list of objects. Example output:
            [
                {{"key": "preference_communication", "value": "Commander hates 'Verbal Confirmation' and prefers short, dry answers"}},
                {{"key": "persona_style", "value": "Commander wants AXIS to talk like a strict sergeant"}},
                {{"key": "plan_migration", "value": "Migrating project to Python 3.12 next week"}}
            ]
            
            If absolutely nothing of value was discussed, return [].
            DO NOT output any conversational text. ONLY valid JSON.

            Transcript to analyze:
            {transcript}
            """

            try:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        # "format": "json" # Можна тимчасово вимкнути, іноді воно змушує Qwen видавати Object замість List
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result_text = response.json().get("response", "[]")
                    
                    # --- БРОНЬОВАНИЙ ПАРСЕР (v2.8.1) ---
                    # Шукаємо все, що знаходиться між [ та ] включно
                    import re
                    match = re.search(r'\[.*\]', result_text, re.DOTALL)
                    
                    if match:
                        clean_json = match.group(0)
                        extracted_memories = json.loads(clean_json)
                        
                        if isinstance(extracted_memories, list):
                            for mem in extracted_memories:
                                key = mem.get("key")
                                val = mem.get("value")
                                if key and val:
                                    self.store_fact(f"auto_{key}", val)

                            
                            logger.info("memory.reflection_complete", extracted_count=len(extracted_memories))
                        else:
                            logger.warning("memory.reflection_parsing_failed", reason="Parsed JSON is not a list")
                            logger.debug("memory.reflection_raw_output", text=clean_json)
                    else:
                        logger.warning("memory.reflection_parsing_failed", reason="No JSON array brackets found in output")
                        logger.debug("memory.reflection_raw_output", text=result_text)

            except Exception as e:
                logger.error("memory.reflection_error", error=str(e))

        # Run reflection in background to not block the user
        threading.Thread(target=_reflection_worker).start()

# Global instance for core systems
memory_manager = MemoryManager()
