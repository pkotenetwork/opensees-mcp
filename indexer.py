"""
Incremental indexer for OpenSeesPy and OPSVIS documentation.
Detects added, modified, and removed files using mtime and content hash.
"""
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any

from config import DOC_SOURCES
from db import Database
from rst_parser import RSTParser

def compute_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()

class DocIndexer:
    def __init__(self, db: Database = None):
        self.db = db or Database()

    def index_all(self, force: bool = False) -> Dict[str, Any]:
        """Performs an incremental update over all configured documentation sources."""
        stats = {
            "scanned": 0,
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "unchanged": 0,
            "total_chunks_indexed": 0
        }

        tracked_docs = self.db.get_all_document_paths()
        found_file_paths = set()

        for repo, doc_dir in DOC_SOURCES.items():
            if not doc_dir.exists():
                print(f"[WARN] Documentation directory not found: {doc_dir}", file=sys.stderr)
                continue

            for rst_path in doc_dir.rglob("*.rst"):
                stats["scanned"] += 1
                norm_path = str(rst_path.resolve())
                found_file_paths.add(norm_path)

                mtime = rst_path.stat().st_mtime
                doc_meta = self.db.get_document_meta(norm_path)

                # Check if file has been modified
                if not force and doc_meta is not None:
                    if abs(doc_meta["mtime"] - mtime) < 1e-4:
                        stats["unchanged"] += 1
                        continue

                # Read and check content hash
                try:
                    raw_bytes = rst_path.read_bytes()
                except Exception as e:
                    print(f"[ERROR] Could not read {rst_path}: {e}", file=sys.stderr)
                    continue

                content_hash = compute_hash(raw_bytes)
                if not force and doc_meta is not None and doc_meta["content_hash"] == content_hash:
                    stats["unchanged"] += 1
                    continue

                # Parse file
                chunks = RSTParser.parse_file(rst_path, repo)
                if not chunks:
                    continue

                doc_id = f"{repo}:{rst_path.stem}"
                new_doc_meta = {
                    "doc_id": doc_id,
                    "repo": repo,
                    "file_path": norm_path,
                    "mtime": mtime,
                    "content_hash": content_hash,
                    "doc_title": chunks[0].doc_title,
                    "chunk_count": len(chunks)
                }

                chunks_data = [
                    {
                        "chunk_id": c.chunk_id,
                        "doc_id": doc_id,
                        "repo": c.repo,
                        "file_path": c.file_path,
                        "doc_title": c.doc_title,
                        "section_title": c.section_title,
                        "command_name": c.command_name,
                        "signature": c.signature,
                        "parameters": c.parameters,
                        "content": c.content,
                        "code_blocks": c.code_blocks,
                        "breadcrumbs": c.breadcrumbs,
                        "token_estimate": c.token_estimate
                    }
                    for c in chunks
                ]

                self.db.insert_document_and_chunks(new_doc_meta, chunks_data)
                stats["total_chunks_indexed"] += len(chunks)

                if doc_meta is None:
                    stats["added"] += 1
                else:
                    stats["updated"] += 1

        # Delete documents that no longer exist on disk
        for tracked_path, doc_id in tracked_docs.items():
            if tracked_path not in found_file_paths:
                self.db.delete_document(doc_id)
                stats["deleted"] += 1

        return stats

if __name__ == "__main__":
    indexer = DocIndexer()
    results = indexer.index_all(force=True)
    print("Indexing completed:", results, file=sys.stderr)

