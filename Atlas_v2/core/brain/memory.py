import os
import json
import requests
import numpy as np
from datetime import datetime
from core.logger import logger
from core.brain.vector_store import VectorStore
from core.brain.rag_retriever import RAGRetriever

class MemoryManager:
    """
    Manages the long-term project context and facts for AXIS.
    Prevents 'Amnesia' by storing and retrieving key project metadata.
    """
    def __init__(self, namespace="default"):
        # Path: Atlas_v2/../memories/facts.json
        self.memories_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "memories"
        ))
        os.makedirs(self.memories_dir, exist_ok=True)
        self.namespace = namespace
        
        # Namespaced Facts and Embeddings
        self.facts_file = os.path.join(self.memories_dir, f"facts_{namespace}.json")
        self.embeddings_file = os.path.join(self.memories_dir, f"embeddings_{namespace}.json")
        
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        
        self.facts = self._load_facts()
        self.embeddings = self._load_embeddings()

        # --- RAG Memory (Namespaced) ---
        try:
            from core.brain.vector_store import VectorStore
            from core.brain.rag_retriever import RAGRetriever
            self.vector_store = VectorStore(namespace=namespace)
            self.rag = RAGRetriever(vector_store=self.vector_store)
            logger.info("memory.rag_initialized",
                        namespace=namespace,
                        available=self.rag.is_available)
        except Exception as e:
            logger.warning("memory.rag_init_failed", error=str(e))
            self.vector_store = None
            self.rag = None

    def switch_namespace(self, new_namespace: str):
        """Switches the memory context to a different project/namespace."""
        if new_namespace == self.namespace: return
        logger.info("memory.switching_namespace", old=self.namespace, new=new_namespace)
        self.__init__(namespace=new_namespace)

    def _load_facts(self) -> dict:
        """Loads facts from JSON file."""
        if not os.path.exists(self.facts_file):
            return {}
        try:
            with open(self.facts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("memory.load_error", error=str(e))
            return {}

    def _load_embeddings(self) -> dict:
        """Loads embeddings from JSON file."""
        if not os.path.exists(self.embeddings_file):
            return {}
        try:
            with open(self.embeddings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_embedding(self, text: str) -> list:
        """Gets embedding from Ollama."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get("embedding", [])
        except Exception as e:
            logger.warning("memory.embedding_failed", error=str(e))
        return []

    def store_fact(self, key: str, value: str, semantic: bool = True):
        """
        Stores a fact in the long-term context.
        Dual-writes to JSON facts file and RAG vector store.
        """
        self.facts[key] = {
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self._save_facts()
        logger.info("memory.fact_stored", key=key)
        
        # --- RAG: Also store in vector DB ---
        if self.rag and self.rag.is_available:
            try:
                self.vector_store.upsert_documents([{
                    "text": f"[FACT] {key}: {value}",
                    "source": f"fact::{key}",
                    "chunk_index": 0,
                    "metadata": {
                        "type": "fact",
                        "key": key,
                    }
                }])
            except Exception as e:
                logger.warning("memory.rag_fact_store_error", error=str(e))

        if semantic:
            import threading
            def _bg_embed():
                embedding = self._get_embedding(f"{key}: {value}")
                if embedding:
                    self.embeddings[key] = embedding
                    self._save_embeddings()
            
            threading.Thread(target=_bg_embed, daemon=True).start()

    def _save_facts(self):
        """Saves facts to JSON file."""
        try:
            with open(self.facts_file, "w", encoding="utf-8") as f:
                json.dump(self.facts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("memory.save_error", error=str(e))

    def _save_embeddings(self):
        """Saves embeddings to JSON file."""
        try:
            with open(self.embeddings_file, "w", encoding="utf-8") as f:
                json.dump(self.embeddings, f)
        except Exception as e:
            logger.error("memory.save_embeddings_error", error=str(e))

    def semantic_search(self, query: str, limit: int = 5) -> list:
        """Performs semantic search using vector similarity."""
        query_emb = self._get_embedding(query)
        if not query_emb or not self.embeddings:
            return []

        results = []
        q_vec = np.array(query_emb)
        
        for key, emb in self.embeddings.items():
            if key not in self.facts: continue
            
            e_vec = np.array(emb)
            # Cosine similarity
            similarity = np.dot(q_vec, e_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(e_vec))
            results.append((key, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_context_for_prompt(self, limit: int = 10, query: str = None) -> str:
        """
        Generates a text block of known facts for the system prompt.
        If query is provided, uses RAG retrieval first, then semantic search.
        Otherwise uses recent facts.
        """
        blocks = []

        # --- RAG Context (if query provided) ---
        if query and self.rag and self.rag.is_available:
            rag_block = self.rag.get_context_block(query, n_results=limit)
            if rag_block:
                blocks.append(rag_block)

        # --- Fact-based Context ---
        if self.facts:
            selected_keys = []
            if query:
                semantic_results = self.semantic_search(query, limit=limit)
                selected_keys = [res[0] for res in semantic_results]
            
            if not selected_keys:
                # Fallback to recent
                sorted_facts = sorted(
                    self.facts.items(), 
                    key=lambda x: x[1].get("timestamp", ""), 
                    reverse=True
                )[:limit]
                selected_keys = [k for k, v in sorted_facts]
            
            fact_block = "\n### RELEVANT PROJECT MEMORIES:\n"
            for key in selected_keys:
                data = self.facts[key]
                fact_block += f"- [{key}]: {data['value']} ({data['timestamp']})\n"
            blocks.append(fact_block)
        
        return "\n".join(blocks)

# Global instance for core systems
memory_manager = MemoryManager()
