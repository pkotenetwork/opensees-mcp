"""
Integration tests for FastMCP server tool functions.
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import (
    search_docs,
    get_doc_section,
    get_command_help,
    list_doc_topics,
    refresh_doc_index,
    get_doc_sources
)

class TestServerTools(unittest.TestCase):
    def test_sources_stats(self):
        stats = get_doc_sources()
        self.assertIn("total_documents", stats)
        self.assertGreater(stats["total_documents"], 0)
        self.assertIn("openseespy", stats["by_repo"])
        self.assertIn("opsvis", stats["by_repo"])

    def test_search_and_get_section(self):
        results = search_docs("uniaxialMaterial", limit=2)
        self.assertTrue(len(results) > 0)
        first_chunk_id = results[0]["chunk_id"]

        section = get_doc_section(first_chunk_id)
        self.assertEqual(section["chunk_id"], first_chunk_id)

    def test_get_command_help(self):
        cmd_help = get_command_help("plot_defo")
        self.assertNotIn("error", cmd_help)
        self.assertEqual(cmd_help["command_name"], "plot_defo")
        self.assertEqual(cmd_help["repo"], "opsvis")

    def test_list_topics(self):
        topics = list_doc_topics(repo="opsvis")
        self.assertTrue(len(topics) > 0)
        self.assertTrue(all(t["repo"] == "opsvis" for t in topics))

    def test_refresh_doc_index(self):
        refresh_stat = refresh_doc_index()
        self.assertIn("unchanged", refresh_stat)
        self.assertGreater(refresh_stat["unchanged"], 0)

if __name__ == "__main__":
    unittest.main()

