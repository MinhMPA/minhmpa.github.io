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


class IsAuthoredTest(unittest.TestCase):
    def test_exact_full_name_matches(self):
        self.assertTrue(bfw.is_authored(["Nhat-Minh Nguyen", "Fabian Schmidt"]))

    def test_initial_form_matches(self):
        self.assertTrue(bfw.is_authored(["N. Nguyen", "F. Schmidt"]))

    def test_short_form_matches(self):
        self.assertTrue(bfw.is_authored(["Minh Nguyen"]))

    def test_no_hyphen_form_matches(self):
        self.assertTrue(bfw.is_authored(["Nhat Minh Nguyen"]))

    def test_case_insensitive(self):
        self.assertTrue(bfw.is_authored(["NHAT-MINH NGUYEN"]))

    def test_returns_false_when_absent(self):
        self.assertFalse(bfw.is_authored(["Vincent Desjacques", "Donghui Jeong"]))

    def test_handles_empty_list(self):
        self.assertFalse(bfw.is_authored([]))


class DistillAnswerTest(unittest.TestCase):
    FIRST = (
        "This Letter asks how much cosmological information can be robustly "
        "extracted from nonlinear galaxy clustering, by performing optimal "
        "Bayesian field-level inference of sigma_8 from simulated dark matter "
        "halos using the LEFTfield forward model."
    )
    SECOND = (
        "The constraint comes entirely from nonlinear information."
    )
    BODY = f"{FIRST} {SECOND}\n\nA second paragraph that should not appear."

    def test_authored_prefix(self):
        out = bfw.distill_answer(
            body=self.BODY,
            arxiv_id="2403.03220",
            authored=True,
            first_author="Nhat-Minh Nguyen",
            title="Test paper",
        )
        self.assertTrue(out.startswith("Minh and collaborators (arXiv:2403.03220):"))
        self.assertIn("nonlinear galaxy clustering", out)

    def test_unauthored_prefix(self):
        out = bfw.distill_answer(
            body=self.BODY,
            arxiv_id="1611.09787",
            authored=False,
            first_author="Vincent Desjacques",
            title="Large-Scale Galaxy Bias",
        )
        self.assertTrue(out.startswith("Desjacques et al. (arXiv:1611.09787):"))

    def test_truncates_long_first_sentence(self):
        long_sentence = " ".join(["word"] * 200) + "."
        out = bfw.distill_answer(
            body=long_sentence,
            arxiv_id="0000.00000",
            authored=True,
            first_author="Minh Nguyen",
            title="Long",
        )
        # 80-word cap + ellipsis
        self.assertIn("…", out)
        body_after_prefix = out.split(": ", 1)[1]
        # crude word count
        word_count = len([w for w in body_after_prefix.replace("…", "").split() if w])
        self.assertLessEqual(word_count, 80)

    def test_failure_marker_emits_fallback(self):
        out = bfw.distill_answer(
            body="_Not yet written._",
            arxiv_id="2604.25171",
            authored=True,
            first_author="Nhat-Minh Nguyen",
            title="Multi-tracers, multi-surveys",
        )
        self.assertIn("Multi-tracers, multi-surveys", out)
        self.assertIn("arXiv:2604.25171", out)
        self.assertIn("summary is not yet available", out.lower())
        # fallback does not use "Minh and collaborators" framing
        self.assertNotIn("Minh and collaborators", out)

    def test_pdf_extraction_failure_marker_also_emits_fallback(self):
        out = bfw.distill_answer(
            body="_PDF text extraction was unusable._",
            arxiv_id="9999.99999",
            authored=False,
            first_author="Some Other",
            title="A paper",
        )
        self.assertIn("summary is not yet available", out.lower())


class ExtractTitleKeywordsTest(unittest.TestCase):
    def test_strips_stopwords(self):
        kw = bfw.extract_title_keywords("How much information can be extracted from galaxy clustering at the field level?")
        self.assertIn("information", kw)
        self.assertIn("galaxy", kw)
        self.assertIn("clustering", kw)
        self.assertIn("field", kw)
        self.assertNotIn("how", kw)  # stoplist
        self.assertNotIn("the", kw)
        self.assertNotIn("at", kw)

    def test_keeps_three_char_acronyms(self):
        kw = bfw.extract_title_keywords("The EFT Likelihood for Large-Scale Structure")
        self.assertIn("eft", kw)
        self.assertIn("likelihood", kw)
        self.assertIn("large-scale", kw)
        self.assertIn("structure", kw)

    def test_drops_one_and_two_char_tokens(self):
        # below MIN_TOKEN_LENGTH (3) — won't help the matcher.
        kw = bfw.extract_title_keywords("A B CD DESI study")
        self.assertNotIn("a", kw)
        self.assertNotIn("b", kw)
        self.assertNotIn("cd", kw)
        self.assertIn("desi", kw)

    def test_lowercases(self):
        kw = bfw.extract_title_keywords("DESI 2024 III: BAO from galaxies and quasars")
        self.assertEqual([k for k in kw if k != k.lower()], [])

    def test_preserves_hyphenated_terms_as_single_token(self):
        kw = bfw.extract_title_keywords("Field-level inference of large-scale structure")
        self.assertIn("field-level", kw)
        self.assertIn("large-scale", kw)


if __name__ == "__main__":
    unittest.main()
