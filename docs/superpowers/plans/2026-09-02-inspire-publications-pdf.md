# INSPIRE Publications PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the landing biography's redundant actions with `CV` and `Publications`, and generate the linked publications PDF reproducibly from Nhat-Minh Nguyen's live INSPIRE profile.

**Architecture:** A single focused Python module will separate pure INSPIRE-record normalization, metrics, and LaTeX rendering from HTTP and PDF compilation side effects. Fixture-driven unit tests will exercise the pure layer and inject fake fetchers/compilers into the orchestration layer; the production command will fetch the public INSPIRE REST API, compile in a same-filesystem temporary directory, and atomically publish the finished PDF.

**Tech Stack:** Python 3 standard library, pytest/unittest-compatible tests, INSPIRE REST API JSON, LaTeX with `latexmk` + LuaLaTeX, Hugo/YAML.

---

## File Map

- Create `scripts/build_publications_pdf.py`: INSPIRE client, record normalization, metric calculation, LaTeX rendering, safe compilation, and CLI entry point.
- Create `tests/test_build_publications_pdf.py`: fixture-driven unit and orchestration tests with no live network calls.
- Create `tests/fixtures/inspire_author.json`: representative author record containing the INSPIRE BAI.
- Create `tests/fixtures/inspire_literature_page_1.json`: first representative literature page, including the two annotated PRLs and pagination.
- Create `tests/fixtures/inspire_literature_page_2.json`: final representative page, including a record without arXiv or citation count.
- Modify `tests/test_homepage.py`: assert the exact two-button landing-page contract.
- Modify `content/_index.md`: configure only `CV` and the local `Publications` PDF.
- Modify `README.md`: document prerequisites, regeneration command, output, and failure semantics.
- Create `static/publications/Nhat-Minh-Nguyen-publications.pdf`: generated, committed publication list served by Hugo.

### Task 1: Pure INSPIRE Data and LaTeX Renderer

**Files:**
- Create: `tests/fixtures/inspire_author.json`
- Create: `tests/fixtures/inspire_literature_page_1.json`
- Create: `tests/fixtures/inspire_literature_page_2.json`
- Create: `tests/test_build_publications_pdf.py`
- Create: `scripts/build_publications_pdf.py`

- [ ] **Step 1: Add representative API fixtures**

Create `tests/fixtures/inspire_author.json`:

```json
{
  "id": "1986925",
  "metadata": {
    "ids": [
      {"schema": "ORCID", "value": "0000-0002-2542-7233"},
      {"schema": "INSPIRE BAI", "value": "Nhat.Minh.Nguyen.1"}
    ]
  }
}
```

Create two literature responses with three total hits. Page 1 must contain DOI `10.1103/PhysRevLett.133.221006`, 20 citations, arXiv `2403.03220`, and DOI `10.1103/PhysRevLett.131.111001`, 10 citations, arXiv `2302.01331`; set `links.next` to `https://example.test/page-2`. Page 2 must contain a 2025 sole-authored record with title `A 100% test of growth & bias`, no `arxiv_eprints`, no `citation_count`, and no next link. Each hit must use the real INSPIRE response shape: `id`, then `metadata.titles`, `metadata.authors`, `metadata.earliest_date`, and optional `metadata.arxiv_eprints`, `metadata.dois`, and `metadata.citation_count`.

- [ ] **Step 2: Write failing tests for identity, pagination, normalization, and metrics**

Create `tests/test_build_publications_pdf.py` with path setup matching `tests/test_build_faq_from_wiki.py` and these tests:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))
import build_publications_pdf as bpp


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_resolve_bai() -> None:
    assert bpp.resolve_bai(load_fixture("inspire_author.json")) == "Nhat.Minh.Nguyen.1"


def test_resolve_bai_rejects_missing_id() -> None:
    with pytest.raises(bpp.GenerationError, match="INSPIRE BAI"):
        bpp.resolve_bai({"metadata": {"ids": []}})


def test_fetch_literature_follows_next_link() -> None:
    page_1 = load_fixture("inspire_literature_page_1.json")
    page_2 = load_fixture("inspire_literature_page_2.json")
    requested: list[str] = []

    def fake_fetch(url: str) -> dict:
        requested.append(url)
        return page_1 if len(requested) == 1 else page_2

    hits = bpp.fetch_literature("Nhat.Minh.Nguyen.1", fetch_json=fake_fetch)
    assert len(hits) == 3
    assert requested[1] == "https://example.test/page-2"
    assert "sort=mostrecent" in requested[0]
    assert "a+Nhat.Minh.Nguyen.1" in requested[0]


def test_normalize_orders_newest_first_and_adds_annotations() -> None:
    hits = (
        load_fixture("inspire_literature_page_1.json")["hits"]["hits"]
        + load_fixture("inspire_literature_page_2.json")["hits"]["hits"]
    )
    publications = bpp.normalize_publications(hits)
    assert [item.year for item in publications] == [2025, 2024, 2023]
    assert publications[0].arxiv_id is None
    by_doi = {item.doi: item for item in publications if item.doi}
    assert by_doi["10.1103/physrevlett.131.111001"].recognition == "Editors’ Suggestion"
    assert by_doi["10.1103/physrevlett.133.221006"].recognition == "Buchalter Cosmology Prize 2024"


def test_compute_metrics_uses_all_records_and_zero_fallback() -> None:
    hits = (
        load_fixture("inspire_literature_page_1.json")["hits"]["hits"]
        + load_fixture("inspire_literature_page_2.json")["hits"]["hits"]
    )
    metrics = bpp.compute_metrics(bpp.normalize_publications(hits))
    assert metrics == bpp.Metrics(publications=3, citations=30, h_index=2)
```

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_build_publications_pdf.py
```

Expected: collection fails with `ModuleNotFoundError: No module named 'build_publications_pdf'`.

- [ ] **Step 4: Implement the pure data layer**

Create `scripts/build_publications_pdf.py` with these exact public types and behaviors:

```python
"""Generate a publication-list PDF from Nhat-Minh Nguyen's INSPIRE profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode

AUTHOR_ID = "1986925"
AUTHOR_NAME = "Nhat-Minh Nguyen"
API_ROOT = "https://inspirehep.net/api"

RECOGNITION_BY_DOI = {
    "10.1103/physrevlett.131.111001": "Editors’ Suggestion",
    "10.1103/physrevlett.133.221006": "Buchalter Cosmology Prize 2024",
}


class GenerationError(RuntimeError):
    """Raised when INSPIRE data or PDF generation is unusable."""


@dataclass(frozen=True)
class Publication:
    record_id: str
    title: str
    author_count: int
    arxiv_id: str | None
    earliest_date: str
    citations: int
    doi: str | None
    recognition: str | None

    @property
    def record_url(self) -> str:
        return f"https://inspirehep.net/literature/{self.record_id}"

    @property
    def author_line(self) -> str:
        return AUTHOR_NAME if self.author_count == 1 else f"{AUTHOR_NAME} et al."

    @property
    def year(self) -> int:
        return int(self.earliest_date[:4])


@dataclass(frozen=True)
class Metrics:
    publications: int
    citations: int
    h_index: int


def resolve_bai(author_payload: dict) -> str:
    ids = author_payload.get("metadata", {}).get("ids", [])
    for identifier in ids:
        if identifier.get("schema") == "INSPIRE BAI" and identifier.get("value"):
            return str(identifier["value"])
    raise GenerationError("author record does not contain an INSPIRE BAI")


def literature_search_url(bai: str) -> str:
    query = urlencode(
        {
            "q": f"a {bai}",
            "sort": "mostrecent",
            "size": 250,
            "fields": (
                "titles,authors,arxiv_eprints,dois,earliest_date,"
                "citation_count"
            ),
        }
    )
    return f"{API_ROOT}/literature?{query}"


def fetch_literature(
    bai: str, *, fetch_json: Callable[[str], dict]
) -> list[dict]:
    url: str | None = literature_search_url(bai)
    records: list[dict] = []
    while url:
        payload = fetch_json(url)
        try:
            page = payload["hits"]["hits"]
        except (KeyError, TypeError) as exc:
            raise GenerationError("unexpected INSPIRE literature response") from exc
        if not isinstance(page, list):
            raise GenerationError("unexpected INSPIRE literature response")
        records.extend(page)
        next_url = payload.get("links", {}).get("next")
        url = str(next_url) if next_url else None
    if not records:
        raise GenerationError("INSPIRE returned no literature records")
    return records


def normalize_doi(value: object) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized or None


def normalize_publications(hits: list[dict]) -> list[Publication]:
    publications: list[Publication] = []
    for hit in hits:
        try:
            metadata = hit["metadata"]
            record_id = str(hit["id"])
            title = str(metadata["titles"][0]["title"])
            earliest_date = str(metadata["earliest_date"])
            int(earliest_date[:4])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationError("literature record lacks required metadata") from exc

        arxiv_entries = metadata.get("arxiv_eprints") or []
        arxiv_id = str(arxiv_entries[0]["value"]) if arxiv_entries else None
        doi_entries = metadata.get("dois") or []
        doi = normalize_doi(doi_entries[0].get("value")) if doi_entries else None
        citations = int(metadata.get("citation_count") or 0)
        author_count = len(metadata.get("authors") or [])
        publications.append(
            Publication(
                record_id=record_id,
                title=title,
                author_count=author_count,
                arxiv_id=arxiv_id,
                earliest_date=earliest_date,
                citations=citations,
                doi=doi,
                recognition=RECOGNITION_BY_DOI.get(doi or ""),
            )
        )

    return sorted(
        publications,
        key=lambda item: (item.earliest_date, int(item.record_id)),
        reverse=True,
    )


def compute_metrics(publications: list[Publication]) -> Metrics:
    counts = sorted((item.citations for item in publications), reverse=True)
    h_index = sum(count >= rank for rank, count in enumerate(counts, start=1))
    return Metrics(
        publications=len(publications),
        citations=sum(counts),
        h_index=h_index,
    )
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

Run the focused command from Step 3. Expected: all four tests pass.

- [ ] **Step 6: Add failing tests for LaTeX safety and approved content**

Append:

```python
def test_latex_escape_handles_reserved_characters() -> None:
    escaped = bpp.latex_escape(
        "100% growth & bias_with #1 {test} $x$ " + chr(92)
    )
    for token in (r"\%", r"\&", r"\_", r"\#", r"\{", r"\}", r"\$", r"\textbackslash{}"):
        assert token in escaped


def test_render_latex_contains_summary_links_fallback_and_recognition() -> None:
    hits = (
        load_fixture("inspire_literature_page_1.json")["hits"]["hits"]
        + load_fixture("inspire_literature_page_2.json")["hits"]["hits"]
    )
    publications = bpp.normalize_publications(hits)
    source = bpp.render_latex(
        publications,
        bpp.compute_metrics(publications),
        generated_on="2026-09-02",
    )
    assert "3 publications" in source
    assert "30 citations" in source
    assert "h-index 2" in source
    assert "Editors’ Suggestion" in source
    assert "Buchalter Cosmology Prize 2024" in source
    assert "arXiv:2403.03220" in source
    assert "INSPIRE record" in source
    assert "Generated from INSPIRE HEP on 2026-09-02" in source
```

- [ ] **Step 7: Run the new tests and verify RED**

Expected: failures because `latex_escape` and `render_latex` do not exist.

- [ ] **Step 8: Implement LaTeX escaping and the complete A4 renderer**

Add `latex_escape`, `citation_label`, and `render_latex`. Use a one-pass character mapping for `\`, `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, and `^`; do not run sequential replacements that can re-escape the LaTeX inserted for an earlier character. The renderer must emit a self-contained LuaLaTeX document using `article`, `geometry`, `fontspec`, `microtype`, `hyperref`, `xcolor`, `enumitem`, and `fancyhdr`; use a 19 mm margin, dark text, muted metadata, blue links, compact enumeration, and page numbers.

For every entry, emit the title as a link to `publication.record_url`, then the short author line, linked `arXiv:<id>` or linked `INSPIRE record`, year, and citation label. Emit the recognition on its own compact accent-colored line when present. The opening block must contain the exact live metrics format and `Generated from INSPIRE HEP on <date>` attribution.

The public signatures are:

```python
def latex_escape(value: object) -> str: ...

def citation_label(count: int) -> str:
    return f"{count:,} citation" if count == 1 else f"{count:,} citations"

def render_latex(
    publications: list[Publication], metrics: Metrics, *, generated_on: str
) -> str: ...
```

- [ ] **Step 9: Run all publication-generator tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_build_publications_pdf.py
```

Expected: all tests pass.

Commit:

```bash
git add scripts/build_publications_pdf.py tests/test_build_publications_pdf.py tests/fixtures/inspire_author.json tests/fixtures/inspire_literature_page_1.json tests/fixtures/inspire_literature_page_2.json
git commit -m "feat: render INSPIRE publications as LaTeX"
```

### Task 2: Safe Live PDF Generation Command

**Files:**
- Modify: `scripts/build_publications_pdf.py`
- Modify: `tests/test_build_publications_pdf.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for orchestration and output preservation**

Append tests using injected fakes:

```python
def fixture_fetcher(url: str) -> dict:
    if url.endswith("/authors/1986925"):
        return load_fixture("inspire_author.json")
    if "page-2" in url:
        return load_fixture("inspire_literature_page_2.json")
    return load_fixture("inspire_literature_page_1.json")


def test_generate_publications_pdf_atomically_publishes_result(tmp_path: Path) -> None:
    output = tmp_path / "publications.pdf"

    def fake_compiler(source: str, build_dir: Path) -> Path:
        assert "3 publications" in source
        compiled = build_dir / "publications.pdf"
        compiled.write_bytes(b"%PDF-1.7\nvalid")
        return compiled

    metrics = bpp.generate_publications_pdf(
        output,
        json_fetcher=fixture_fetcher,
        compiler=fake_compiler,
        generated_on="2026-09-02",
    )
    assert output.read_bytes() == b"%PDF-1.7\nvalid"
    assert metrics == bpp.Metrics(3, 30, 2)


def test_failed_compilation_preserves_existing_pdf(tmp_path: Path) -> None:
    output = tmp_path / "publications.pdf"
    output.write_bytes(b"old valid PDF")

    def failing_compiler(source: str, build_dir: Path) -> Path:
        raise bpp.GenerationError("LaTeX compilation failed")

    with pytest.raises(bpp.GenerationError, match="compilation failed"):
        bpp.generate_publications_pdf(
            output,
            json_fetcher=fixture_fetcher,
            compiler=failing_compiler,
            generated_on="2026-09-02",
        )
    assert output.read_bytes() == b"old valid PDF"
```

- [ ] **Step 2: Run the focused tests and verify RED**

Expected: `generate_publications_pdf` is missing.

- [ ] **Step 3: Implement HTTP, compilation, atomic publication, and CLI**

Add imports for `argparse`, `json`, `os`, `shutil`, `subprocess`, `sys`, `tempfile`, `date`, `Path`, `Request`, `urlopen`, and `HTTPError`/`URLError`.

Implement these signatures:

```python
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "static"
    / "publications"
    / "Nhat-Minh-Nguyen-publications.pdf"
)


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={"User-Agent": "minhmpa-homepage-publications/1.0"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GenerationError(f"could not fetch INSPIRE data: {exc}") from exc
    if not isinstance(payload, dict):
        raise GenerationError("INSPIRE returned a non-object JSON response")
    return payload


def compile_latex(source: str, build_dir: Path) -> Path:
    if shutil.which("latexmk") is None or shutil.which("lualatex") is None:
        raise GenerationError("latexmk and lualatex are required")
    tex_path = build_dir / "publications.tex"
    tex_path.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            "latexmk", "-lualatex", "-interaction=nonstopmode",
            "-halt-on-error", "publications.tex",
        ],
        cwd=build_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    pdf_path = build_dir / "publications.pdf"
    if result.returncode != 0 or not pdf_path.is_file():
        diagnostic = (result.stdout + result.stderr)[-4000:]
        raise GenerationError(f"LaTeX compilation failed:\n{diagnostic}")
    return pdf_path


def generate_publications_pdf(
    output: Path = DEFAULT_OUTPUT,
    *,
    json_fetcher: Callable[[str], dict] = fetch_json,
    compiler: Callable[[str, Path], Path] = compile_latex,
    generated_on: str | None = None,
) -> Metrics:
    author = json_fetcher(f"{API_ROOT}/authors/{AUTHOR_ID}")
    bai = resolve_bai(author)
    publications = normalize_publications(
        fetch_literature(bai, fetch_json=json_fetcher)
    )
    metrics = compute_metrics(publications)
    source = render_latex(
        publications,
        metrics,
        generated_on=generated_on or date.today().isoformat(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".publications-build-", dir=output.parent
    ) as temporary:
        compiled = compiler(source, Path(temporary))
        if not compiled.is_file():
            raise GenerationError("compiler did not produce a PDF")
        os.replace(compiled, output)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate Nhat-Minh Nguyen's INSPIRE publications PDF."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        metrics = generate_publications_pdf(args.output)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Wrote {args.output} ({metrics.publications} publications, "
        f"{metrics.citations} citations, h-index {metrics.h_index})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Keep the orchestration tests' injected `json_fetcher` keyword consistent with this signature.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Task 1 test command. Expected: all tests pass.

- [ ] **Step 5: Document the regeneration workflow**

Add `## Publications PDF` to `README.md` after `Local Build Check`:

````markdown
## Publications PDF

The landing-page publication list is generated from INSPIRE author record
`1986925`. Install `latexmk` and LuaLaTeX, then run:

```bash
python scripts/build_publications_pdf.py
```

The command refreshes
`static/publications/Nhat-Minh-Nguyen-publications.pdf`. It reports the live
publication, citation, and h-index totals. Generation happens in a temporary
directory, so a failed API request or LaTeX build leaves the last valid PDF
untouched.
````

- [ ] **Step 6: Run all Python tests and commit**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q
```

Expected: all tests pass.

Commit:

```bash
git add scripts/build_publications_pdf.py tests/test_build_publications_pdf.py README.md
git commit -m "feat: safely generate publications PDF"
```

### Task 3: Two-Button Homepage Contract

**Files:**
- Modify: `tests/test_homepage.py:154-181`
- Modify: `content/_index.md:15-27`

- [ ] **Step 1: Rewrite the homepage action test first**

Replace the current unordered four-action expectation with an ordered two-action assertion:

```python
def test_homepage_actions_and_target_behavior(homepage: ParsedHomePage) -> None:
    expected_actions = [
        ("CV", "/cv/Nhat-Minh-Nguyen-academic-cv.pdf"),
        (
            "Publications",
            "/publications/Nhat-Minh-Nguyen-publications.pdf",
        ),
    ]
    action_links = [
        link
        for link in homepage.links
        if "homepage-action"
        in str(link["attrs"].get("class", "")).split()
    ]

    assert [str(link["text"]) for link in action_links] == [
        label for label, _ in expected_actions
    ]
    assert "homepage-actions" in homepage.classes

    for link, (_, expected_href) in zip(action_links, expected_actions):
        attrs = link["attrs"]
        assert attrs["href"] == expected_href
        assert attrs["target"] == "_blank"
        assert "noopener" in str(attrs["rel"]).split()
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_homepage.py::test_homepage_actions_and_target_behavior
```

Expected: failure showing the old four labels.

- [ ] **Step 3: Configure exactly the approved two buttons**

Replace `content._index.md`'s `buttons` list with:

```yaml
      buttons:
        - text: CV
          url: /cv/Nhat-Minh-Nguyen-academic-cv.pdf
          new_tab: true
        - text: Publications
          url: /publications/Nhat-Minh-Nguyen-publications.pdf
          new_tab: true
```

Do not change navigation, biography, theme, background, spacing, interests/education flags, or the generic biography partial.

- [ ] **Step 4: Run homepage and full Python tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_homepage.py
PYTHONDONTWRITEBYTECODE=1 pytest -q
```

Expected: both commands pass.

- [ ] **Step 5: Commit**

```bash
git add content/_index.md tests/test_homepage.py
git commit -m "feat: focus homepage document actions"
```

### Task 4: Generate and Inspect the Live Publications PDF

**Files:**
- Create: `static/publications/Nhat-Minh-Nguyen-publications.pdf`

- [ ] **Step 1: Verify local build prerequisites**

Run:

```bash
command -v latexmk
command -v lualatex
```

Expected: both commands print executable paths. If either is missing, stop and report the exact missing prerequisite; do not substitute a different PDF pipeline.

- [ ] **Step 2: Run the generator against live INSPIRE data**

Run:

```bash
python scripts/build_publications_pdf.py
```

Expected: exit 0, an output line with current publication/citation/h-index values, and a valid file at `static/publications/Nhat-Minh-Nguyen-publications.pdf`.

- [ ] **Step 3: Verify PDF metadata and extractable content**

Run:

```bash
pdfinfo static/publications/Nhat-Minh-Nguyen-publications.pdf
pdftotext static/publications/Nhat-Minh-Nguyen-publications.pdf -
```

Expected: A4 page size; nonzero page count; title, live summary line, all publication entries, both recognition notes, arXiv labels, and the INSPIRE fallback for records without arXiv.

- [ ] **Step 4: Render and visually inspect every PDF page**

Use the session's PDF skill and Poppler rendering workflow. Inspect every page for clipping, overflow, broken glyphs, awkward page breaks, illegible links/metadata, and excessive whitespace. If layout changes are required, add a failing renderer assertion when applicable, update `render_latex`, rerun all generator tests, regenerate, and re-render before continuing.

- [ ] **Step 5: Commit the reviewed artifact**

```bash
git add static/publications/Nhat-Minh-Nguyen-publications.pdf
git commit -m "docs: add generated INSPIRE publications list"
```

### Task 5: Whole-Branch Verification and PR Update

**Files:**
- Verify only; modify files only to fix discovered failures.

- [ ] **Step 1: Run the complete automated suite**

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q
node --test tests/research-bot-matcher.test.mjs
```

Expected: zero failures.

- [ ] **Step 2: Run production and whitespace checks**

```bash
hugo --gc --minify
git diff --check master...HEAD
```

Expected: Hugo exits 0 and the diff check has no output.

- [ ] **Step 3: Verify generated-site targets**

Start a Hugo preview from this worktree and verify desktop and mobile landing views. Confirm the design is unchanged except for exactly two actions, both wrap correctly at narrow widths, `CV` opens the existing CV PDF, and `Publications` opens the generated PDF in a new tab.

- [ ] **Step 4: Review the final branch diff**

```bash
git status --short --branch
git log --oneline master..HEAD
git diff --stat master...HEAD
```

Expected: a clean worktree containing only the approved homepage, generator, tests, docs, design/plan, and generated PDF changes.

- [ ] **Step 5: Push the updated PR branch**

```bash
git push origin homepage-cleanup-plan
gh pr view 3 --json url,state,baseRefName,headRefName,mergeable,statusCheckRollup
```

Expected: PR #3 remains open against `master`, points to `homepage-cleanup-plan`, and contains the new commits.
