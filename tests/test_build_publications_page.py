"""Bibliographic completeness, citation transitions, and failure preservation."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_publications_page as page


def paper(record_id="1"):
    return {
        "id": record_id,
        "metadata": {
            "titles": [{"title": "Constraining $f_{\\rm NL}$ with galaxy clustering"}],
            "authors": [
                {"full_name": "Yu, Author"},
                {"full_name": "Nguyen, Nhat-Minh", "record": {"$ref": f"{page.API_ROOT}/authors/{page.AUTHOR_ID}"}},
            ],
            "earliest_date": "2026-07-01",
            "arxiv_eprints": [{"value": "2607.01314"}],
        },
    }


def test_preprint_becomes_journal_reference_without_changing_author_order():
    record = paper()
    preprint = page.render_page([record], "2026-11-18")
    assert "Yu, **Nguyen**." in preprint
    assert "[arXiv preprint](https://arxiv.org/abs/2607.01314), 2026." in preprint
    assert "f\\_NL" in preprint
    record["metadata"].update({
        "dois": [{"value": "10.1234/example"}],
        "publication_info": [{"journal_title": "Phys.Rev.D", "journal_volume": "115", "artid": "123456", "year": 2027}],
    })
    published = page.render_page([record], "2027-01-01")
    assert "Yu, **Nguyen**." in published
    assert "[Phys. Rev. D 115, 123456, 2027](https://doi.org/10.1234/example)" in published
    assert "[arXiv preprint]" not in published


def test_jcap_citation_uses_issue_and_publication_year():
    metadata = paper()["metadata"]
    metadata.update({
        "dois": [{"value": "10.1088/1475-7516/2025/07/028"}],
        "publication_info": [{"journal_title": "JCAP", "journal_volume": "2025", "journal_issue": "07", "artid": "028", "year": 2025}],
    })
    assert "[JCAP 07, 028, 2025]" in page.reference(metadata, "2024")[0]


def test_collaboration_and_small_group_citations():
    metadata = paper()["metadata"]
    assert page.authors(metadata) == "Yu, **Nguyen**"
    metadata["collaborations"] = [{"value": "DESI"}]
    assert page.authors(metadata) == "DESI Collaboration"
    metadata["collaborations"] = [{"value": "Beyond-2point Collaboration"}]
    assert page.authors(metadata) == "Beyond-2point Collaboration"


def test_wrong_nguyen_is_not_highlighted():
    assert not page.is_author({"full_name": "Nguyen, Nhat-Minh", "record": {"$ref": f"{page.API_ROOT}/authors/1"}})


def test_fetches_every_page_and_validates_total():
    first, second = paper(), paper("2")
    payloads = [
        {"metadata": {"ids": [{"schema": "INSPIRE BAI", "value": "Nhat.Minh.Nguyen.1"}]}},
        {"hits": {"total": 2, "hits": [first]}, "links": {"next": f"{page.API_ROOT}/literature?page=2"}},
        {"hits": {"total": {"value": 2, "relation": "eq"}, "hits": [second]}},
    ]
    urls = []
    def fetch(url):
        urls.append(url)
        return payloads[len(urls) - 1]
    assert page.fetch_records(fetch) == [first, second]
    assert "a+Nhat.Minh.Nguyen.1" in urls[1]
    assert urls[-1].endswith("page=2")
    payloads[1]["links"] = {}
    urls.clear()
    with pytest.raises(page.GenerationError, match="incomplete"):
        page.fetch_records(fetch)


def test_duplicate_and_empty_lists_are_rejected():
    with pytest.raises(page.GenerationError):
        page.render_page([paper(), paper()], "2026-11-18")
    with pytest.raises(page.GenerationError):
        page.render_page([], "2026-11-18")


def test_newest_first_and_literal_title():
    earlier = paper("9")
    earlier["metadata"]["earliest_date"] = "2024-01-01"
    newer = paper("10")
    newer["metadata"]["titles"][0]["title"] = "Galaxy [sizes](https://example.org) <script>alert(1)</script>"
    rendered = page.render_page([earlier, newer], "2026-11-18")
    assert "1. Yu, **Nguyen**. “Galaxy \\[sizes\\]" in rendered
    assert "<script>" not in rendered
    assert "All 2 works" in rendered


@pytest.mark.parametrize("failure", ["network", "metadata"])
def test_failed_refresh_preserves_existing_page(tmp_path, monkeypatch, failure):
    destination = tmp_path / "index.md"
    destination.write_text("last complete list")
    def fetch():
        if failure == "network":
            raise page.GenerationError("connection refused")
        broken = deepcopy(paper())
        del broken["metadata"]["arxiv_eprints"]
        return [broken]
    monkeypatch.setattr(page, "fetch_records", fetch)
    monkeypatch.setattr(sys, "argv", ["refresh", "--output", str(destination)])
    assert page.main() == 1
    assert destination.read_text() == "last complete list"


def test_snapshot_roundtrip(tmp_path, monkeypatch):
    source, output = tmp_path / "source.json", tmp_path / "index.md"
    source.write_text(json.dumps({"author_id": page.AUTHOR_ID, "updated": "2026-11-18", "records": [paper()]}))
    monkeypatch.setattr(sys, "argv", ["refresh", "--from-snapshot", str(source), "--output", str(output)])
    assert page.main() == 0
    assert "Updated 2026-11-18" in output.read_text()


def test_erratum_does_not_replace_original_journal_article():
    metadata = paper()["metadata"]
    metadata.update({
        "dois": [{"value": "10.1234/erratum", "material": "erratum"}, {"value": "10.1234/article"}],
        "publication_info": [
            {"journal_title": "Phys.Rev.D", "material": "erratum", "artid": "099999", "year": 2027},
            {"journal_title": "Phys.Rev.D", "journal_volume": "114", "artid": "123456", "year": 2026},
        ],
    })
    citation, doi = page.reference(metadata, "2026")
    assert "114, 123456, 2026" in citation
    assert doi == "10.1234/article"
