"""
OpenSeesPy and OPSVIS FastMCP Server.
Standard I/O transport for Google Antigravity integration.
Stdout is strictly reserved for JSON-RPC messages; all logging goes to stderr.
"""
import sys
import logging
from typing import Optional, List, Dict, Any

# Configure logging exclusively to stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("opensees_mcp")

# Import FastMCP / MCPServer safely across mcp versions
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        logger.error(f"Failed to import FastMCP/MCPServer: {e}")
        raise

from config import DEFAULT_SEARCH_LIMIT
from db import Database
from indexer import DocIndexer
from search import DocSearch

# Initialize FastMCP Server instance
mcp = FastMCP("OpenSeesPy & OPSVIS Documentation Server")

# Initialize DB, search engine, and indexer
db = Database()
search_engine = DocSearch(db)
indexer = DocIndexer(db)

@mcp.tool()
def search_docs(query: str, repo: Optional[str] = None, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Dict[str, Any]]:
    """
    Search OpenSeesPy and OPSVIS documentation using BM25 ranking.
    Returns token-efficient excerpts and chunk IDs.
    
    Args:
        query: Keywords or API command to search for (e.g. 'Steel01', 'fiber section', 'plot_model').
        repo: Filter by repository ('openseespy' or 'opsvis'). Optional.
        limit: Number of results to return (default 5, max 20).
    """
    logger.info(f"Tool search_docs called: query={query!r}, repo={repo!r}, limit={limit}")
    return search_engine.search(query=query, repo=repo, limit=limit)

@mcp.tool()
def get_doc_section(chunk_id: str) -> Dict[str, Any]:
    """
    Retrieve the full content, parameters, and code examples for a specific documentation section.
    
    Args:
        chunk_id: The unique chunk ID obtained from search_docs or get_command_help.
    """
    logger.info(f"Tool get_doc_section called: chunk_id={chunk_id!r}")
    result = search_engine.get_section(chunk_id=chunk_id)
    if not result:
        return {"error": f"Section with chunk_id '{chunk_id}' not found."}
    return result

@mcp.tool()
def get_command_help(command_name: str) -> Dict[str, Any]:
    """
    Retrieve quick syntax, parameters, description, and code examples for an OpenSeesPy or OPSVIS command.
    
    Args:
        command_name: Name of the command (e.g., 'model', 'node', 'element', 'uniaxialMaterial', 'plot_defo').
    """
    logger.info(f"Tool get_command_help called: command_name={command_name!r}")
    result = search_engine.get_command_help(command_name=command_name)
    if not result:
        return {"error": f"Command '{command_name}' not found. Try searching with search_docs()."}
    return result

@mcp.tool()
def list_doc_topics(repo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List indexed documentation topics and chapter categories.
    
    Args:
        repo: Filter by 'openseespy' or 'opsvis'. Optional.
    """
    logger.info(f"Tool list_doc_topics called: repo={repo!r}")
    return search_engine.list_topics(repo=repo)

@mcp.tool()
def refresh_doc_index() -> Dict[str, Any]:
    """
    Incrementally scan documentation directories and update the SQLite FTS index.
    Detects added, updated, and deleted files.
    """
    logger.info("Tool refresh_doc_index called")
    return indexer.index_all(force=False)

@mcp.tool()
def get_doc_sources() -> Dict[str, Any]:
    """
    Get indexed documentation statistics, including total documents and chunks per repository.
    """
    logger.info("Tool get_doc_sources called")
    return db.get_stats()

def main():
    """Main entrypoint for MCP server over STDIO transport."""
    logger.info("Starting OpenSees & OPSVIS MCP Server on STDIO transport...")
    try:
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

