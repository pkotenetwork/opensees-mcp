"""
Configuration settings for OpenSeesPy and OPSVIS documentation MCP server.
"""
from pathlib import Path
import sys

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Parent directory containing the documentation folders
PROJECT_ROOT = BASE_DIR.parent

# Paths to documentation repositories
DOC_SOURCES = {
    "openseespy": PROJECT_ROOT / "OpenseesPy_Docs",
    "opsvis": PROJECT_ROOT / "OPSVIS_Docs",
}

# Database path for SQLite with FTS5
DB_PATH = BASE_DIR / "doc_index.db"

# Excerpt token / character constraints
EXCERPT_MAX_CHARS = 800
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20

# Python executable to use
PYTHON_EXE = sys.executable

