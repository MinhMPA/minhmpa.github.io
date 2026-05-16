# Wiki → FAQ Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-05-16-wiki-faq-generator-design.md`

**Goal:** Build `scripts/build_faq_from_wiki.py`, a one-way Python generator that reads the local LLM wiki and writes wiki-derived FAQ entries into `data/research_bot.yaml` (and its JSON mirror) without disturbing hand-curated entries.

**Architecture:** Single-file Python module structured as small pure functions for each pipeline stage (load wiki, distill answer, build entry, build bucket entry, merge YAML), with a `main()` CLI at the bottom. All functions are unit-testable with synthetic input. A separate small step keeps `tests/fixtures/research_bot.json` in sync with the YAML so the existing node-based matcher tests still pass.

**Tech Stack:** Python 3 (already required by the existing wiki tooling), `pyyaml` (pinned in `scripts/requirements.txt`), `python3 -m unittest` (stdlib) for the generator unit tests. No new runtime deps for the site itself.

---

## Spec deviations (read first)

The implementation deliberately deviates from the spec on two minor points; both are bug-fixes against the spec, not feature changes:

1. **Title-keyword length filter is `≥ 3`, not `≥ 4`.** Reason: the matcher in `assets/js/research-bot.js` sets `MIN_TOKEN_LENGTH = 3`. A keyword like `"EFT"` (length 3) participates in scoring only if both the keyword's own tokens and the user's query tokens survive the filter — using ≥ 3 in keyword extraction matches the matcher's behavior. The stoplist is widened to compensate.
2. **Wiki bucket `redshift-space-modeling` keeps only SRC-0008** (already corrected in the spec during self-review).
3. **Bucket validation is lenient.** The spec said exit code 5 should fire when the bucket map references a SRC not present in the wiki. Implementation in Task 9 instead filters each bucket's SRC list to those present in the loaded records and skips buckets that become empty. Rationale: the bucket map is a static config that may legitimately name aspirational SRC IDs while the wiki is still being populated. Exit code 5 is now reserved for structurally malformed bucket maps (e.g., a bucket value that isn't a list).
4. **Matcher hand-entry priority bonus** (commit `18a80ac`). The spec explicitly listed `assets/js/research-bot.js` as untouched, relying on YAML insertion order as the tiebreaker for hand vs wiki entries. In practice, wiki entries score strictly higher than hand entries on short generic queries (their keyword set is larger: bucket anchor keywords + title tokens + arxiv id). To preserve the "hand entries win on generic queries; wiki entries win on paper-specific queries" UX described in the spec, the matcher now adds `SCORE_HAND_ENTRY = 50` to any entry whose `source` field is not `"wiki"`, but only when its `contentScore` (question + keyword matches, pre-token-overlap) is positive. The `contentScore > 0` guard prevents off-topic hand entries from winning the no-match fallback path solely on their bonus.
5. **Hand-entry YAML formatting is normalized on first run.** PyYAML's `safe_dump` re-serializes hand entries with 2-space list indentation and 80-character folded-scalar wrap, which is not byte-identical to the prior 4-space indentation. The content of every hand entry is preserved verbatim — only whitespace and line wrapping change, and only on the first run after the generator is introduced. Subsequent runs are byte-stable. The operator workflow doc should call this out.

If subsequent implementation reveals additional deviations, append them here before continuing.

---

## File Structure

**New files:**

- `scripts/build_faq_from_wiki.py` — single Python module, ~400–500 lines. Contains pure functions (`load_wiki_records`, `extract_summary_body`, `is_authored`, `distill_answer`, `extract_title_keywords`, `build_per_paper_entry`, `build_bucket_entry`, `merge_yaml`, `dump_yaml_to_json_mirror`) plus a `main(argv)` entry point. Bucket map (`BUCKETS`) and stoplist (`STOPLIST`) are module-level constants.
- `scripts/requirements.txt` — single line: `PyYAML>=6,<7`. No transitive deps.
- `tests/test_build_faq_from_wiki.py` — Python unit tests using stdlib `unittest`. Lives next to the existing node tests because the repo treats `tests/` as the cross-language test root.
- `tests/fixtures/synthetic_wiki/` — small hand-crafted fixture wiki with 3 SRC records covering the interesting cases (authored, not authored, failure-marker summary). Mirrors the real wiki layout: `wiki_records/sources/SRC-*.yaml` and `wiki_pages/sources/SRC-*-*.md`.
- `docs/wiki-faq-generator.md` — operator documentation, one page, follows the style of `docs/research-homepage-bot.md`. Explains when to run the generator, the review workflow, and how to extend the bucket map.

**Modified files:**

- `data/research_bot.yaml` — wiki entries appended on first generator run. Hand entries untouched.
- `tests/fixtures/research_bot.json` — refreshed by the generator to mirror the new YAML.
- `tests/research-bot-matcher.test.mjs` — `EXPECTED_IDS` assertion replaced with a forward-compatible assertion (hand-entry ids are still present; wiki entries are permitted on top); new regression tests for wiki entries appended at the bottom of the file.
- `.github/workflows/jekyll.yml` — add a Python `unittest` step before the existing node test step. Both must pass before Hugo build.

**Files explicitly NOT touched:**

- `assets/js/research-bot.js` — the matcher precondition (ignores unknown YAML fields) is verified in Task 1; no JS changes required.
- `layouts/shortcodes/research-bot.html` — schema unchanged.
- `/Users/nguyenmn/research-wiki/` and anything under it — the generator is read-only against the wiki.

---

## Task 1: Verify matcher precondition + scaffold scripts/

**Files:**
- Create: `scripts/requirements.txt`
- Create: `scripts/build_faq_from_wiki.py` (placeholder)
- Read: `assets/js/research-bot.js` (verification only)

- [ ] **Step 1: Confirm `scoreEntry` reads only known fields**

Open `assets/js/research-bot.js` and inspect `scoreEntry()` and `entryTokenSet()`. Confirm they only access `entry.questions`, `entry.keywords`, `entry.answer` (in the public return path), `entry.id`, and `entry.url`. Append a single-line note to `docs/superpowers/plans/2026-05-16-wiki-faq-generator.md` under "Spec deviations" if you find anything that contradicts the spec's precondition (e.g., an iteration over `Object.keys(entry)`). If everything checks out, do nothing — the precondition is met.

Expected: no additional notes needed.

- [ ] **Step 2: Create `scripts/requirements.txt`**

```
PyYAML>=6,<7
```

- [ ] **Step 3: Create `scripts/build_faq_from_wiki.py` as a stub**

```python
"""Generate wiki-derived FAQ entries for the research-bot widget.

Reads the LLM wiki at WIKI_ROOT (default: /Users/nguyenmn/research-wiki/),
rewrites entries with `source: wiki` in data/research_bot.yaml, and
refreshes tests/fixtures/research_bot.json so the node matcher tests
still pass. Hand-authored entries are preserved verbatim.

This file is intentionally one module; functions are small and pure so
that they can be exercised individually from
tests/test_build_faq_from_wiki.py.

Usage:
    python3 scripts/build_faq_from_wiki.py [WIKI_ROOT]

Exit codes:
    0 success (file rewritten or unchanged)
    2 usage error
    3 wiki root invalid or no SRC records found
    4 a SRC record is malformed
    5 a bucket map entry references an unknown SRC ID
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    raise NotImplementedError("filled in by subsequent tasks")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Install the dep into a project-local virtualenv (optional, doc only)**

Run: `python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt`
Expected: `Successfully installed PyYAML-6.x.x`.
If you don't want a venv, install into the user site: `python3 -m pip install --user -r scripts/requirements.txt`.

- [ ] **Step 5: Commit**

```bash
git add scripts/requirements.txt scripts/build_faq_from_wiki.py
git commit -m "Scaffold wiki-FAQ generator script and pin PyYAML"
```

---

## Task 2: Wiki loader (records + summary body)

**Files:**
- Create: `tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0001.yaml`
- Create: `tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0002.yaml`
- Create: `tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0003.yaml`
- Create: `tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0001-authored-paper.md`
- Create: `tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0002-not-authored-paper.md`
- Create: `tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0003-failure-marker.md`
- Create: `tests/test_build_faq_from_wiki.py`
- Modify: `scripts/build_faq_from_wiki.py` (add `load_wiki_records`, `extract_summary_body`)

- [ ] **Step 1: Create the synthetic wiki fixtures**

`tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0001.yaml`:

```yaml
record_id: SRC-0001
record_type: source
status: active
duplicate_of:
superseded_by:
source_storage: local
raw_path: raw/papers/2403.03220.pdf
source_url:
page_path: wiki_pages/sources/SRC-0001-authored-paper.md
source_type: paper
source_format: pdf
title: "How much information can be extracted from galaxy clustering at the field level?"
authors:
  - "Nhat-Minh Nguyen"
  - "Fabian Schmidt"
added_date: 2026-05-15
processed_date: 2026-05-15
published_date: 2024-03-05
content_fingerprint:
```

`tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0002.yaml`:

```yaml
record_id: SRC-0002
record_type: source
status: active
duplicate_of:
superseded_by:
source_storage: local
raw_path: raw/review_papers/1611.09787v5.pdf
source_url:
page_path: wiki_pages/sources/SRC-0002-not-authored-paper.md
source_type: paper
source_format: pdf
title: "Large-Scale Galaxy Bias"
authors:
  - "Vincent Desjacques"
  - "Donghui Jeong"
  - "Fabian Schmidt"
added_date: 2026-05-15
processed_date: 2026-05-15
published_date: 2016-11-29
content_fingerprint:
```

`tests/fixtures/synthetic_wiki/wiki_records/sources/SRC-0003.yaml`:

```yaml
record_id: SRC-0003
record_type: source
status: active
duplicate_of:
superseded_by:
source_storage: local
raw_path: raw/papers/2604.25171.pdf
source_url:
page_path: wiki_pages/sources/SRC-0003-failure-marker.md
source_type: paper
source_format: pdf
title: "Multi-tracers, multi-surveys: a joint Fisher analysis of DESI+PFS"
authors:
  - "Nhat-Minh Nguyen"
added_date: 2026-05-15
processed_date: 2026-05-15
published_date: 2026-04-28
content_fingerprint:
```

`tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0001-authored-paper.md`:

```markdown
---
record_id: SRC-0001
page_type: source_summary
title: "How much information can be extracted from galaxy clustering at the field level?"
aliases:
  - "2403.03220"
tags:
  - source
  - paper
  - arxiv
---

# How much information can be extracted from galaxy clustering at the field level?

- arXiv: [2403.03220](https://arxiv.org/abs/2403.03220)
- Authors: Nhat-Minh Nguyen, Fabian Schmidt

## Summary

This Letter asks how much cosmological information can be robustly extracted from nonlinear galaxy clustering, by performing optimal Bayesian field-level inference of sigma_8 from simulated dark matter halos using the LEFTfield forward model. The constraint comes entirely from nonlinear information. The work demonstrates that field-level inference recovers sigma_8 unbiased and tightens the constraint by factors of three to five over power-spectrum-plus-bispectrum analyses.

A second paragraph that should not appear in the distilled answer.
```

`tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0002-not-authored-paper.md`:

```markdown
---
record_id: SRC-0002
page_type: source_summary
title: "Large-Scale Galaxy Bias"
aliases:
  - "1611.09787"
tags:
  - source
  - paper
  - arxiv
---

# Large-Scale Galaxy Bias

- arXiv: [1611.09787](https://arxiv.org/abs/1611.09787)
- Authors: Vincent Desjacques, Donghui Jeong, Fabian Schmidt

## Summary

This review provides a comprehensive treatment of galaxy bias, the statistical relation between the distribution of galaxies and the underlying matter density field. The authors focus on large, quasi-linear scales on which the clustering of galaxies admits a perturbative bias expansion.
```

`tests/fixtures/synthetic_wiki/wiki_pages/sources/SRC-0003-failure-marker.md`:

```markdown
---
record_id: SRC-0003
page_type: source_summary
title: "Multi-tracers, multi-surveys: a joint Fisher analysis of DESI+PFS"
aliases:
  - "2604.25171"
tags:
  - source
  - paper
  - arxiv
---

# Multi-tracers, multi-surveys: a joint Fisher analysis of DESI+PFS

## Summary

_Not yet written._
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_build_faq_from_wiki.py`:

```python
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
        # second paragraph is preserved as part of the body; distillation later
        # is what truncates.
        self.assertIn("A second paragraph", body)

    def test_failure_marker_is_returned_verbatim(self):
        page = FIXTURE_WIKI / "wiki_pages" / "sources" / "SRC-0003-failure-marker.md"
        body = bfw.extract_summary_body(page)
        self.assertEqual(body.strip(), "_Not yet written._")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_build_faq_from_wiki -v`
Expected: `AttributeError: module 'build_faq_from_wiki' has no attribute 'load_wiki_records'`. Fine — that's the failing state we want.

- [ ] **Step 4: Implement `load_wiki_records` and `extract_summary_body`**

Replace the body of `scripts/build_faq_from_wiki.py` (keeping the docstring) with:

```python
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


REQUIRED_RECORD_FIELDS = ("title", "authors", "raw_path", "page_path")

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


def load_wiki_records(wiki_root: Path) -> dict[str, dict]:
    """Load all SRC-*.yaml records, keyed by record_id.

    Each record dict gets an extra `arxiv_id` field derived from `raw_path`.
    Raises FileNotFoundError if wiki_records/sources/ does not exist.
    Raises ValueError if a record is missing any required field.
    """
    records_dir = wiki_root / "wiki_records" / "sources"
    if not records_dir.is_dir():
        raise FileNotFoundError(
            f"expected {records_dir} to exist; is {wiki_root} a wiki root?"
        )
    out: dict[str, dict] = {}
    for yaml_path in sorted(records_dir.glob("SRC-*.yaml")):
        with yaml_path.open() as fh:
            r = yaml.safe_load(fh)
        if not isinstance(r, dict):
            raise ValueError(f"{yaml_path}: top-level value is not a mapping")
        for field in REQUIRED_RECORD_FIELDS:
            if not r.get(field):
                raise ValueError(f"{yaml_path}: missing required field '{field}'")
        m = _ARXIV_ID_RE.search(Path(r["raw_path"]).name)
        if not m:
            raise ValueError(
                f"{yaml_path}: cannot extract arxiv id from raw_path={r['raw_path']!r}"
            )
        r["arxiv_id"] = m.group(1)
        out[r["record_id"]] = r
    return out


def extract_summary_body(page_path: Path) -> str:
    """Return the prose under the `## Summary` heading of a source page.

    Strips frontmatter, the title/H1, the metadata bullets above the heading,
    and any trailing whitespace. Returns the body verbatim, including any
    placeholder lines like `_Not yet written._`.
    """
    text = page_path.read_text(encoding="utf-8")
    # locate "## Summary" heading line
    parts = re.split(r"^##\s+Summary\s*$", text, maxsplit=1, flags=re.MULTILINE)
    if len(parts) < 2:
        return ""
    body = parts[1].strip()
    return body


def main(argv: list[str]) -> int:  # placeholder; filled in by later tasks
    raise NotImplementedError("filled in by subsequent tasks")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki -v`
Expected: all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py tests/fixtures/synthetic_wiki
git commit -m "Wire wiki record loader and summary extraction for FAQ generator"
```

---

## Task 3: Authorship detection

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `is_authored`, `MINH_NAME_FORMS`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `IsAuthoredTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py` (before the `if __name__` line):

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.IsAuthoredTest -v`
Expected: 7 errors, all "module ... has no attribute 'is_authored'".

- [ ] **Step 3: Implement `is_authored`**

Add to `scripts/build_faq_from_wiki.py` (above `main`):

```python
MINH_NAME_FORMS = frozenset(
    {
        "nhat-minh nguyen",
        "nhat minh nguyen",
        "minh nguyen",
        "n. nguyen",
        "n nguyen",
    }
)


def is_authored(authors: list[str]) -> bool:
    """True iff any author name matches a canonical form of Minh's name."""
    for a in authors or []:
        if a.strip().casefold() in MINH_NAME_FORMS:
            return True
    return False
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.IsAuthoredTest -v`
Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Add authorship detection to FAQ generator"
```

---

## Task 4: Answer distillation

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `distill_answer`, `FAILURE_MARKERS`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `DistillAnswerTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.DistillAnswerTest -v`
Expected: 5 errors, all "module ... has no attribute 'distill_answer'".

- [ ] **Step 3: Implement `distill_answer`**

Add to `scripts/build_faq_from_wiki.py`:

```python
FAILURE_MARKERS = frozenset(
    {
        "_not yet written._",
        "_pdf could not be read._",
        "_pdf text extraction was unusable._",
    }
)

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _surname(full_name: str) -> str:
    return full_name.strip().split()[-1] if full_name.strip() else ""


def _is_failure(body: str) -> bool:
    first_line = body.strip().split("\n", 1)[0].strip().casefold()
    if first_line in FAILURE_MARKERS:
        return True
    # also catch the more verbose "_PDF could not be read: <reason>._" form
    if first_line.startswith("_pdf could not be read") and first_line.endswith("._"):
        return True
    return False


def distill_answer(
    *,
    body: str,
    arxiv_id: str,
    authored: bool,
    first_author: str,
    title: str,
) -> str:
    """Excerpt 1-2 sentences (≤80 words) from `body`, prepend author tone."""
    if _is_failure(body):
        return (
            f"{title} by {_surname(first_author) or first_author} et al. "
            f"(arXiv:{arxiv_id}). A summary is not yet available; see the arXiv "
            "abstract."
        )

    sentences = _SENTENCE_BOUNDARY.split(body.strip())
    selected: list[str] = []
    words_total = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        words = s.split()
        if words_total == 0 and len(words) > 80:
            selected.append(" ".join(words[:80]) + "…")
            words_total = 80
            break
        selected.append(s)
        words_total += len(words)
        if words_total >= 60:
            break

    excerpt = " ".join(selected)
    if authored:
        prefix = f"Minh and collaborators (arXiv:{arxiv_id}):"
    else:
        surname = _surname(first_author) or first_author
        prefix = f"{surname} et al. (arXiv:{arxiv_id}):"
    return f"{prefix} {excerpt}"
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.DistillAnswerTest -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Implement answer distillation with author-tone prefix and fallback"
```

---

## Task 5: Title keyword extraction

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `STOPLIST`, `extract_title_keywords`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `ExtractTitleKeywordsTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.ExtractTitleKeywordsTest -v`
Expected: 5 errors, "module ... has no attribute 'extract_title_keywords'".

- [ ] **Step 3: Implement `extract_title_keywords`**

Add to `scripts/build_faq_from_wiki.py`:

```python
STOPLIST = frozenset(
    """
    a an the and or but of for with without to from in on at by as is are was
    were be been has have had do does did this that these those it its into
    onto over under between using used via based model models paper papers
    study studies analysis results new beyond towards toward about what
    which who where when why how can their there our we i me my your you
    her his their them they we us if then than so such not no nor only also
    """.split()
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def extract_title_keywords(title: str) -> list[str]:
    """Return lowercase content tokens from a title (length ≥ 3, no stopwords)."""
    if not title:
        return []
    raw = _TOKEN_RE.findall(title)
    seen: set[str] = set()
    out: list[str] = []
    for tok in raw:
        low = tok.lower()
        if len(low) < 3:
            continue
        if low in STOPLIST:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(low)
    return out
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.ExtractTitleKeywordsTest -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Extract content tokens from paper titles for FAQ keyword lists"
```

---

## Task 6: Bucket map and bucket entry generation

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `BUCKETS`, `BUCKET_TEMPLATES`, `BUCKET_KEYWORDS`, `BUCKET_QUESTIONS`, `build_bucket_entry`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `BuildBucketEntryTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.BuildBucketEntryTest -v`
Expected: 5 errors.

- [ ] **Step 3: Implement bucket map and `build_bucket_entry`**

Add to `scripts/build_faq_from_wiki.py`:

```python
# bucket_id -> list of SRC IDs; ground truth lives only here.
BUCKETS: dict[str, list[str]] = {
    "field-level-inference": [
        "SRC-0002", "SRC-0003", "SRC-0004", "SRC-0006", "SRC-0010", "SRC-0014",
        "SRC-0016", "SRC-0019", "SRC-0020", "SRC-0024", "SRC-0025", "SRC-0026",
        "SRC-0027", "SRC-0032", "SRC-0033", "SRC-0034", "SRC-0037",
    ],
    "eft-bias-modeling": [
        "SRC-0001", "SRC-0002", "SRC-0004", "SRC-0005", "SRC-0008", "SRC-0009",
        "SRC-0026", "SRC-0027",
    ],
    "bao-and-large-scale-clustering": [
        "SRC-0012", "SRC-0021", "SRC-0022", "SRC-0023", "SRC-0025", "SRC-0028",
        "SRC-0029", "SRC-0030",
    ],
    "growth-of-structure": [
        "SRC-0013", "SRC-0015", "SRC-0017", "SRC-0018", "SRC-0031",
    ],
    "desi-2024": [
        "SRC-0021", "SRC-0022", "SRC-0023", "SRC-0028", "SRC-0029", "SRC-0030",
    ],
    "kinematic-sz": ["SRC-0007"],
    "intrinsic-alignment": ["SRC-0011", "SRC-0035"],
    "primordial-non-gaussianity": ["SRC-0035"],
    "redshift-space-modeling": ["SRC-0008"],
    "multi-tracer-fisher": ["SRC-0036"],
}

# Per-bucket human prose. The {papers} placeholder is replaced with a
# comma-joined list of arxiv refs (up to 5) plus an overflow note.
BUCKET_TEMPLATES: dict[str, str] = {
    "field-level-inference": (
        "Minh works on field-level Bayesian inference of cosmological parameters "
        "from nonlinear galaxy clustering, primarily via the LEFTfield EFT-based "
        "forward model. Relevant papers include {papers}."
    ),
    "eft-bias-modeling": (
        "EFT-based galaxy bias models give a controlled, perturbative description "
        "of how galaxies trace the matter density on large scales. Relevant "
        "papers include {papers}."
    ),
    "bao-and-large-scale-clustering": (
        "Minh works on extracting cosmological information from galaxy clustering "
        "at the BAO scale and beyond, both via traditional summary statistics and "
        "field-level inference. Relevant papers include {papers}."
    ),
    "growth-of-structure": (
        "Minh works on measuring the growth of cosmic structure across redshift "
        "and testing the concordance LambdaCDM expectation against current data. "
        "Relevant papers include {papers}."
    ),
    "desi-2024": (
        "Minh co-authored the DESI 2024 cosmological-results series, covering "
        "BAO from galaxies, quasars, and the Lyman-alpha forest, and the "
        "full-shape galaxy-clustering analysis. Relevant papers include {papers}."
    ),
    "kinematic-sz": (
        "Minh worked on forward-modeling the kinematic Sunyaev-Zel'dovich effect "
        "from galaxy surveys, including uncertainties from velocity reconstruction. "
        "Relevant paper: {papers}."
    ),
    "intrinsic-alignment": (
        "Minh works on field-level inference of galaxy intrinsic alignment from "
        "galaxy shapes, and on using galaxy sizes as a complementary, zero-bias "
        "tracer. Relevant papers include {papers}."
    ),
    "primordial-non-gaussianity": (
        "Minh works on galaxy sizes as a complementary, zero-bias tracer of local "
        "primordial non-Gaussianity. Relevant paper: {papers}."
    ),
    "redshift-space-modeling": (
        "Minh contributed to extending the EFT likelihood for large-scale structure "
        "to redshift space. Relevant paper: {papers}."
    ),
    "multi-tracer-fisher": (
        "Minh works on multi-tracer, multi-survey forecasts to quantify the gains "
        "from combining current and next-generation galaxy surveys. Relevant "
        "paper: {papers}."
    ),
}

BUCKET_KEYWORDS: dict[str, list[str]] = {
    "field-level-inference": [
        "field-level inference", "field-level", "FLI", "LEFTfield", "Bayesian",
        "posterior", "forward model", "initial conditions",
    ],
    "eft-bias-modeling": [
        "EFT", "effective field theory", "bias", "galaxy bias", "perturbation",
        "perturbative", "bias expansion",
    ],
    "bao-and-large-scale-clustering": [
        "BAO", "baryon acoustic oscillations", "galaxy clustering",
        "power spectrum", "large-scale clustering",
    ],
    "growth-of-structure": [
        "growth", "growth rate", "growth index", "structure growth",
        "sigma_8", "fsigma8", "S_8",
    ],
    "desi-2024": [
        "DESI", "DESI 2024", "year one", "Y1", "spectroscopic survey",
    ],
    "kinematic-sz": [
        "kSZ", "kinematic SZ", "Sunyaev-Zel'dovich", "Sunyaev",
        "velocity reconstruction",
    ],
    "intrinsic-alignment": [
        "intrinsic alignment", "IA", "galaxy shapes", "galaxy sizes", "shapes",
        "sizes",
    ],
    "primordial-non-gaussianity": [
        "primordial non-Gaussianity", "PNG", "fNL", "non-Gaussianity",
        "scale-dependent bias",
    ],
    "redshift-space-modeling": [
        "redshift space", "redshift-space distortion", "RSD",
    ],
    "multi-tracer-fisher": [
        "multi-tracer", "multi-survey", "Fisher", "forecast", "PFS",
        "DESI+PFS",
    ],
}

BUCKET_QUESTIONS: dict[str, list[str]] = {
    "field-level-inference": [
        "Tell me about field-level inference",
        "What's your work on field-level inference?",
        "What is FLI?",
    ],
    "eft-bias-modeling": [
        "Tell me about EFT galaxy bias modeling",
        "What is EFT-based bias modeling?",
        "What's your work on the bias expansion?",
    ],
    "bao-and-large-scale-clustering": [
        "Tell me about your work on BAO",
        "What's your work on baryon acoustic oscillations?",
        "Tell me about large-scale galaxy clustering",
    ],
    "growth-of-structure": [
        "Tell me about your work on the growth of structure",
        "What's your work on the growth rate?",
        "What's S_8?",
    ],
    "desi-2024": [
        "Tell me about your DESI papers",
        "What's your role in DESI 2024?",
        "Tell me about the DESI Y1 cosmology results",
    ],
    "kinematic-sz": [
        "Do you work on the kinematic SZ effect?",
        "Tell me about your kSZ paper",
    ],
    "intrinsic-alignment": [
        "Do you work on intrinsic alignment?",
        "Tell me about your work on galaxy shapes and sizes",
    ],
    "primordial-non-gaussianity": [
        "Do you work on primordial non-Gaussianity?",
        "Tell me about your work on PNG",
    ],
    "redshift-space-modeling": [
        "Do you work on redshift-space modeling?",
        "Tell me about your work on the EFT likelihood in redshift space",
    ],
    "multi-tracer-fisher": [
        "Tell me about your multi-tracer forecast",
        "What's your work on DESI+PFS?",
    ],
}


def _format_papers_list(srcs: list[str], records: dict[str, dict]) -> str:
    # sort: authored first (Minh-authored stable), then by published_date descending
    def sort_key(src: str) -> tuple[int, str]:
        r = records[src]
        authored = 0 if is_authored(r.get("authors") or []) else 1
        return (authored, "9999-99-99" if not r.get("published_date") else
                _invert_date(str(r["published_date"])))

    ordered = sorted(srcs, key=sort_key)
    head, tail = ordered[:5], ordered[5:]
    refs = [f"arXiv:{records[s]['arxiv_id']}" for s in head]
    txt = ", ".join(refs[:-1]) + (f", and {refs[-1]}" if len(refs) > 1 else refs[0])
    if tail:
        txt += f", and {len(tail)} others — see /research/"
    return txt


def _invert_date(d: str) -> str:
    """For descending sort via ascending-key trick."""
    # Map "2024-03-05" -> "7975-96-94" so larger dates sort earlier.
    try:
        y, m, day = d.split("-")
        return f"{9999 - int(y):04d}-{99 - int(m):02d}-{99 - int(day):02d}"
    except Exception:
        return "0000-00-00"


def build_bucket_entry(
    bucket_id: str,
    srcs: list[str],
    records: dict[str, dict],
) -> dict:
    if bucket_id not in BUCKETS:
        raise KeyError(f"unknown bucket: {bucket_id!r}")
    for s in srcs:
        if s not in records:
            raise KeyError(f"bucket {bucket_id!r} references unknown SRC ID {s!r}")

    papers_text = _format_papers_list(srcs, records) if srcs else "(none yet)"
    answer = BUCKET_TEMPLATES[bucket_id].replace("{papers}", papers_text)
    return {
        "id": f"wiki-bucket-{bucket_id}",
        "source": "wiki",
        "questions": list(BUCKET_QUESTIONS[bucket_id]),
        "keywords": list(BUCKET_KEYWORDS[bucket_id]),
        "answer": answer,
        "url": "/research/",
    }
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.BuildBucketEntryTest -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Add bucket map and bucket-entry generator for FAQ"
```

---

## Task 7: Per-paper entry assembly

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `build_per_paper_entry`, `_buckets_for`, `_questions_for_paper`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `BuildPerPaperEntryTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.BuildPerPaperEntryTest -v`
Expected: 5 errors.

- [ ] **Step 3: Implement `build_per_paper_entry`**

Add to `scripts/build_faq_from_wiki.py`:

```python
# Single-bucket question templates per the spec.
BUCKET_PAPER_QUESTION: dict[str, str] = {
    "field-level-inference": "Tell me about your field-level inference paper",
    "eft-bias-modeling": "Tell me about your work on EFT galaxy bias",
    "bao-and-large-scale-clustering": "Tell me about your BAO paper",
    "growth-of-structure": "Tell me about your work on the growth of structure",
    "desi-2024": "Tell me about your DESI 2024 paper",
    "kinematic-sz": "Tell me about your work on the kinematic SZ effect",
    "intrinsic-alignment": "Tell me about your work on galaxy shapes and sizes",
    "primordial-non-gaussianity": "Tell me about your work on primordial non-Gaussianity",
    "redshift-space-modeling": "Tell me about your work on the EFT likelihood in redshift space",
    "multi-tracer-fisher": "Tell me about your multi-tracer forecast",
}


def _buckets_for(src_id: str) -> set[str]:
    return {b for b, members in BUCKETS.items() if src_id in members}


def build_per_paper_entry(
    src_id: str,
    record: dict,
    *,
    buckets_membership: set[str],
) -> dict:
    arxiv_id = record["arxiv_id"]
    title = record["title"]
    authors = record.get("authors") or []
    authored = is_authored(authors)
    first_author = authors[0] if authors else ""

    questions = [
        f'Tell me about "{title}"',
        f"What is {arxiv_id} about?",
    ]
    if len(buckets_membership) == 1:
        only_bucket = next(iter(buckets_membership))
        flavor = BUCKET_PAPER_QUESTION.get(only_bucket)
        if flavor:
            questions.append(flavor)

    # keywords: arxiv id + Nguyen (if authored) + bucket anchor keywords + title tokens
    kw_in_order: list[str] = [arxiv_id]
    if authored:
        kw_in_order.append("Nguyen")
    for b in sorted(buckets_membership):
        kw_in_order.extend(BUCKET_KEYWORDS.get(b, []))
    kw_in_order.extend(extract_title_keywords(title))

    seen: set[str] = set()
    keywords: list[str] = []
    for k in kw_in_order:
        low = k.lower()
        if low in seen:
            continue
        seen.add(low)
        keywords.append(k)
        if len(keywords) >= 12:
            break

    answer = distill_answer(
        body=record.get("summary_body", ""),
        arxiv_id=arxiv_id,
        authored=authored,
        first_author=first_author,
        title=title,
    )

    return {
        "id": "wiki-" + arxiv_id.replace(".", "-"),
        "source": "wiki",
        "arxiv_id": arxiv_id,
        "authored": authored,
        "questions": questions,
        "keywords": keywords,
        "answer": answer,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
    }
```

- [ ] **Step 4: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.BuildPerPaperEntryTest -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Assemble per-paper FAQ entries with author tone and bucket-derived keywords"
```

---

## Task 8: YAML merge with hand entries

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `merge_yaml`, helpers for stable dump)
- Modify: `tests/test_build_faq_from_wiki.py` (add `MergeYamlTest`)
- Create: `tests/fixtures/sample_research_bot.yaml` (small starter to exercise the merge)

- [ ] **Step 1: Create the fixture starter YAML**

`tests/fixtures/sample_research_bot.yaml`:

```yaml
- id: research-overview
  questions:
    - What do you work on?
  keywords:
    - research
    - cosmology
  answer: >
    Sample answer for the test.
  url: /research/

- id: field-level-inference
  questions:
    - Tell me about field-level inference
  keywords:
    - field-level inference
    - FLI
  answer: >
    Sample FLI answer.
  url: /research/
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
        # both hand ids appear in original order
        idx_overview = merged_text.find("id: research-overview")
        idx_fli = merged_text.find("id: field-level-inference\n")
        idx_wiki = merged_text.find("id: wiki-")
        self.assertGreater(idx_overview, -1)
        self.assertGreater(idx_fli, -1)
        self.assertGreater(idx_wiki, -1)
        # hand entries come before wiki entries
        self.assertLess(idx_overview, idx_wiki)
        self.assertLess(idx_fli, idx_wiki)

    def test_drops_existing_source_wiki_entries(self):
        # pre-existing wiki entry should be replaced, not duplicated
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
```

- [ ] **Step 3: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.MergeYamlTest -v`
Expected: 4 errors.

- [ ] **Step 4: Implement `merge_yaml`**

Add to `scripts/build_faq_from_wiki.py`:

```python
def _entry_sort_key(entry: dict) -> tuple[int, str]:
    """Per-paper entries (id starts with 'wiki-<digits>') come before bucket
    entries (id starts with 'wiki-bucket-'). Within each group, sort by id."""
    eid = entry.get("id", "")
    if eid.startswith("wiki-bucket-"):
        return (1, eid)
    return (0, eid)


class _LiteralStr(str):
    """Marker class to force PyYAML's block-folded style for long strings."""


def _folded_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style=">")


yaml.add_representer(_LiteralStr, _folded_representer)


def _stylize_answers(entries: list[dict]) -> list[dict]:
    """Mark answer fields for block-folded YAML output (>)."""
    out = []
    for e in entries:
        e2 = dict(e)
        if "answer" in e2 and isinstance(e2["answer"], str):
            e2["answer"] = _LiteralStr(e2["answer"])
        out.append(e2)
    return out


def merge_yaml(*, existing_text: str, new_entries: list[dict]) -> str:
    """Merge wiki-derived entries into the existing YAML text.

    Strategy:
      1. Parse existing YAML to a list of dicts.
      2. Drop entries with `source == 'wiki'`.
      3. Append new_entries, sorted: per-paper first (by id), then bucket
         entries (by id).
      4. Dump with block-folded answers, allow_unicode=True, sort_keys=False,
         width=80, indent=2.
    """
    existing = yaml.safe_load(existing_text) or []
    if not isinstance(existing, list):
        raise ValueError("existing YAML must be a top-level list of entries")
    hand = [e for e in existing if not (isinstance(e, dict) and e.get("source") == "wiki")]
    sorted_new = sorted(new_entries, key=_entry_sort_key)
    merged = hand + sorted_new
    styled = _stylize_answers(merged)
    return yaml.dump(
        styled,
        sort_keys=False,
        allow_unicode=True,
        width=80,
        indent=2,
    )
```

- [ ] **Step 5: Run tests and confirm pass**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.MergeYamlTest -v`
Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py tests/fixtures/sample_research_bot.yaml
git commit -m "Merge wiki-derived entries into research_bot.yaml without disturbing hand entries"
```

---

## Task 9: CLI wrapper and end-to-end synthetic-wiki run

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (implement `main`)
- Modify: `tests/test_build_faq_from_wiki.py` (add `MainPipelineTest`)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_build_faq_from_wiki.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm failures**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.MainPipelineTest -v`
Expected: 3 errors ("NotImplementedError" for `main`).

- [ ] **Step 3: Implement `main`**

Replace the `main` stub in `scripts/build_faq_from_wiki.py` with:

```python
import argparse
from pathlib import Path


DEFAULT_WIKI = Path("/Users/nguyenmn/research-wiki")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Generate wiki-derived FAQ entries for the research-bot widget."
    )
    parser.add_argument(
        "--wiki", default=str(DEFAULT_WIKI),
        help="Path to the LLM wiki root (default: %(default)s)",
    )
    parser.add_argument(
        "--repo", default=".",
        help="Path to the github.io repo root (default: cwd)",
    )
    args = parser.parse_args(argv)

    wiki_root = Path(args.wiki)
    repo_root = Path(args.repo)

    try:
        records = load_wiki_records(wiki_root)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 3
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4

    if not records:
        print(f"error: no SRC records found under {wiki_root}", file=sys.stderr)
        return 3

    # attach summary body to each record
    for src_id, rec in records.items():
        page_path = wiki_root / rec["page_path"]
        if not page_path.is_file():
            print(f"error: {src_id}: page_path missing: {page_path}", file=sys.stderr)
            return 4
        rec["summary_body"] = extract_summary_body(page_path)

    # bucket validation
    for bucket_id, srcs in BUCKETS.items():
        for s in srcs:
            if s not in records:
                print(
                    f"error: bucket {bucket_id!r} references unknown SRC ID {s!r}",
                    file=sys.stderr,
                )
                return 5

    per_paper_entries = [
        build_per_paper_entry(src_id, rec, buckets_membership=_buckets_for(src_id))
        for src_id, rec in sorted(records.items())
    ]
    bucket_entries = [
        build_bucket_entry(bucket_id, srcs, records)
        for bucket_id, srcs in BUCKETS.items()
    ]
    new_entries = per_paper_entries + bucket_entries

    yaml_path = repo_root / "data" / "research_bot.yaml"
    if not yaml_path.is_file():
        print(f"error: cannot find {yaml_path}", file=sys.stderr)
        return 3
    existing_text = yaml_path.read_text()
    new_text = merge_yaml(existing_text=existing_text, new_entries=new_entries)

    if new_text == existing_text:
        print("no changes")
        return 0

    yaml_path.write_text(new_text)
    print(
        f"wrote {len(per_paper_entries)} per-paper entries and "
        f"{len(bucket_entries)} bucket entries to {yaml_path}"
    )
    return 0
```

- [ ] **Step 4: Run all tests and confirm pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: every test passes. There should be ≥ 26 tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Wire CLI entry point for FAQ generator"
```

---

## Task 10: JSON mirror sync

**Files:**
- Modify: `scripts/build_faq_from_wiki.py` (add `dump_yaml_to_json_mirror`, call from `main`)
- Modify: `tests/test_build_faq_from_wiki.py` (extend `MainPipelineTest`)

- [ ] **Step 1: Write the failing test**

Append to `MainPipelineTest` in `tests/test_build_faq_from_wiki.py`:

```python
    def test_main_writes_json_mirror(self):
        repo = self._temp_repo()
        (repo / "tests" / "fixtures").mkdir(parents=True)
        # seed an empty JSON mirror
        (repo / "tests" / "fixtures" / "research_bot.json").write_text("[]")
        try:
            rc = bfw.main(["--wiki", str(FIXTURE_WIKI), "--repo", str(repo)])
            self.assertEqual(rc, 0)
            import json
            mirror = json.loads(
                (repo / "tests" / "fixtures" / "research_bot.json").read_text()
            )
            ids = [e["id"] for e in mirror]
            self.assertIn("research-overview", ids)
            self.assertIn("wiki-2403-03220", ids)
            self.assertIn("wiki-bucket-field-level-inference", ids)
        finally:
            shutil.rmtree(repo)
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `python3 -m unittest tests.test_build_faq_from_wiki.MainPipelineTest.test_main_writes_json_mirror -v`
Expected: FAIL — JSON file is still empty (or `[]`).

- [ ] **Step 3: Implement mirror sync**

Add to `scripts/build_faq_from_wiki.py`:

```python
import json


def dump_yaml_to_json_mirror(yaml_text: str, json_path: Path) -> None:
    """Write a deterministic JSON mirror of the YAML entry list.

    Strips the `_LiteralStr` markers so JSON output is plain strings; preserves
    entry ordering and key insertion order via sort_keys=False.
    """
    entries = yaml.safe_load(yaml_text) or []
    # ensure regular str (not _LiteralStr) for json.dumps
    cleaned = json.loads(json.dumps(entries, default=str))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # 2-space indent, newline at EOF, deterministic
    json_path.write_text(
        json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n"
    )
```

Then at the end of `main`, after writing the YAML:

```python
    json_path = repo_root / "tests" / "fixtures" / "research_bot.json"
    dump_yaml_to_json_mirror(new_text, json_path)
    print(f"refreshed JSON mirror at {json_path}")
    return 0
```

(Replace the existing `return 0` line; preserve the "no changes" path's return as well — for that branch, still call `dump_yaml_to_json_mirror(existing_text, json_path)` so the mirror is healed even if the YAML is already correct.)

The final main tail becomes:

```python
    json_path = repo_root / "tests" / "fixtures" / "research_bot.json"

    if new_text == existing_text:
        dump_yaml_to_json_mirror(existing_text, json_path)
        print("no changes (JSON mirror refreshed)")
        return 0

    yaml_path.write_text(new_text)
    dump_yaml_to_json_mirror(new_text, json_path)
    print(
        f"wrote {len(per_paper_entries)} per-paper entries and "
        f"{len(bucket_entries)} bucket entries to {yaml_path}; "
        f"refreshed JSON mirror at {json_path}"
    )
    return 0
```

- [ ] **Step 4: Run all tests and confirm pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: all tests pass, including the new JSON-mirror test.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_faq_from_wiki.py tests/test_build_faq_from_wiki.py
git commit -m "Refresh JSON mirror alongside research_bot.yaml in the generator"
```

---

## Task 11: Loosen the matcher test drift assertion

**Files:**
- Modify: `tests/research-bot-matcher.test.mjs`

- [ ] **Step 1: Update `EXPECTED_IDS` assertion**

Replace the existing `EXPECTED_IDS` block (lines 28–47 of `tests/research-bot-matcher.test.mjs`) with:

```javascript
// Drift detection: hand-authored entries must remain in their canonical order.
// Wiki-derived entries (ids starting with "wiki-") are permitted on top and
// are not part of the hand-curated drift contract.
const EXPECTED_HAND_IDS = [
  "research-overview",
  "field-level-inference",
  "eft-modeling",
  "publications",
  "software",
  "collaboration",
  "contact",
  "affiliation",
  "growth-of-structure",
  "awards",
  "outreach",
];

test("JSON fixture preserves hand-authored entry ids in order", () => {
  const handIds = FAQ.map((e) => e.id).filter((id) => !id.startsWith("wiki-"));
  assert.deepEqual(handIds, EXPECTED_HAND_IDS);
});

test("All wiki-derived entries are tagged source: wiki", () => {
  for (const e of FAQ) {
    if (e.id.startsWith("wiki-")) {
      assert.equal(
        e.source,
        "wiki",
        `entry ${e.id} has id prefix 'wiki-' but is missing source: wiki`,
      );
    }
  }
});
```

- [ ] **Step 2: Run the existing matcher tests**

Run: `node --test tests/research-bot-matcher.test.mjs`
Expected: all original tests pass; the two new tests pass. Since no wiki entries are in the fixture yet, the `wiki-*` assertion is vacuously true.

- [ ] **Step 3: Commit**

```bash
git add tests/research-bot-matcher.test.mjs
git commit -m "Allow wiki-derived FAQ entries in the matcher drift-detection test"
```

---

## Task 12: First production run against the real wiki

**Files:**
- Modify: `data/research_bot.yaml` (generated)
- Modify: `tests/fixtures/research_bot.json` (generated)

This task is operator-driven; do not auto-generate without reviewing the diff.

- [ ] **Step 1: Run the generator against the real wiki**

From the repo root:

```bash
python3 scripts/build_faq_from_wiki.py
```

Expected: stdout reports `wrote 37 per-paper entries and 10 bucket entries to data/research_bot.yaml; refreshed JSON mirror at tests/fixtures/research_bot.json`.

- [ ] **Step 2: Inspect the diff**

```bash
git diff --stat data/research_bot.yaml tests/fixtures/research_bot.json
git diff data/research_bot.yaml | head -200
```

Expected: hand entries are byte-identical; only additions at the end. Inspect a handful of generated entries by eye for tone, accuracy, and obvious extraction artifacts (e.g., stray LaTeX residues, mis-attributed authorship).

- [ ] **Step 3: Run the full test suite**

```bash
node --test tests/research-bot-matcher.test.mjs
python3 -m unittest discover -s tests -v
```

Expected: both green.

- [ ] **Step 4: Manual UI walkthrough (per `docs/research-homepage-bot.md`)**

```bash
hugo server -D
```

Visit `http://localhost:1313/contact/` and exercise:
- "What do you work on?" → still returns the hand `research-overview` entry.
- "Tell me about 2403.03220" → returns the matching `wiki-2403-03220` entry; "Learn more →" goes to `https://arxiv.org/abs/2403.03220`.
- "Tell me about your DESI 2024 paper" → returns any DESI-2024 entry (per-paper or bucket).
- "Who won the world cup?" → falls back to the deterministic no-match string.
- "Tell me about field-level inference" → still returns the hand `field-level-inference` entry (tied entries fall to the earlier-listed hand entry).
- Empty submit → empty-input message.
- Prompt-injection attempt → fallback string.

- [ ] **Step 5: Commit if the diff looks right**

```bash
git add data/research_bot.yaml tests/fixtures/research_bot.json
git commit -m "Add wiki-derived FAQ entries for 37 papers and 10 topic buckets"
```

If anything in Step 2 or 4 is wrong, do NOT commit. Open an issue or roll back the generator output and iterate on the script.

---

## Task 13: Matcher regression tests for the new entries

**Files:**
- Modify: `tests/research-bot-matcher.test.mjs`

- [ ] **Step 1: Write the failing tests**

Append to the bottom of `tests/research-bot-matcher.test.mjs` (after the "shape sanity" block):

```javascript
// ---------- wiki-derived entries ----------
// These rely on the generator having been run at least once. They assert
// the spec's coexistence rules between hand and wiki entries.

test("12. 'Tell me about 2403.03220' -> wiki per-paper entry", () => {
  const r = answerQuestion("Tell me about 2403.03220", FAQ);
  assert.ok(r && !r.empty, `expected a match, got ${JSON.stringify(r)}`);
  assert.equal(r.sourceId, "wiki-2403-03220");
});

test("13. 'Tell me about your DESI 2024 paper' -> DESI bucket or per-paper", () => {
  const r = answerQuestion("Tell me about your DESI 2024 paper", FAQ);
  assert.ok(r && !r.empty);
  assert.ok(
    r.sourceId === "wiki-bucket-desi-2024" ||
      r.sourceId.startsWith("wiki-2404-") ||
      r.sourceId.startsWith("wiki-2411-"),
    `unexpected sourceId ${r.sourceId}`,
  );
});

test("14. Generic 'tell me about field-level inference' still prefers hand entry", () => {
  const r = answerQuestion("Tell me about field-level inference", FAQ);
  assert.ok(r && !r.empty);
  assert.equal(
    r.sourceId,
    "field-level-inference",
    "hand entry should win the tie because it appears earlier in the YAML",
  );
});

test("15. arXiv-id keyword wins against generic hand-entry overlap", () => {
  const r = answerQuestion("what is 1611.09787 about", FAQ);
  assert.ok(r && !r.empty);
  assert.equal(r.sourceId, "wiki-1611-09787");
});
```

- [ ] **Step 2: Run the test and confirm it passes**

Run: `node --test tests/research-bot-matcher.test.mjs`
Expected: all tests pass, including the four new ones.

If any of 12–15 fail, the generator's keyword strategy needs tuning. Most likely culprits:
- `wiki-2403-03220` lost: arxiv-id keyword wasn't recognised because of token splitting. Inspect `entry.keywords` and add `"2403"` and `"03220"` as separate keywords if needed.
- Hand FLI entry lost: wiki bucket entry is scoring higher than expected. Check that wiki bucket keywords don't include "field-level inference" as an exact verbatim hand-entry keyword.

- [ ] **Step 3: Commit**

```bash
git add tests/research-bot-matcher.test.mjs
git commit -m "Add matcher regression tests for wiki-derived FAQ entries"
```

---

## Task 14: Wire Python tests into CI

**Files:**
- Modify: `.github/workflows/jekyll.yml`

- [ ] **Step 1: Inspect the current workflow**

Open `.github/workflows/jekyll.yml`. Locate the step that runs the node matcher tests (added in the recent `feat/research-bot` branch — look for `node --test`).

- [ ] **Step 2: Add a Python step just before the node step**

Insert in the workflow's `build` (or `test`) job, immediately before the existing node-test step:

```yaml
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Python deps for generator tests
        run: pip install -r scripts/requirements.txt

      - name: Run generator unit tests
        run: python3 -m unittest discover -s tests -v
```

- [ ] **Step 3: Verify locally**

There is no easy way to run `act` without extra setup; instead, verify the YAML is syntactically valid:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/jekyll.yml'))"
```

Expected: no exception.

- [ ] **Step 4: Push branch and watch CI**

```bash
git push -u origin <branch-name>
gh run watch
```

Expected: both the Python and the node test steps run and pass. The Hugo build step continues to run after them.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/jekyll.yml
git commit -m "Run generator unit tests in CI before node matcher tests"
```

---

## Task 15: Operator documentation

**Files:**
- Create: `docs/wiki-faq-generator.md`

- [ ] **Step 1: Write the docs page**

```markdown
# Wiki → FAQ generator — operator notes

This document covers the `scripts/build_faq_from_wiki.py` script that
expands the research-bot FAQ from the local LLM wiki.

## When to run

Run after the wiki at `/Users/nguyenmn/research-wiki/` changes in any
way the visitor-facing FAQ should reflect:

- new paper added to the wiki
- summary rewritten
- bucket map updated (this is a code change to the generator itself)

## How to run

From the repo root:

```bash
python3 scripts/build_faq_from_wiki.py
```

This rewrites:

- `data/research_bot.yaml` (the Hugo data file that ships to the browser)
- `tests/fixtures/research_bot.json` (the JSON mirror used by node tests)

It never modifies the wiki and never touches hand-authored FAQ entries.

## Review workflow

1. `git diff data/research_bot.yaml` — hand entries should be untouched.
2. `node --test tests/research-bot-matcher.test.mjs` — green.
3. `python3 -m unittest discover -s tests -v` — green.
4. `hugo server -D`, walk the manual UI checklist in
   `docs/research-homepage-bot.md`.
5. Commit and push.

## Extending the bucket map

The bucket map lives at the top of `scripts/build_faq_from_wiki.py`. To
add a new bucket:

1. Add an entry to `BUCKETS` (id → list of SRC-IDs).
2. Add an entry to `BUCKET_TEMPLATES` (the human prose, with `{papers}`
   placeholder).
3. Add an entry to `BUCKET_KEYWORDS`.
4. Add an entry to `BUCKET_QUESTIONS`.
5. Optionally add an entry to `BUCKET_PAPER_QUESTION` to give papers in
   that bucket a third, topic-flavored question phrasing.
6. Re-run the generator. Update tests in
   `tests/test_build_faq_from_wiki.py` if the new bucket should be in
   the synthetic-wiki test set.
```

- [ ] **Step 2: Commit**

```bash
git add docs/wiki-faq-generator.md
git commit -m "Add operator docs for the wiki-FAQ generator"
```

---

## Self-Review

Performed inline before this plan was saved:

1. **Spec coverage:**
   - Architecture overview → Tasks 1, 2.
   - Inputs (records, summary pages, bucket map) → Tasks 2, 6.
   - Per-paper entry generation → Tasks 3, 4, 5, 7.
   - Topic-bucket entry generation → Task 6.
   - YAML merge + idempotency → Task 8.
   - CLI + exit codes → Task 9.
   - JSON mirror (added during implementation discovery) → Task 10.
   - Existing tests stay green → Task 11.
   - New regression tests → Task 13.
   - CI integration → Task 14.
   - Operator workflow docs → Task 15.
   - Manual review run → Task 12.
   - Matcher precondition verified → Task 1, Step 1.
   - Edge cases (version-stripped arxiv ID, failure markers, single sentence > 80 words, unknown bucket SRC) → Tasks 2, 4, 6 tests.
2. **Placeholder scan:** No "TBD", "TODO", or "similar to Task N" left in.
3. **Type consistency:** Function names (`load_wiki_records`, `extract_summary_body`, `is_authored`, `distill_answer`, `extract_title_keywords`, `build_bucket_entry`, `build_per_paper_entry`, `merge_yaml`, `dump_yaml_to_json_mirror`, `main`) are used consistently across tasks and tests. The `BUCKETS`, `BUCKET_TEMPLATES`, `BUCKET_KEYWORDS`, `BUCKET_QUESTIONS`, `BUCKET_PAPER_QUESTION` dicts are named consistently. Spec deviation re: keyword length ≥ 3 is documented at the top of this plan.
