# OpenSeesPy & OPSVIS Documentation MCP Server

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Built with Google Antigravity 2.0](https://img.shields.io/badge/Built%20with-Google%20Antigravity%202.0-4285F4.svg)](https://deepmind.google)
[![Powered by Gemini](https://img.shields.io/badge/AI%20Pair%20Programmer-Gemini%20Flash-F4B400.svg)](https://ai.google.dev)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

A lightweight, production-ready, and completely offline Model Context Protocol (MCP) server providing intelligent documentation search and code retrieval for **OpenSeesPy** and **OPSVIS**.

Designed specifically for structural engineers, researchers, and developers pair-programming with AI assistants such as **Google Antigravity 2.0**, **Gemini**, Claude, and Cursor.

---

## ⚡ Built With Google Antigravity 2.0 & Gemini

This project was architected, implemented, and verified entirely via pair programming using:
- **Google Antigravity 2.0** (Next-Generation Agentic Coding Environment by Google DeepMind)
- **Gemini** (Advanced Reasoning & Agentic Execution)

---

## 🎯 Key Features

- **100% Local & Offline**: Zero external vector APIs, embedding costs, or cloud services.
- **Dual-Layer Search Engine**:
  - **SQLite FTS5 BM25 Ranking** with boosted weighting for API commands and parameters.
  - **Fuzzy / Typo-Tolerant Fallback** utilizing trigram indexing and vocabulary distance matching (e.g. automatically resolves `elasitc` $\rightarrow$ `Elastic`).
- **AST-Powered Code Intelligence**: Statically parses function signatures and docstrings directly from Python source code without loading heavy DLLs.
- **Section-Aware Chunking**: Preserves structural parameters, equations, and executable Python examples without chunk fragmentation.
- **Strict Token Efficiency**: Excerpts are capped at ~500–800 characters to prevent context window bloat during LLM pair programming.
- **Clean STDIO Transport**: Fully compliant with the official MCP specification; `sys.stdout` is reserved strictly for JSON-RPC messages and logs route to `stderr`.

---

## 🛠️ Exposed MCP Tools

| Tool | Description |
| :--- | :--- |
| `search_docs(query, repo, limit)` | Full-text BM25 search across OpenSeesPy and OPSVIS with relevance ranking. |
| `get_doc_section(chunk_id)` | Fetches the complete section content, parameters, and full code examples. |
| `get_command_help(command_name)` | Quick retrieval of command signatures, argument tables, and syntax. |
| `list_doc_topics(repo)` | Lists top-level chapters, sections, and module hierarchies. |
| `refresh_doc_index()` | Incrementally updates the database when documentation files change. |
| `get_doc_sources()` | Displays indexing statistics across both repositories. |

---

## 🚀 Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/pkotenetwork/opensees-mcp.git
cd opensees-mcp
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(The repository includes the pre-indexed `doc_index.db` covering 548 files and 1,293 chunks—ready to query immediately).*

---

## 🤖 Google Antigravity 2.0 Configuration

Add the server to your Antigravity MCP configuration (`~/.gemini/antigravity/mcp_config.json` or `~/.gemini/config/mcp_config.json`):

```json
{
  "mcpServers": {
    "opensees-docs": {
      "command": "python",
      "args": [
        "/path/to/opensees-mcp/server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```
*(On Windows, provide the full path to `python.exe` and escape backslashes, e.g. `C:\\ProgramData\\anaconda3\\python.exe` and `D:\\opensees-mcp\\server.py`).*

---

## 🧪 Testing

Run the automated test suite (parser, incremental indexer, BM25 search, and MCP endpoints):
```bash
python -m unittest discover -s tests
```

---

## 📄 License & Attribution

- **License**: Released under the [GNU General Public License v3.0 (GPLv3)](./LICENSE).
- **OpenSees & OpenSeesPy**: Open System for Earthquake Engineering Simulation (UC Berkeley / PEER).
- **OPSVIS**: Pre-, post-processing and visualization Python module for OpenSeesPy by Seweryn Kokot (Opole University of Technology, Poland). Cite: *SoftwareX, 34, 102615 (2026)*.
- **Author**: Prashant Kote ([@pkotenetwork](https://github.com/pkotenetwork))
