"""
AXIS RAG Memory — Retrieval-Augmented Generation Retriever
Performs semantic search and formats results for Brain prompt injection.
"""

from core.logger import logger
from core.brain.vector_store import VectorStore
from core.brain.code_indexer import CodeIndexer


class RAGRetriever:
    """
    Query-time RAG retriever for AXIS.
    Retrieves relevant context from the vector store and formats it
    for injection into the LLM system prompt or conversation.
    """

    def __init__(self, vector_store: VectorStore = None, project_root: str = None):
        if vector_store is None:
            self.vector_store = VectorStore()
        else:
            self.vector_store = vector_store

        self.indexer = CodeIndexer(self.vector_store, project_root=project_root)
        self._indexed = False

    @property
    def is_available(self) -> bool:
        return self.vector_store.is_available

    def ensure_indexed(self, force: bool = False):
        """
        Ensures the project is indexed. Only runs once per session
        unless force=True.
        """
        if not self.is_available:
            logger.warning("rag.skip_indexing", reason="Vector store not available")
            return

        if self._indexed and not force:
            return

        import threading
        def _bg_index():
            try:
                stats = self.indexer.index_project(force=force)
                logger.info("rag.bg_index_done",
                            indexed=stats["files_indexed"],
                            chunks=stats["chunks_total"])
                self._indexed = True
            except Exception as e:
                logger.error("rag.bg_index_error", error=str(e))

        # Run indexing in background to not block boot
        thread = threading.Thread(target=_bg_index, daemon=True)
        thread.start()
        logger.info("rag.indexing_started", mode="background")

    def retrieve(self, query: str, n_results: int = 5,
                 doc_type: str = None) -> list[dict]:
        """
        Retrieves relevant document chunks for a given query.

        Args:
            query: User's question or search query
            n_results: Maximum number of results to return
            doc_type: Optional filter by document type ('python', 'markdown', etc.)

        Returns:
            List of dicts with: text, source, score, metadata
        """
        if not self.is_available:
            return []

        where_filter = None
        if doc_type:
            where_filter = {"type": doc_type}

        results = self.vector_store.query(
            query_text=query,
            n_results=n_results,
            where_filter=where_filter
        )

        if results:
            logger.debug("rag.retrieved",
                         query_preview=query[:80],
                         results=len(results),
                         top_score=f"{results[0]['score']:.3f}" if results else "N/A")

        return results

    def get_context_block(self, query: str, n_results: int = 5,
                          min_score: float = 0.45) -> str:
        """
        Retrieves relevant context and formats it as a prompt block.

        Args:
            query: The user's question
            n_results: Max number of chunks to include
            min_score: Minimum similarity score (0.0-1.0) to include a result.
                       Default 0.45 filters out tangentially related chunks.

        Returns:
            Formatted string block with precise source citations (file:line, object info).
        """
        results = self.retrieve(query, n_results=n_results)

        if not results:
            return ""

        # Filter by minimum score — prevents context pollution
        relevant = [r for r in results if r.get("score", 0) >= min_score]

        filtered_count = len(results) - len(relevant)
        if filtered_count > 0:
            logger.debug("rag.filtered_low_score",
                         filtered=filtered_count,
                         threshold=min_score,
                         lowest_kept=f"{relevant[-1]['score']:.3f}" if relevant else "N/A")

        if not relevant:
            return ""

        block = "\n### \U0001f9e0 RAG CONTEXT (Retrieved from project knowledge base):\n"
        block += f"Query: \"{query[:100]}\"\n"
        block += "---\n"

        for i, result in enumerate(relevant, 1):
            source = result.get("source", "unknown")
            meta = result.get("metadata", {})
            score = result.get("score", 0)
            text = result.get("text", "")

            # Make source path relative for readability
            if "Atlas" in source:
                source = source.split("Atlas")[-1].lstrip("/\\")

            # Build precise location string
            start_line = meta.get("start_line", "")
            end_line = meta.get("end_line", "")
            obj_type = meta.get("object_type", "")
            obj_name = meta.get("object_name", "")

            location = source
            if start_line:
                location += f":{start_line}"
                if end_line and end_line != start_line:
                    location += f"-{end_line}"

            label = location
            if obj_type and obj_name:
                label += f" ({obj_type} {obj_name})"
            elif obj_type:
                label += f" ({obj_type})"

            # Truncate very long chunks
            if len(text) > 800:
                text = text[:800] + "\n... [truncated]"

            block += f"\n**[{i}] {label}** (relevance: {score:.0%})\n"
            block += f"```\n{text}\n```\n"

        block += "---\n"
        block += ("Use the above context to inform your response. "
                  "Cite sources with file:line when referencing specific code or documentation.\n")

        return block

    def index_single_file(self, filepath: str) -> int:
        """
        Indexes or re-indexes a single file (e.g., after a write_file tool call).
        Returns number of chunks indexed.
        """
        if not self.is_available:
            return 0
        return self.indexer.index_file(filepath, force=True)

    def get_stats(self) -> dict:
        """Returns combined stats from vector store and indexer."""
        store_stats = self.vector_store.get_stats() if self.vector_store else {}
        return {
            "vector_store": store_stats,
            "indexed": self._indexed,
        }
