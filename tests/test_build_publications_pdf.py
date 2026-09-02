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


def test_latex_escape_handles_reserved_characters() -> None:
    escaped = bpp.latex_escape("100% growth & bias_with #1 {test} $x$ " + chr(92))
    for token in (
        r"\%", r"\&", r"\_", r"\#", r"\{", r"\}",
        r"\$", r"\textbackslash{}",
    ):
        assert token in escaped


def test_render_latex_contains_summary_links_fallback_and_recognition() -> None:
    hits = (
        load_fixture("inspire_literature_page_1.json")["hits"]["hits"]
        + load_fixture("inspire_literature_page_2.json")["hits"]["hits"]
    )
    publications = bpp.normalize_publications(hits)
    source = bpp.render_latex(publications, bpp.compute_metrics(publications), generated_on="2026-09-02")
    assert "3 publications" in source
    assert "30 citations" in source
    assert "h-index 2" in source
    assert "Editors’ Suggestion" in source
    assert "Buchalter Cosmology Prize 2024" in source
    assert "arXiv:2403.03220" in source
    assert "INSPIRE record" in source
    assert "Generated from INSPIRE HEP on 2026-09-02" in source


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
