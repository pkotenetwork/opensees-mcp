# OpenSeesPy & OPSVIS Documentation MCP Server

A lightweight, production-ready local Model Context Protocol (MCP) server for searching, browsing, and retrieving documentation for **OpenSeesPy** and **OPSVIS**.

## Key Features

- **Local & Offline**: Zero external APIs, embeddings, or third-party cloud services.
- **SQLite FTS5 + BM25 Ranking**: Fast, native full-text search with boosted weighting for API commands and function signatures.
- **Section-Based Chunking**: Preserves parameters, technical descriptions, and Python code examples without fragmentation.
- **Incremental Indexing**: Uses file timestamps (`mtime`) and content hashing to instantly track added, updated, or removed documentation files.
- **Strict Token Efficiency**: Short, focused excerpts (~500–800 chars) by default; full sections and code blocks are only fetched on explicit request.
- **Clean STDIO Transport**: Standard output is reserved strictly for MCP JSON-RPC protocol messages; all logs write to `stderr`.

---

## Directory Structure

```text
opensees_mcp/
├── config.py                 # Paths, search limits, and database configuration
├── rst_parser.py             # RST parser, Sphinx directives, code block extractor
├── db.py                     # SQLite FTS5 database schema and helpers
├── indexer.py                # Incremental file indexer
├── search.py                 # BM25 search engine and token-optimized snippet generator
├── server.py                 # FastMCP STDIO server exposing MCP tools
├── requirements.txt          # Python dependencies (mcp>=2.3.0)
├── doc_index.db              # Pre-indexed SQLite database
└── tests/                    # Automated unit and integration test suite
    ├── test_rst_parser.py
    ├── test_indexer.py
    ├── test_search.py
    └── test_server.py
```

---

## Exposed MCP Tools

1. `search_docs(query: str, repo: Optional[str] = None, limit: int = 5)`
   - Full-text search with BM25 ranking across OpenSeesPy and OPSVIS documentation.
   - Returns concise excerpts with chunk IDs and match relevance.
2. `get_doc_section(chunk_id: str)`
   - Retrieves the full documentation content, parameters, and complete Python code blocks for a specific chunk.
3. `get_command_help(command_name: str)`
   - Quick lookup for command signatures, parameters, usage descriptions, and code examples (e.g., `model`, `node`, `plot_defo`).
4. `list_doc_topics(repo: Optional[str] = None)`
   - Lists all top-level documentation sections, chapters, and available modules.
5. `refresh_doc_index()`
   - Incrementally scans documentation directories and synchronizes SQLite FTS5 with disk changes.
6. `get_doc_sources()`
   - Displays indexed documentation statistics (document counts and chunk counts per repository).

---

## Google Antigravity MCP Configuration

To add this server to Antigravity, add the following configuration to your Antigravity MCP settings (`mcp_config.json` or Antigravity Settings > MCP Servers):

```json
{
  "mcpServers": {
    "opensees-docs": {
      "command": "C:\\ProgramData\\anaconda3\\python.exe",
      "args": [
        "d:\\OneDrive-Personal\\OneDrive\\Data\\OpenseesPy\\opensees_mcp\\server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

---

## Manual Execution & Testing

### 1. Re-index Documentation
```bash
C:\ProgramData\anaconda3\python.exe d:\OneDrive-Personal\OneDrive\Data\OpenseesPy\opensees_mcp\indexer.py
```

### 2. Run Test Suite
```bash
C:\ProgramData\anaconda3\python.exe -m unittest discover -s d:\OneDrive-Personal\OneDrive\Data\OpenseesPy\opensees_mcp\tests
```

### 3. Run MCP Server directly
```bash
C:\ProgramData\anaconda3\python.exe d:\OneDrive-Personal\OneDrive\Data\OpenseesPy\opensees_mcp\server.py
```

