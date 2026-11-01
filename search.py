"""
Search engine using SQLite FTS5 BM25 ranking and token-efficient snippet generation.
"""
import difflib
import re
from typing import List, Dict, Any, Optional

from config import DB_PATH, EXCERPT_MAX_CHARS, DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT
from db import Database

class DocSearch:
    def __init__(self, db: Database = None):
        self.db = db or Database()
        self._command_vocabulary = None

    def _get_vocabulary(self) -> List[str]:
        """Loads unique command and section names for spelling suggestion."""
        if self._command_vocabulary is None:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT command_name FROM chunks WHERE length(command_name) > 1")
                self._command_vocabulary = [r[0] for r in cur.fetchall() if r[0]]
        return self._command_vocabulary

    def _suggest_corrections(self, query: str) -> List[str]:
        """Finds closest vocabulary terms for words that might have typos."""
        vocab = self._get_vocabulary()
        words = re.findall(r"[a-zA-Z_]{3,}", query)
        corrections = []
        for w in words:
            matches = difflib.get_close_matches(w, vocab, n=2, cutoff=0.6)
            for m in matches:
                if m.lower() != w.lower():
                    corrections.append(m)
        return corrections

    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitizes user input for SQLite FTS5 query syntax."""
        cleaned = re.sub(r'["\'*^:()\[\]{}]', ' ', query).strip()
        tokens = cleaned.split()
        if not tokens:
            return ""
        # Match tokens with prefix search on the last term
        formatted_tokens = []
        for i, token in enumerate(tokens):
            if i == len(tokens) - 1 and len(token) >= 2:
                formatted_tokens.append(f'"{token}"*')
            else:
                formatted_tokens.append(f'"{token}"')
        return " AND ".join(formatted_tokens)

    def _create_concise_excerpt(self, content: str, query: str, max_chars: int = EXCERPT_MAX_CHARS) -> str:
        """Generates a clean, token-efficient excerpt focused on query keywords or API content."""
        if not content:
            return ""

        # Normalize multiple spaces / newlines
        clean_text = re.sub(r"\n{2,}", "\n", content).strip()

        if len(clean_text) <= max_chars:
            return clean_text

        # Try to locate the query keywords in text
        q_words = [w.lower() for w in re.split(r"\W+", query) if len(w) > 2]
        match_pos = -1
        for word in q_words:
            pos = clean_text.lower().find(word)
            if pos != -1:
                match_pos = pos
                break

        if match_pos == -1 or match_pos < 100:
            # Take from beginning
            excerpt = clean_text[:max_chars].rsplit(" ", 1)[0]
            return excerpt + "..."
        else:
            # Center around match
            start = max(0, match_pos - 150)
            end = min(len(clean_text), start + max_chars)
            excerpt = clean_text[start:end].strip()
            if start > 0:
                excerpt = "..." + excerpt.split(" ", 1)[-1]
            if end < len(clean_text):
                excerpt = excerpt.rsplit(" ", 1)[0] + "..."
            return excerpt

    def search(self, query: str, repo: Optional[str] = None, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Dict[str, Any]]:
        """
        Executes an FTS5 search with BM25 ranking.
        Boosts command_name and signature matches.
        """
        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        fts_query = self._sanitize_fts_query(query)

        if not fts_query:
            return []

        # FTS5 bm25 weights: (command_name: 10.0, section_title: 5.0, signature: 10.0, parameters: 3.0, content: 1.0)
        # Note: chunk_id is unindexed so FTS5 columns are: 0: command_name, 1: section_title, 2: signature, 3: parameters, 4: content
        sql = """
            SELECT
                c.chunk_id,
                c.repo,
                c.doc_title,
                c.section_title,
                c.command_name,
                c.signature,
                c.content,
                c.code_blocks,
                bm25(chunks_fts, 10.0, 5.0, 10.0, 3.0, 1.0) as rank
            FROM chunks_fts f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            WHERE chunks_fts MATCH ?
        """
        params = [fts_query]

        if repo:
            sql += " AND c.repo = ?"
            params.append(repo.lower().strip())

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(sql, params)
                rows = cur.fetchall()
            except Exception:
                rows = []

            # If no results found with standard BM25, try spelling correction fallback
            if not rows:
                suggestions = self._suggest_corrections(query)
                for corrected in suggestions:
                    fallback_fts = self._sanitize_fts_query(corrected)
                    if fallback_fts:
                        fb_sql = """
                            SELECT
                                c.chunk_id,
                                c.repo,
                                c.doc_title,
                                c.section_title,
                                c.command_name,
                                c.signature,
                                c.content,
                                c.code_blocks,
                                bm25(chunks_fts, 10.0, 5.0, 10.0, 3.0, 1.0) as rank
                            FROM chunks_fts f
                            JOIN chunks c ON c.chunk_id = f.chunk_id
                            WHERE chunks_fts MATCH ?
                        """
                        fb_params = [fallback_fts]
                        if repo:
                            fb_sql += " AND c.repo = ?"
                            fb_params.append(repo.lower().strip())
                        fb_sql += " ORDER BY rank LIMIT ?"
                        fb_params.append(limit)

                        try:
                            cur.execute(fb_sql, fb_params)
                            fb_rows = cur.fetchall()
                            if fb_rows:
                                rows = fb_rows
                                break
                        except Exception:
                            pass

        results = []
        for r in rows:
            excerpt = self._create_concise_excerpt(r["content"], query)
            results.append({
                "chunk_id": r["chunk_id"],
                "repo": r["repo"],
                "doc_title": r["doc_title"],
                "section_title": r["section_title"],
                "command_name": r["command_name"],
                "signature": r["signature"],
                "excerpt": excerpt,
                "has_code": bool(r["code_blocks"] and r["code_blocks"].strip()),
                "relevance_rank": round(float(r["rank"]), 3)
            })

        return results

    def get_section(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the full content and code examples for a specific chunk."""
        sql = """
            SELECT
                chunk_id,
                repo,
                file_path,
                doc_title,
                section_title,
                command_name,
                signature,
                parameters,
                content,
                code_blocks,
                breadcrumbs
            FROM chunks
            WHERE chunk_id = ?
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (chunk_id.strip(),))
            row = cur.fetchone()
            if not row:
                return None

            return {
                "chunk_id": row["chunk_id"],
                "repo": row["repo"],
                "file_path": row["file_path"],
                "doc_title": row["doc_title"],
                "section_title": row["section_title"],
                "command_name": row["command_name"],
                "signature": row["signature"],
                "parameters": row["parameters"],
                "content": row["content"],
                "code_blocks": row["code_blocks"],
                "breadcrumbs": row["breadcrumbs"]
            }

    def get_command_help(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Exact or best-match retrieval for API syntax, parameters, and examples."""
        clean_name = command_name.strip()

        # 1. Try exact match on command_name
        sql = """
            SELECT chunk_id, repo, doc_title, section_title, command_name,
                   signature, parameters, content, code_blocks
            FROM chunks
            WHERE LOWER(command_name) = LOWER(?)
            ORDER BY (signature IS NOT NULL AND signature != '') DESC
            LIMIT 1
        """
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (clean_name,))
            row = cur.fetchone()

            if not row:
                # 2. Try partial match on command_name or signature
                cur.execute(
                    """
                    SELECT chunk_id, repo, doc_title, section_title, command_name,
                           signature, parameters, content, code_blocks
                    FROM chunks
                    WHERE LOWER(command_name) LIKE ? OR LOWER(signature) LIKE ?
                    ORDER BY (signature IS NOT NULL AND signature != '') DESC
                    LIMIT 1
                    """,
                    (f"%{clean_name}%", f"%{clean_name}%")
                )
                row = cur.fetchone()

            if not row:
                return None

            return {
                "command_name": row["command_name"],
                "signature": row["signature"] or f"{row['command_name']}(...)",
                "repo": row["repo"],
                "doc_title": row["doc_title"],
                "parameters": row["parameters"],
                "description": self._create_concise_excerpt(row["content"], clean_name, max_chars=600),
                "code_example": row["code_blocks"] if row["code_blocks"] else None,
                "chunk_id": row["chunk_id"]
            }

    def list_topics(self, repo: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists high-level topics and categories grouped by repository."""
        sql = """
            SELECT repo, doc_title, COUNT(*) as chunk_count
            FROM chunks
        """
        params = []
        if repo:
            sql += " WHERE repo = ?"
            params.append(repo.lower().strip())

        sql += " GROUP BY repo, doc_title ORDER BY repo, doc_title"

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [{"repo": r["repo"], "title": r["doc_title"], "chunk_count": r["chunk_count"]} for r in rows]

