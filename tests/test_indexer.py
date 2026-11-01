"""
Unit and integration tests for SQLite indexing engine.
"""
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import Database
from indexer import DocIndexer

class TestIndexer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_index.db"
        self.db = Database(self.db_path)
        self.indexer = DocIndexer(self.db)

    def tearDown(self):
        import gc
        del self.indexer
        del self.db
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_incremental_indexing(self):
        stats_initial = self.indexer.index_all(force=False)
        self.assertGreater(stats_initial["added"], 0)
        self.assertEqual(stats_initial["deleted"], 0)

        # Second run without changes should report unchanged
        stats_second = self.indexer.index_all(force=False)
        self.assertEqual(stats_second["added"], 0)
        self.assertEqual(stats_second["updated"], 0)
        self.assertGreater(stats_second["unchanged"], 0)

if __name__ == "__main__":
    unittest.main()
