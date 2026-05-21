"""
Vector Memory Manager - ChromaDB local persistent store for semantic search
"""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings


class VectorMemoryManager:
    """Manages local vector embeddings using ChromaDB."""

    def __init__(self, persist_dir: str = None):
        if persist_dir is None:
            persist_dir = str(Path(__file__).parent / "chroma_db")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)
        self._init_collections()

    def _init_collections(self):
        """Initialize ChromaDB collections."""
        try:
            self.repo_collection = self.client.get_or_create_collection(
                name="repository_files",
                metadata={"description": "Repository file contents and summaries"}
            )
            self.memory_collection = self.client.get_or_create_collection(
                name="project_memory",
                metadata={"description": "Persistent project memory and insights"}
            )
            self.conversation_collection = self.client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Chat conversation history"}
            )
            self.debug_collection = self.client.get_or_create_collection(
                name="debug_context",
                metadata={"description": "Debugging history and solutions"}
            )
        except Exception as e:
            print(f"Warning: ChromaDB collection init error: {e}")

    def _make_id(self, text: str, prefix: str = "") -> str:
        """Generate a stable ID from text."""
        return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()[:12]}"

    # ── Repository Embeddings ─────────────────────────────────────────────────

    def store_file(self, project_id: int, file_path: str, content: str, summary: str = ""):
        """Store a repository file in vector memory."""
        try:
            doc_id = self._make_id(f"{project_id}_{file_path}", "file")
            text = f"File: {file_path}\n\nSummary: {summary}\n\nContent:\n{content[:2000]}"
            self.repo_collection.upsert(
                documents=[text],
                metadatas=[{"project_id": str(project_id), "file_path": file_path, "summary": summary}],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Warning: Failed to store file vector: {e}")
            return None

    def search_repository(self, query: str, project_id: int, n_results: int = 5) -> List[Dict]:
        """Search repository files semantically."""
        try:
            results = self.repo_collection.query(
                query_texts=[query],
                n_results=min(n_results, max(1, self.repo_collection.count())),
                where={"project_id": str(project_id)} if self.repo_collection.count() > 0 else None
            )
            if not results["documents"] or not results["documents"][0]:
                return []
            docs = []
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                docs.append({"content": doc, "metadata": meta, "distance": results["distances"][0][i] if results.get("distances") else 0})
            return docs
        except Exception as e:
            print(f"Warning: Repository search error: {e}")
            return []

    def get_project_file_count(self, project_id: int) -> int:
        """Count stored files for a project."""
        try:
            results = self.repo_collection.get(where={"project_id": str(project_id)})
            return len(results["ids"])
        except Exception:
            return 0

    def clear_project_files(self, project_id: int):
        """Remove all stored files for a project."""
        try:
            results = self.repo_collection.get(where={"project_id": str(project_id)})
            if results["ids"]:
                self.repo_collection.delete(ids=results["ids"])
        except Exception as e:
            print(f"Warning: Failed to clear project files: {e}")

    # ── Project Memory ────────────────────────────────────────────────────────

    def store_memory(self, project_id: int, memory_type: str, content: str) -> str:
        """Store a project memory/insight."""
        try:
            doc_id = self._make_id(f"{project_id}_{memory_type}_{content[:50]}", "mem")
            self.memory_collection.upsert(
                documents=[content],
                metadatas=[{"project_id": str(project_id), "memory_type": memory_type}],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Warning: Failed to store memory: {e}")
            return ""

    def search_memory(self, query: str, project_id: int = None, n_results: int = 5) -> List[Dict]:
        """Search project memories semantically."""
        try:
            count = self.memory_collection.count()
            if count == 0:
                return []
            where = {"project_id": str(project_id)} if project_id else None
            results = self.memory_collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where=where
            )
            if not results["documents"] or not results["documents"][0]:
                return []
            return [
                {"content": doc, "metadata": results["metadatas"][0][i]}
                for i, doc in enumerate(results["documents"][0])
            ]
        except Exception as e:
            print(f"Warning: Memory search error: {e}")
            return []

    # ── Conversation Memory ───────────────────────────────────────────────────

    def store_conversation(self, project_id: int, role: str, content: str, agent: str = "general"):
        """Store a conversation turn for semantic search."""
        try:
            doc_id = self._make_id(f"{project_id}_{role}_{content[:50]}", "conv")
            self.conversation_collection.upsert(
                documents=[f"{role}: {content}"],
                metadatas=[{"project_id": str(project_id), "role": role, "agent": agent}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"Warning: Failed to store conversation: {e}")

    def search_conversations(self, query: str, project_id: int, n_results: int = 5) -> List[Dict]:
        """Search past conversations semantically."""
        try:
            count = self.conversation_collection.count()
            if count == 0:
                return []
            results = self.conversation_collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
                where={"project_id": str(project_id)}
            )
            if not results["documents"] or not results["documents"][0]:
                return []
            return [{"content": doc, "metadata": results["metadatas"][0][i]}
                    for i, doc in enumerate(results["documents"][0])]
        except Exception as e:
            print(f"Warning: Conversation search error: {e}")
            return []

    # ── Debug Memory ──────────────────────────────────────────────────────────

    def store_debug(self, project_id: int, error: str, analysis: str, fix: str):
        """Store debugging history."""
        try:
            content = f"Error: {error}\nAnalysis: {analysis}\nFix: {fix}"
            doc_id = self._make_id(f"{project_id}_{error[:50]}", "dbg")
            self.debug_collection.upsert(
                documents=[content],
                metadatas=[{"project_id": str(project_id)}],
                ids=[doc_id]
            )
        except Exception as e:
            print(f"Warning: Failed to store debug: {e}")

    def search_debug_history(self, error: str, project_id: int) -> List[Dict]:
        """Find similar past errors and their solutions."""
        try:
            count = self.debug_collection.count()
            if count == 0:
                return []
            results = self.debug_collection.query(
                query_texts=[error],
                n_results=min(3, count)
            )
            if not results["documents"] or not results["documents"][0]:
                return []
            return [{"content": doc} for doc in results["documents"][0]]
        except Exception as e:
            print(f"Warning: Debug search error: {e}")
            return []

    def get_stats(self) -> Dict:
        """Return vector store statistics."""
        try:
            return {
                "repository_files": self.repo_collection.count(),
                "memories": self.memory_collection.count(),
                "conversations": self.conversation_collection.count(),
                "debug_entries": self.debug_collection.count(),
            }
        except Exception:
            return {}
