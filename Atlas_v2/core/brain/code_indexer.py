"""
AXIS RAG Memory — Code Indexer
Scans project files, splits them into semantic chunks, and indexes into the vector store.
"""

import os
import hashlib
import json
import time
from core.logger import logger



class CodeIndexer:
    """
    Indexes project source code, documentation, and configuration
    into the AXIS vector store for RAG retrieval.
    """

    # File extensions to index
    INDEXABLE_EXTENSIONS = {
        ".py": "python",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".txt": "text",
    }

    SKIP_DIRS = {
        "__pycache__", ".git", ".github", "venv", ".venv",
        "node_modules", ".pytest_cache", ".ruff_cache",
        "axis_ai.egg-info", "generated_images", "vector_db",
        "_legacy", ".tmp", "logs", "agent_skills_old"
    }

    # Max chunk size in characters (~500 tokens)
    MAX_CHUNK_SIZE = 2000
    # Overlap between chunks
    CHUNK_OVERLAP = 200

    def __init__(self, vector_store, project_root: str = None):
        self.vector_store = vector_store

        if project_root is None:
            project_root = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "..", "..", ".."
            ))
        self.project_root = project_root

        # File hash cache to avoid re-indexing unchanged files
        self.hash_cache_file = os.path.join(
            project_root, "memories", "index_hashes.json"
        )
        self.hash_cache = self._load_hash_cache()

    def _load_hash_cache(self) -> dict:
        """Loads the file hash cache from disk."""
        if os.path.exists(self.hash_cache_file):
            try:
                with open(self.hash_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_hash_cache(self):
        """Saves the file hash cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.hash_cache_file), exist_ok=True)
            with open(self.hash_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.hash_cache, f, indent=2)
        except Exception as e:
            logger.warning("rag.hash_cache_save_error", error=str(e))

    @staticmethod
    def _file_hash(filepath: str) -> str:
        """Computes SHA256 hash of a file's content."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _should_index(self, filepath: str) -> bool:
        """Checks if a file needs (re-)indexing based on content hash."""
        current_hash = self._file_hash(filepath)
        cached_hash = self.hash_cache.get(filepath)

        if cached_hash == current_hash:
            return False  # File unchanged

        self.hash_cache[filepath] = current_hash
        return True

    @staticmethod
    def _detect_python_object(line: str, context_class: str = None) -> tuple:
        """
        Detects the object type and name from a Python boundary line.
        Returns (object_type, object_name).
        """
        stripped = line.strip()
        if stripped.startswith("class "):
            name = stripped.split("class ")[1].split("(")[0].split(":")[0].strip()
            return "class", name
        elif stripped.startswith("async def "):
            name = stripped.split("async def ")[1].split("(")[0].strip()
            if context_class:
                name = f"{context_class}.{name}"
            return "async_function", name
        elif stripped.startswith("def "):
            name = stripped.split("def ")[1].split("(")[0].strip()
            if context_class:
                name = f"{context_class}.{name}"
            return "function", name
        return "module", ""

    def _split_python_file(self, content: str, filepath: str) -> list[dict]:
        """
        Splits a Python file into semantic chunks by class/function boundaries.
        Each chunk carries rich metadata: object_type, object_name, start/end line.
        Falls back to line-based chunking for files without clear boundaries.
        """
        chunks = []
        lines = content.split("\n")

        # Find class and function boundaries with their types
        boundaries = []  # list of (line_index, object_type, object_name)
        current_class = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class "):
                obj_type, obj_name = self._detect_python_object(line)
                current_class = obj_name
                boundaries.append((i, obj_type, obj_name))
            elif stripped.startswith("def ") or stripped.startswith("async def "):
                # Check indentation — if indented, it belongs to current_class
                indent = len(line) - len(line.lstrip())
                ctx = current_class if indent > 0 else None
                obj_type, obj_name = self._detect_python_object(line, ctx)
                boundaries.append((i, obj_type, obj_name))

        if not boundaries:
            # No functions/classes — use line-based chunking
            return self._split_by_lines(content, filepath)

        # Add start marker for module-level code before first boundary
        if boundaries[0][0] != 0:
            boundaries.insert(0, (0, "module", "imports"))

        for idx in range(len(boundaries)):
            start, obj_type, obj_name = boundaries[idx]
            end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)

            chunk_text = "\n".join(lines[start:end]).strip()
            if not chunk_text or len(chunk_text) < 20:
                continue

            base_meta = {
                "type": "python",
                "object_type": obj_type,
                "object_name": obj_name,
                "start_line": start + 1,
                "end_line": end,
            }

            # Source header with rich info
            header = f"# Source: {filepath}:{start+1}-{end} | {obj_type} {obj_name}"

            # If chunk is too large, sub-split it
            if len(chunk_text) > self.MAX_CHUNK_SIZE:
                sub_chunks = self._split_by_size(chunk_text)
                for j, sc in enumerate(sub_chunks):
                    meta = {**base_meta, "sub_chunk": j}
                    chunks.append({
                        "text": f"{header} (part {j+1})\n{sc}",
                        "source": filepath,
                        "chunk_index": len(chunks),
                        "metadata": meta,
                    })
            else:
                chunks.append({
                    "text": f"{header}\n{chunk_text}",
                    "source": filepath,
                    "chunk_index": len(chunks),
                    "metadata": base_meta,
                })

        return chunks

    def _split_by_lines(self, content: str, filepath: str) -> list[dict]:
        """Splits content into chunks by line count."""
        lines = content.split("\n")
        chunks = []
        ext = os.path.splitext(filepath)[1].lower()
        file_type = self.INDEXABLE_EXTENSIONS.get(ext, "text")
        # ~50 lines per chunk
        chunk_size = 50
        for i in range(0, len(lines), chunk_size - 5):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = "\n".join(chunk_lines).strip()
            if not chunk_text:
                continue
            chunks.append({
                "text": f"# Source: {filepath}:{i+1}-{i+len(chunk_lines)}\n{chunk_text}",
                "source": filepath,
                "chunk_index": len(chunks),
                "metadata": {
                    "type": file_type,
                    "object_type": "fragment",
                    "object_name": "",
                    "start_line": i + 1,
                    "end_line": i + len(chunk_lines),
                }
            })
        return chunks

    def _split_by_size(self, text: str) -> list[str]:
        """Splits text into chunks of MAX_CHUNK_SIZE with CHUNK_OVERLAP overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.MAX_CHUNK_SIZE
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.CHUNK_OVERLAP
        return chunks

    def _split_markdown_file(self, content: str, filepath: str) -> list[dict]:
        """Splits a Markdown file by headings (## sections)."""
        chunks = []
        sections = []
        current_section = []
        current_heading = ""

        for line in content.split("\n"):
            if line.startswith("## ") or line.startswith("# "):
                if current_section:
                    sections.append((current_heading, "\n".join(current_section)))
                current_heading = line.strip("# ").strip()
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append((current_heading, "\n".join(current_section)))

        for sec_idx, (heading, section_text) in enumerate(sections):
            section_text = section_text.strip()
            if len(section_text) < 10:
                continue

            # Detect section line number for traceability
            sec_start = 1
            for li, line in enumerate(content.split("\n"), 1):
                if heading and heading in line:
                    sec_start = li
                    break

            base_meta = {
                "type": "markdown",
                "object_type": "section",
                "object_name": heading or f"section_{sec_idx}",
                "section": heading,
                "start_line": sec_start,
            }

            if len(section_text) > self.MAX_CHUNK_SIZE:
                sub_chunks = self._split_by_size(section_text)
                for j, sc in enumerate(sub_chunks):
                    meta = {**base_meta, "sub_chunk": j}
                    chunks.append({
                        "text": f"# Source: {filepath}:{sec_start} | Section: {heading}\n{sc}",
                        "source": filepath,
                        "chunk_index": len(chunks),
                        "metadata": meta,
                    })
            else:
                chunks.append({
                    "text": f"# Source: {filepath}:{sec_start} | Section: {heading}\n{section_text}",
                    "source": filepath,
                    "chunk_index": len(chunks),
                    "metadata": base_meta,
                })

        return chunks if chunks else self._split_by_lines(content, filepath)

    def _split_file(self, content: str, filepath: str, ext: str) -> list[dict]:
        """Routes file content to the appropriate splitter."""
        if ext == ".py":
            return self._split_python_file(content, filepath)
        elif ext in (".md",):
            return self._split_markdown_file(content, filepath)
        else:
            return self._split_by_lines(content, filepath)

    def index_file(self, filepath: str, force: bool = False) -> int:
        """
        Indexes a single file into the vector store.
        Returns the number of chunks indexed.
        """
        if not self.vector_store or not self.vector_store.is_available:
            return 0

        ext = os.path.splitext(filepath)[1].lower()
        if ext not in self.INDEXABLE_EXTENSIONS:
            return 0

        if not force and not self._should_index(filepath):
            return 0

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.warning("rag.read_error", file=filepath, error=str(e))
            return 0

        if not content.strip():
            return 0

        # Remove old chunks for this file
        self.vector_store.delete_by_source(filepath)

        # Split and index
        chunks = self._split_file(content, filepath, ext)
        if chunks:
            self.vector_store.upsert_documents(chunks)

        return len(chunks)

    def index_directory(self, directory: str = None, force: bool = False) -> dict:
        """
        Recursively indexes all eligible files in a directory.
        Returns stats: {files_scanned, files_indexed, chunks_total}.
        """
        if directory is None:
            directory = self.project_root

        stats = {"files_scanned": 0, "files_indexed": 0, "chunks_total": 0}

        for root, dirs, files in os.walk(directory):
            # Filter out skipped directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                if ext not in self.INDEXABLE_EXTENSIONS:
                    continue

                stats["files_scanned"] += 1

                n_chunks = self.index_file(filepath, force=force)
                if n_chunks > 0:
                    stats["files_indexed"] += 1
                    stats["chunks_total"] += n_chunks
                    # --- THROTTLE INDEXING (v3.2.4 "Cool Down") ---
                    time.sleep(0.1) 

        self._save_hash_cache()

        logger.info("rag.index_complete",
                     scanned=stats["files_scanned"],
                     indexed=stats["files_indexed"],
                     chunks=stats["chunks_total"])
        return stats

    def cleanup_stale_sources(self) -> int:
        """
        Removes vector store entries and hash cache entries for files
        that no longer exist on disk. Prevents hallucinating deleted code.

        Returns:
            Number of stale sources cleaned up.
        """
        if not self.vector_store or not self.vector_store.is_available:
            return 0

        stale_paths = [
            path for path in list(self.hash_cache.keys())
            if not os.path.exists(path)
        ]

        for path in stale_paths:
            self.vector_store.delete_by_source(path)
            del self.hash_cache[path]
            logger.info("rag.stale_source_removed", path=path)

        if stale_paths:
            self._save_hash_cache()
            logger.info("rag.stale_cleanup_done", removed=len(stale_paths))

        return len(stale_paths)

    def index_project(self, force: bool = False) -> dict:
        """
        Full project indexing — scans key directories.
        Also cleans up stale entries for deleted files.
        """
        total_stats = {
            "files_scanned": 0, "files_indexed": 0,
            "chunks_total": 0, "stale_removed": 0,
        }

        # --- Phase 0: Remove stale sources for deleted files ---
        total_stats["stale_removed"] = self.cleanup_stale_sources()

        # --- Phase 1: Index key directories ---
        scan_dirs = [
            os.path.join(self.project_root, "Atlas_v2", "core"),
            os.path.join(self.project_root, "Atlas_v2", "agent_skills"),
            os.path.join(self.project_root, "memories"),
        ]

        # Also index root-level docs (dynamic)
        root_docs = [
            os.path.join(self.project_root, "README.md"),
            os.path.join(self.project_root, "PROJECT_PLAN.md"), # In case it was recreated
        ]

        for scan_dir in scan_dirs:
            if os.path.exists(scan_dir) and os.path.isdir(scan_dir):
                stats = self.index_directory(scan_dir, force=force)
                for k in ["files_scanned", "files_indexed", "chunks_total"]:
                    total_stats[k] += stats[k]
        
        for doc in root_docs:
            if os.path.exists(doc):
                n = self.index_file(doc, force=force)
                if n > 0:
                    total_stats["files_indexed"] += 1
                    total_stats["chunks_total"] += n

        self._save_hash_cache()

        logger.info("rag.project_index_complete",
                     total_scanned=total_stats["files_scanned"],
                     total_indexed=total_stats["files_indexed"],
                     total_chunks=total_stats["chunks_total"],
                     stale_removed=total_stats["stale_removed"])
        return total_stats
