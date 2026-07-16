import json
import tempfile
import unittest
from pathlib import Path

from monitor import atomic_write_json, build_record, extract_visible_text, read_previous_hash


class MonitorTests(unittest.TestCase):
    def test_extracts_visible_text_and_ignores_nonvisible_content(self):
        html = """
        <html><head><title> Example </title><style>.x{display:none}</style></head>
        <body><h1>Hello&nbsp;world</h1><script>secret()</script></body></html>
        """
        text, title = extract_visible_text(html)
        self.assertEqual(title, "Example")
        self.assertEqual(text, "Example Hello world")
        self.assertNotIn("secret", text)

    def test_whitespace_only_change_keeps_the_same_hash(self):
        first = build_record("<p>Hello world</p>", "first", None)
        second = build_record("<p> Hello\n  world </p>", "second", first["text_sha256"])
        self.assertFalse(second["changed"])

    def test_copy_change_is_detected(self):
        first = build_record("<p>Book a demo</p>", "first", None)
        second = build_record("<p>Start a free trial</p>", "second", first["text_sha256"])
        self.assertTrue(second["changed"])

    def test_atomic_baseline_can_be_read(self):
        record = build_record("<p>Evidence</p>", "fixture", None)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            atomic_write_json(path, record)
            self.assertEqual(read_previous_hash(path), record["text_sha256"])
            self.assertEqual(json.loads(path.read_text())["source"], "fixture")


if __name__ == "__main__":
    unittest.main()

