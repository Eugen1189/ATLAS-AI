"""
AXIS RAG Memory — Vector Store (ChromaDB)
Manages the local vector database for semantic search across project knowledge.
"""

import os
import hashlib
from datetime import datetime
from core.logger import logger

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class VectorStore:
    """
    ChromaDB-based vector store for AXIS RAG memory.
    Supports Categorized Knowledge:
    - Knowledge: Long-term (code, docs)
    - Session: Short-term (recent logs, current context)
    """

    def __init__(self, persist_dir: str = None, namespace: str = "default"):
        if not CHROMADB_AVAILABLE:
            logger.warning("rag.chromadb_missing",
                           reason="chromadb package is not installed. RAG disabled.")
            self.client = None
            self.knowledge = None
            self.session = None
            return

        # Scoped Memory: create separate subdirectories per workspace/namespace
        if persist_dir is None:
            base_memories = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "memories"
            ))
            persist_dir = os.path.join(base_memories, "vector_db", namespace)

        os.makedirs(persist_dir, exist_ok=True)
        self.persist_dir = persist_dir

        try:
            self.client = chromadb.PersistentClient(path=persist_dir)
            
            # Category 1: Static Knowledge (Code)
            self.knowledge = self.client.get_or_create_collection(
                name="axis_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Category 2: Dynamic Sessions (Logs/Prompts)
            self.session = self.client.get_or_create_collection(
                name="axis_session",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("rag.vector_store_ready",
                        namespace=namespace,
                        knowledge_docs=self.knowledge.count(),
                        session_docs=self.session.count())
        except Exception as e:
            logger.error("rag.vector_store_init_error", error=str(e))
            self.client = None
            self.knowledge = None
            self.session = None

    def purge_session(self):
        """Wipes the session cache to prevent error-hallucinations."""
        try:
            if self.session:
                count = self.session.count()
                self.client.delete_collection("axis_session")
                self.session = self.client.create_collection("axis_session")
                logger.info("rag.session_purged", count=count)
        except Exception as e:
            logger.error("rag.purge_error", error=str(e))

    @property
    def is_available(self) -> bool:
        return self.knowledge is not None

    @staticmethod
    def _make_id(source: str, chunk_index: int = 0) -> str:
        """Generates a deterministic ID from source path + chunk index."""
        raw = f"{source}::chunk_{chunk_index}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def upsert_documents(self, documents: list[dict], category: str = "knowledge"):
        """
        Upserts a batch of documents into the vector store.
        category: 'knowledge' (long-term) or 'session' (short-term)
        """
        if not self.is_available:
            return

        target = self.knowledge if category == "knowledge" else self.session
        if not target: return

        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            doc_id = self._make_id(doc["source"], doc.get("chunk_index", 0))
            ids.append(doc_id)
            texts.append(doc["text"])

            meta = doc.get("metadata", {})
            meta["source"] = doc["source"]
            meta["chunk_index"] = doc.get("chunk_index", 0)
            meta["indexed_at"] = datetime.now().isoformat()
            metadatas.append(meta)

        try:
            target.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.debug("rag.upserted", count=len(ids), category=category)
        except Exception as e:
            logger.error("rag.upsert_error", error=str(e))

    def query(self, query_text: str, n_results: int = 5,
              where_filter: dict = None, collections: list = ["knowledge", "session"]) -> list[dict]:
        """
        Performs semantic search across specified collections.
        """
        if not self.is_available:
            return []

        all_matches = []
        for cat in collections:
            target = self.knowledge if cat == "knowledge" else self.session
            if not target: continue
            
            try:
                kwargs = {
                    "query_texts": [query_text],
                    "n_results": min(n_results, target.count() or 1)
                }
                if where_filter:
                    kwargs["where"] = where_filter

                results = target.query(**kwargs)

                if results and results.get("documents"):
                    for i, doc_text in enumerate(results["documents"][0]):
                        all_matches.append({
                            "text": doc_text,
                            "source": results["metadatas"][0][i].get("source", "unknown"),
                            "score": 1.0 - (results["distances"][0][i]
                                             if results.get("distances") else 0),
                            "metadata": results["metadatas"][0][i],
                            "category": cat
                        })
            except Exception as e:
                logger.error("rag.query_error", category=cat, error=str(e))
                
        # Sort combined results by score
        all_matches.sort(key=lambda x: x["score"], reverse=True)
        return all_matches[:n_results]

    def delete_by_source(self, source: str, category: str = "knowledge"):
        """Deletes all chunks belonging to a specific source file."""
        if not self.is_available:
            return
        target = self.knowledge if category == "knowledge" else self.session
        try:
            target.delete(where={"source": source})
            logger.debug("rag.deleted_source", source=source, category=category)
        except Exception as e:
            logger.error("rag.delete_error", error=str(e))

    def get_stats(self) -> dict:
        """Returns basic statistics about the vector store."""
        if not self.is_available:
            return {"status": "unavailable", "docs": 0}
        
        try:
            return {
                "status": "ready",
                "knowledge_docs": self.knowledge.count() if self.knowledge else 0,
                "session_docs": self.session.count() if self.session else 0,
                "persist_dir": self.persist_dir
            }
        except Exception as e:
            logger.error("rag.stats_error", error=str(e))
            return {"status": "error", "message": str(e)}
