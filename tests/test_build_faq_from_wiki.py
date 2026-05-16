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


class BuildBucketEntryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # tiny fake records for the test buckets
        cls.records = {
            "SRC-0001": {"arxiv_id": "1611.09787", "title": "Large-Scale Galaxy Bias",
                         "authors": ["Vincent Desjacques"], "published_date": "2016-11-29"},
            "SRC-0020": {"arxiv_id": "2403.03220", "title": "How much information...",
                         "authors": ["Nhat-Minh Nguyen"], "published_date": "2024-03-05"},
            "SRC-0036": {"arxiv_id": "2604.25171",
                         "title": "Multi-tracers, multi-surveys: a joint Fisher analysis of DESI+PFS",
                         "authors": ["Nhat-Minh Nguyen"], "published_date": "2026-04-28"},
        }

    def test_shape(self):
        e = bfw.build_bucket_entry(
            "field-level-inference", ["SRC-0020"], self.records
        )
        self.assertEqual(e["id"], "wiki-bucket-field-level-inference")
        self.assertEqual(e["source"], "wiki")
        self.assertEqual(e["url"], "/research/")
        self.assertIsInstance(e["questions"], list)
        self.assertIsInstance(e["keywords"], list)
        self.assertIsInstance(e["answer"], str)

    def test_answer_mentions_papers(self):
        e = bfw.build_bucket_entry(
            "multi-tracer-fisher", ["SRC-0036"], self.records
        )
        self.assertIn("arXiv:2604.25171", e["answer"])

    def test_answer_caps_at_five_papers_with_overflow_note(self):
        many = {f"SRC-{i:04d}": {
            "arxiv_id": f"24{i:02d}.00000",
            "title": f"Paper {i}",
            "authors": ["Nhat-Minh Nguyen"],
            "published_date": f"2024-{i:02d}-01",
        } for i in range(1, 9)}
        e = bfw.build_bucket_entry(
            "field-level-inference", list(many.keys()), many
        )
        # at most 5 arxiv ids in the answer, plus an overflow note
        n_arxivs = e["answer"].count("arXiv:")
        self.assertLessEqual(n_arxivs, 5)
        self.assertIn("and ", e["answer"])
        self.assertIn("others", e["answer"])

    def test_unknown_bucket_raises(self):
        with self.assertRaises(KeyError):
            bfw.build_bucket_entry("nope-not-a-bucket", [], self.records)

    def test_unknown_src_in_bucket_raises(self):
        with self.assertRaises(KeyError) as ctx:
            bfw.build_bucket_entry(
                "field-level-inference", ["SRC-9999"], self.records
            )
        self.assertIn("SRC-9999", str(ctx.exception))


class BuildPerPaperEntryTest(unittest.TestCase):
    def setUp(self):
        self.records = bfw.load_wiki_records(FIXTURE_WIKI)
        for src_id, rec in self.records.items():
            page_path = FIXTURE_WIKI / rec["page_path"]
            rec["summary_body"] = bfw.extract_summary_body(page_path)

    def test_authored_paper_entry_shape(self):
        e = bfw.build_per_paper_entry(
            "SRC-0001", self.records["SRC-0001"], buckets_membership={"field-level-inference"}
        )
        self.assertEqual(e["id"], "wiki-2403-03220")
        self.assertEqual(e["source"], "wiki")
        self.assertEqual(e["arxiv_id"], "2403.03220")
        self.assertTrue(e["authored"])
        self.assertEqual(e["url"], "https://arxiv.org/abs/2403.03220")
        # three questions: title, arxiv-id, single-bucket flavor
        self.assertEqual(len(e["questions"]), 3)
        self.assertIn('Tell me about "How much information', e["questions"][0])
        self.assertEqual(e["questions"][1], "What is 2403.03220 about?")
        self.assertIn("field-level inference paper", e["questions"][2])
        # arxiv id and Nguyen in keywords
        self.assertIn("2403.03220", e["keywords"])
        self.assertIn("nguyen", [k.lower() for k in e["keywords"]])
        # answer uses authored prefix
        self.assertTrue(e["answer"].startswith("Minh and collaborators (arXiv:2403.03220):"))

    def test_unauthored_paper_entry(self):
        e = bfw.build_per_paper_entry(
            "SRC-0002", self.records["SRC-0002"], buckets_membership={"eft-bias-modeling"}
        )
        self.assertFalse(e["authored"])
        self.assertTrue(e["answer"].startswith("Desjacques et al. (arXiv:1611.09787):"))
        # not authored -> no "Nguyen" in keywords
        self.assertNotIn("nguyen", [k.lower() for k in e["keywords"]])

    def test_multi_bucket_paper_omits_third_question(self):
        e = bfw.build_per_paper_entry(
            "SRC-0001", self.records["SRC-0001"],
            buckets_membership={"field-level-inference", "eft-bias-modeling"},
        )
        # two questions only (title + arxiv-id)
        self.assertEqual(len(e["questions"]), 2)

    def test_failure_marker_paper_uses_fallback_answer(self):
        e = bfw.build_per_paper_entry(
            "SRC-0003", self.records["SRC-0003"], buckets_membership={"multi-tracer-fisher"}
        )
        self.assertIn("summary is not yet available", e["answer"].lower())

    def test_keyword_cap_is_twelve(self):
        e = bfw.build_per_paper_entry(
            "SRC-0001", self.records["SRC-0001"], buckets_membership={"field-level-inference"}
        )
        self.assertLessEqual(len(e["keywords"]), 12)


class MergeYamlTest(unittest.TestCase):
    def setUp(self):
        self.sample = (Path(__file__).parent / "fixtures" / "sample_research_bot.yaml").read_text()
        self.new_entries = [
            {
                "id": "wiki-1611-09787",
                "source": "wiki",
                "arxiv_id": "1611.09787",
                "authored": False,
                "questions": ["What is 1611.09787 about?"],
                "keywords": ["1611.09787", "EFT", "galaxy bias"],
                "answer": "Desjacques et al. (arXiv:1611.09787): example.",
                "url": "https://arxiv.org/abs/1611.09787",
            },
            {
                "id": "wiki-bucket-field-level-inference",
                "source": "wiki",
                "questions": ["Tell me about field-level inference"],
                "keywords": ["field-level inference", "LEFTfield"],
                "answer": "Minh works on FLI. arXiv:2403.03220.",
                "url": "/research/",
            },
        ]

    def test_preserves_hand_entries_in_order(self):
        merged_text = bfw.merge_yaml(existing_text=self.sample, new_entries=self.new_entries)
        idx_overview = merged_text.find("id: research-overview")
        idx_fli = merged_text.find("id: field-level-inference\n")
        idx_wiki = merged_text.find("id: wiki-")
        self.assertGreater(idx_overview, -1)
        self.assertGreater(idx_fli, -1)
        self.assertGreater(idx_wiki, -1)
        self.assertLess(idx_overview, idx_wiki)
        self.assertLess(idx_fli, idx_wiki)

    def test_drops_existing_source_wiki_entries(self):
        with_existing = self.sample + "\n- id: wiki-old-stale\n  source: wiki\n  questions: []\n  keywords: []\n  answer: stale\n"
        merged_text = bfw.merge_yaml(existing_text=with_existing, new_entries=self.new_entries)
        self.assertNotIn("wiki-old-stale", merged_text)
        self.assertIn("wiki-1611-09787", merged_text)

    def test_idempotent(self):
        merged1 = bfw.merge_yaml(existing_text=self.sample, new_entries=self.new_entries)
        merged2 = bfw.merge_yaml(existing_text=merged1, new_entries=self.new_entries)
        self.assertEqual(merged1, merged2)

    def test_per_paper_before_buckets(self):
        merged_text = bfw.merge_yaml(existing_text=self.sample, new_entries=self.new_entries)
        idx_paper = merged_text.find("id: wiki-1611-09787")
        idx_bucket = merged_text.find("id: wiki-bucket-field-level-inference")
        self.assertGreater(idx_paper, -1)
        self.assertGreater(idx_bucket, -1)
        self.assertLess(idx_paper, idx_bucket)


import tempfile
import shutil


class MainPipelineTest(unittest.TestCase):
    def _temp_repo(self) -> Path:
        """Create a tmp dir mirroring the data/ structure with the sample YAML."""
        repo = Path(tempfile.mkdtemp())
        (repo / "data").mkdir()
        src = Path(__file__).parent / "fixtures" / "sample_research_bot.yaml"
        shutil.copy(src, repo / "data" / "research_bot.yaml")
        return repo

    def test_main_writes_yaml_with_wiki_entries(self):
        repo = self._temp_repo()
        try:
            rc = bfw.main(
                ["--wiki", str(FIXTURE_WIKI), "--repo", str(repo)]
            )
            self.assertEqual(rc, 0)
            text = (repo / "data" / "research_bot.yaml").read_text()
            self.assertIn("wiki-2403-03220", text)
            self.assertIn("wiki-bucket-field-level-inference", text)
            self.assertIn("id: research-overview", text)  # hand entry preserved
        finally:
            shutil.rmtree(repo)

    def test_main_is_idempotent(self):
        repo = self._temp_repo()
        try:
            bfw.main(["--wiki", str(FIXTURE_WIKI), "--repo", str(repo)])
            text1 = (repo / "data" / "research_bot.yaml").read_text()
            bfw.main(["--wiki", str(FIXTURE_WIKI), "--repo", str(repo)])
            text2 = (repo / "data" / "research_bot.yaml").read_text()
            self.assertEqual(text1, text2)
        finally:
            shutil.rmtree(repo)

    def test_main_returns_3_on_missing_wiki(self):
        repo = self._temp_repo()
        try:
            rc = bfw.main(["--wiki", "/nonexistent/path", "--repo", str(repo)])
            self.assertEqual(rc, 3)
        finally:
            shutil.rmtree(repo)


if __name__ == "__main__":
    unittest.main()
