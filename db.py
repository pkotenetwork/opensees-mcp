"""
Database management using SQLite with FTS5 and BM25 ranking.
"""
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import DB_PATH

SCHEMA_SQL = """
-- Table of tracked documentation source files for incremental updates
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    mtime REAL NOT NULL,
    content_hash TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    chunk_count INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table of documentation chunks
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    file_path TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    section_title TEXT NOT NULL,
    command_name TEXT NOT NULL,
    signature TEXT,
    parameters TEXT,
    content TEXT NOT NULL,
    code_blocks TEXT,
    breadcrumbs TEXT,
    token_estimate INTEGER,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Full-text search index table using SQLite FTS5 (porter tokenizer for words)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    command_name,
    section_title,
    signature,
    parameters,
    content,
    tokenize = 'porter unicode61'
);

-- Trigram index table for fuzzy/typo-tolerant matching on command names and signatures
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_trigram USING fts5(
    chunk_id UNINDEXED,
    command_name,
    signature,
    tokenize = 'trigram'
);

-- Indices for rapid exact lookups
CREATE INDEX IF NOT EXISTS idx_chunks_command ON chunks(command_name);
CREATE INDEX IF NOT EXISTS idx_chunks_repo ON chunks(repo);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
"""

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def get_document_meta(self, file_path: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM documents WHERE file_path = ?", (file_path,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    def delete_document(self, doc_id: str):
        with self.get_connection() as conn:
            cur = conn.cursor()
            # Delete from FTS first
            cur.execute("DELETE FROM chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_id,))
            cur.execute("DELETE FROM chunks_trigram WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_id,))
            cur.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            cur.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()

    def insert_document_and_chunks(self, doc_meta: Dict[str, Any], chunks: List[Dict[str, Any]]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            # If doc exists, clean old records
            cur.execute("DELETE FROM chunks_fts WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_meta["doc_id"],))
            cur.execute("DELETE FROM chunks_trigram WHERE chunk_id IN (SELECT chunk_id FROM chunks WHERE doc_id = ?)", (doc_meta["doc_id"],))
            cur.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_meta["doc_id"],))
            cur.execute("DELETE FROM documents WHERE doc_id = ?", (doc_meta["doc_id"],))

            cur.execute(
                """
                INSERT INTO documents (doc_id, repo, file_path, mtime, content_hash, doc_title, chunk_count)
                VALUES (:doc_id, :repo, :file_path, :mtime, :content_hash, :doc_title, :chunk_count)
                """,
                doc_meta
            )

            for chunk in chunks:
                cur.execute(
                    """
                    INSERT INTO chunks (chunk_id, doc_id, repo, file_path, doc_title, section_title,
                                        command_name, signature, parameters, content, code_blocks,
                                        breadcrumbs, token_estimate)
                    VALUES (:chunk_id, :doc_id, :repo, :file_path, :doc_title, :section_title,
                            :command_name, :signature, :parameters, :content, :code_blocks,
                            :breadcrumbs, :token_estimate)
                    """,
                    chunk
                )
                cur.execute(
                    """
                    INSERT INTO chunks_fts (chunk_id, command_name, section_title, signature, parameters, content)
                    VALUES (:chunk_id, :command_name, :section_title, :signature, :parameters, :content)
                    """,
                    {
                        "chunk_id": chunk["chunk_id"],
                        "command_name": chunk["command_name"],
                        "section_title": chunk["section_title"],
                        "signature": chunk["signature"] or "",
                        "parameters": chunk["parameters"] or "",
                        "content": chunk["content"] or ""
                    }
                )
                cur.execute(
                    """
                    INSERT INTO chunks_trigram (chunk_id, command_name, signature)
                    VALUES (:chunk_id, :command_name, :signature)
                    """,
                    {
                        "chunk_id": chunk["chunk_id"],
                        "command_name": chunk["command_name"],
                        "signature": chunk["signature"] or ""
                    }
                )
            conn.commit()

    def get_all_document_paths(self) -> Dict[str, str]:
        """Returns map of file_path -> doc_id for all tracked documents."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT file_path, doc_id FROM documents")
            return {row["file_path"]: row["doc_id"] for row in cur.fetchall()}

    def get_stats(self) -> Dict[str, Any]:
        """Returns statistics for indexed documents."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT repo, COUNT(DISTINCT doc_id) as doc_count, COUNT(*) as chunk_count FROM chunks GROUP BY repo")
            repo_stats = {row["repo"]: {"documents": row["doc_count"], "chunks": row["chunk_count"]} for row in cur.fetchall()}

            cur.execute("SELECT COUNT(*) FROM documents")
            total_docs = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cur.fetchone()[0]

            return {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "by_repo": repo_stats
            }
