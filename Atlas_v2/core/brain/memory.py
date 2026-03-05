import os
import json
import requests
import numpy as np
from datetime import datetime
from core.logger import logger

class MemoryManager:
    """
    Manages the long-term project context and facts for AXIS.
    Prevents 'Amnesia' by storing and retrieving key project metadata.
    """
    def __init__(self):
        # Path: Atlas_v2/../memories/facts.json
        self.memories_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "memories"
        ))
        os.makedirs(self.memories_dir, exist_ok=True)
        self.facts_file = os.path.join(self.memories_dir, "facts.json")
        self.embeddings_file = os.path.join(self.memories_dir, "embeddings.json")
        
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        
        self.facts = self._load_facts()
        self.embeddings = self._load_embeddings()

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
        """
        self.facts[key] = {
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self._save_facts()
        logger.info("memory.fact_stored", key=key)
        
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
        If query is provided, uses semantic search. Otherwise uses recent facts.
        """
        if not self.facts:
            return ""

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
        
        block = "\n### RELEVANT PROJECT MEMORIES:\n"
        for key in selected_keys:
            data = self.facts[key]
            block += f"- [{key}]: {data['value']} ({data['timestamp']})\n"
        
        return block

# Global instance for core systems
memory_manager = MemoryManager()
