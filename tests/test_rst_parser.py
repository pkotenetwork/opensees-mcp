"""
Unit and integration tests for RST parser.
"""
import sys
from pathlib import Path
import unittest

# Ensure opensees_mcp is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rst_parser import RSTParser, clean_inline_rst, extract_signature_and_command

class TestRSTParser(unittest.TestCase):
    def test_clean_inline_rst(self):
        sample = ":func:`model` and ``uniaxialMaterial`` with `target`_"
        cleaned = clean_inline_rst(sample)
        self.assertIn("model", cleaned)
        self.assertIn("uniaxialMaterial", cleaned)
        self.assertNotIn(":func:", cleaned)

    def test_extract_signature_and_command(self):
        sig_line = ".. function:: model('basic', '-ndm', ndm, '-ndf', ndf=ndm*(ndm+1)/2)"
        sig, cmd = extract_signature_and_command(sig_line)
        self.assertEqual(cmd, "model")
        self.assertIn("'-ndm'", sig)

    def test_parse_real_file(self):
        from config import DOC_SOURCES
        opensees_dir = DOC_SOURCES["openseespy"]
        # Find model.rst
        model_files = list(opensees_dir.rglob("model.rst"))
        self.assertTrue(len(model_files) > 0, "model.rst should exist")
        chunks = RSTParser.parse_file(model_files[0], "openseespy")
        self.assertTrue(len(chunks) >= 1)
        # Check that signature or command was captured
        has_model_cmd = any("model" in c.command_name.lower() or "model" in c.doc_title.lower() for c in chunks)
        self.assertTrue(has_model_cmd)

if __name__ == "__main__":
    unittest.main()

