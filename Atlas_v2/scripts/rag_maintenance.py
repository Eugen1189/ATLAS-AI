"""
AXIS RAG Maintenance Tool (v2.7)
Performs deep cleaning of the vector database.
- Wipes 'session' collection (recent logs/errors).
- Forces re-indexing of the 'knowledge' collection (clean source code).
- Excludes legacy/tmp folders.
"""
import os
import sys
from pathlib import Path

# Fix paths for standalone execution
current_script = os.path.abspath(__file__)
atlas_v2_dir = os.path.dirname(os.path.dirname(current_script))
if atlas_v2_dir not in sys.path:
    sys.path.insert(0, atlas_v2_dir)

from core.logger import logger
from core.brain.vector_store import VectorStore
from core.brain.rag_retriever import RAGRetriever

def perform_maintenance(namespace="default"):
    print(f"Starting AXIS RAG Maintenance (Namespace: {namespace})...")
    
    try:
        store = VectorStore(namespace=namespace)
        if not store.is_available:
            print("Vector store not available.")
            return

        # 1. Purge Sessions
        print("Purging session collection (Recent Logs/Errors)...")
        store.purge_session()
        
        # 2. Reset Knowledge
        print("Re-indexing knowledge collection (Clean Source)...")
        store.client.delete_collection("axis_knowledge")
        store.knowledge = store.client.create_collection("axis_knowledge", metadata={"hnsw:space": "cosine"})
        
        # 3. Trigger full re-index
        current_script_path = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_script_path, "..", ".."))
        
        rag = RAGRetriever(vector_store=store, project_root=project_root)
        
        print(f"Detected Project Root: {project_root}")
        print("Started background indexing. This may take a minute...")
        
        # Sync-index important files first
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(store, project_root=project_root)
        
        # Exclude legacy folders manually during this maintenance run
        original_skip = set(indexer.SKIP_DIRS)
        indexer.SKIP_DIRS = list(original_skip | {"_legacy", "venv", ".git", "node_modules", "agent_skills_old"})
        
        stats = indexer.index_project(force=True)
        print(f"Maintenance Complete!")
        print(f"Stats: {stats['files_indexed']} files indexed, {stats['chunks_total']} chunks created.")
        
    except Exception as e:
        print(f"❌ Maintenance Failed: {e}")

if __name__ == "__main__":
    ns = sys.argv[1] if len(sys.argv) > 1 else "default"
    perform_maintenance(ns)
