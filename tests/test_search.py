"""
Unit and integration tests for search engine and BM25 ranking.
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import Database
from search import DocSearch

class TestSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        cls.searcher = DocSearch(cls.db)

    def test_search_docs_limit_and_structure(self):
        results = self.searcher.search("Steel01", limit=3)
        self.assertLessEqual(len(results), 3)
        for r in results:
            self.assertIn("chunk_id", r)
            self.assertIn("excerpt", r)
            self.assertIn("relevance_rank", r)
            self.assertLessEqual(len(r["excerpt"]), 1000)

    def test_search_repo_filter(self):
        opsvis_res = self.searcher.search("plot_model", repo="opsvis")
        for r in opsvis_res:
            self.assertEqual(r["repo"], "opsvis")

    def test_get_command_help(self):
        help_info = self.searcher.get_command_help("model")
        self.assertIsNotNone(help_info)
        self.assertEqual(help_info["command_name"], "model")
        self.assertIn("-ndm", help_info["signature"])

    def test_get_section(self):
        help_info = self.searcher.get_command_help("model")
        chunk_id = help_info["chunk_id"]
        sec = self.searcher.get_section(chunk_id)
        self.assertIsNotNone(sec)
        self.assertEqual(sec["chunk_id"], chunk_id)
        self.assertIn("content", sec)

    def test_list_topics(self):
        topics = self.searcher.list_topics()
        self.assertGreater(len(topics), 0)
        repos = {t["repo"] for t in topics}
        self.assertIn("openseespy", repos)
        self.assertIn("opsvis", repos)

if __name__ == "__main__":
    unittest.main()

