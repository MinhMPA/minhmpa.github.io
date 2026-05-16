"""Unit tests for scripts/build_faq_from_wiki.py."""

from __future__ import annotations

import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_faq_from_wiki as bfw

FIXTURE_WIKI = Path(__file__).resolve().parent / "fixtures" / "synthetic_wiki"


class LoadWikiRecordsTest(unittest.TestCase):
    def test_loads_all_three_records(self):
        records = bfw.load_wiki_records(FIXTURE_WIKI)
        self.assertEqual(sorted(records.keys()), ["SRC-0001", "SRC-0002", "SRC-0003"])

    def test_record_fields_passed_through(self):
        records = bfw.load_wiki_records(FIXTURE_WIKI)
        r = records["SRC-0001"]
        self.assertEqual(r["title"],
                         "How much information can be extracted from galaxy clustering at the field level?")
        self.assertEqual(r["authors"],
                         ["Nhat-Minh Nguyen", "Fabian Schmidt"])
        self.assertEqual(r["arxiv_id"], "2403.03220")

    def test_arxiv_id_strips_version_suffix(self):
        records = bfw.load_wiki_records(FIXTURE_WIKI)
        self.assertEqual(records["SRC-0002"]["arxiv_id"], "1611.09787")


class ExtractSummaryBodyTest(unittest.TestCase):
    def test_extracts_only_prose_under_summary_heading(self):
        page = FIXTURE_WIKI / "wiki_pages" / "sources" / "SRC-0001-authored-paper.md"
        body = bfw.extract_summary_body(page)
        self.assertTrue(body.startswith("This Letter asks"))
        self.assertIn("LEFTfield", body)
        self.assertIn("A second paragraph", body)

    def test_failure_marker_is_returned_verbatim(self):
        page = FIXTURE_WIKI / "wiki_pages" / "sources" / "SRC-0003-failure-marker.md"
        body = bfw.extract_summary_body(page)
        self.assertEqual(body.strip(), "_Not yet written._")


if __name__ == "__main__":
    unittest.main()
