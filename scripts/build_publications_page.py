"""Refresh the CV-style publication page from the complete INSPIRE author list."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import quote, urlencode, urlparse

from build_publications_pdf import (
    API_ROOT, AUTHOR_ID, GenerationError, RECOGNITION_BY_DOI,
    fetch_json, normalize_doi, plain_title, resolve_bai,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "content/publications/index.md"
PROFILE_URL = f"https://inspirehep.net/authors/{AUTHOR_ID}?ui-citation-summary=true"
FIELDS = (
    "titles,authors.full_name,authors.record,collaborations,publication_info,"
    "dois,arxiv_eprints,earliest_date"
)
JOURNALS = {
    "Phys.Rev.Lett.": "Phys. Rev. Lett.",
    "Phys.Rev.D": "Phys. Rev. D",
    "Astrophys.J.": "ApJ",
    "Astrophys.J.Lett.": "ApJL",
    "Mon.Not.Roy.Astron.Soc.": "MNRAS",
    "Astron.Astrophys.": "A&A",
    "SciPost Phys.Lect.Notes": "SciPost Physics Lecture Notes",
}


def request_json(url: str) -> dict:
    """Retry transient service failures, without accepting partial responses."""
    for attempt in range(3):
        try:
            return fetch_json(url)
        except (GenerationError, OSError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def fetch_records(fetch=request_json) -> list[dict]:
    bai = resolve_bai(fetch(f"{API_ROOT}/authors/{AUTHOR_ID}"))
    url = f"{API_ROOT}/literature?" + urlencode({
        "q": f"a {bai}", "sort": "mostrecent", "size": 250, "fields": FIELDS,
    })
    records, visited, expected = [], set(), None
    while url:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "inspirehep.net":
            raise GenerationError("unexpected INSPIRE pagination URL")
        if url in visited:
            raise GenerationError("INSPIRE pagination repeated a page")
        visited.add(url)
        payload = fetch(url)
        try:
            page = payload["hits"]["hits"]
            total = payload["hits"]["total"]
            if isinstance(total, dict):
                if total.get("relation", "eq") != "eq":
                    raise GenerationError("INSPIRE did not return an exact total")
                total = total["value"]
            if not isinstance(page, list) or not isinstance(total, int):
                raise ValueError("invalid hit count")
        except (KeyError, TypeError, ValueError) as exc:
            raise GenerationError("unexpected INSPIRE literature response") from exc
        if expected is not None and expected != total:
            raise GenerationError("INSPIRE total changed during retrieval; retry")
        expected = total
        records.extend(page)
        url = payload.get("links", {}).get("next")
    if not records or len(records) != expected:
        raise GenerationError("INSPIRE returned an empty or incomplete publication list")
    return records


def text(value: object) -> str:
    """Keep catalog text literal in Markdown and prevent embedded HTML."""
    value = " ".join(plain_title(value).split())
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", value)


def is_author(author: dict) -> bool:
    ref = author.get("record", {}).get("$ref", "").rstrip("/")
    if ref:
        return ref == f"{API_ROOT}/authors/{AUTHOR_ID}"
    name = author.get("full_name", "").lower().replace("-", " ")
    return name in {"nguyen, nhat minh", "nhat minh nguyen"}


def authors(metadata: dict) -> str:
    collaborations = [text(c["value"]) for c in metadata.get("collaborations", [])]
    if collaborations:
        return ", ".join(
            c if "collaboration" in c.lower() else f"{c} Collaboration"
            for c in collaborations
        )
    names = metadata.get("authors") or []
    if not names or any(not a.get("full_name") for a in names):
        raise GenerationError("publication lacks author names")
    shown = names
    if len(names) > 5:
        shown = names[:2] if len(names) > 1 and is_author(names[1]) else names[:1]
    labels = []
    for author in shown:
        surname = text(author["full_name"].split(",", 1)[0])
        labels.append(f"**{surname}**" if is_author(author) else surname)
    return ", ".join(labels) + (" et al." if len(shown) < len(names) else "")


def reference(metadata: dict, year: str) -> tuple[str, str | None]:
    """Prefer the journal article; keep preprints accurately labelled."""
    infos = [p for p in metadata.get("publication_info", [])
             if (p.get("journal_title") or p.get("pubinfo_freetext"))
             and p.get("material", "").lower() != "erratum"]
    dois = [normalize_doi(d.get("value")) for d in metadata.get("dois", [])
            if d.get("material", "").lower() != "erratum"]
    doi = next((d for d in dois if d), None)
    if infos and doi:
        # Some journals (e.g. Open Journal of Astrophysics) are represented
        # only by a free-text reference. They are still published papers.
        info = next((p for p in infos if p.get("journal_title")), infos[0])
        url = "https://doi.org/" + quote(doi, safe="/:;")
        if not info.get("journal_title"):
            return f"[{text(info['pubinfo_freetext'])}]({url}).", doi
        journal = JOURNALS.get(info["journal_title"], info["journal_title"])
        volume = info.get("journal_volume", "")
        if journal == "JCAP":
            volume = info.get("journal_issue") or volume
        pages = info.get("artid") or info.get("page_start")
        label = journal + (f" {volume}" if volume else "")
        if pages:
            label += f", {pages}"
        label += f", {info.get('year') or year}"
        return f"[{text(label)}]({url}).", doi
    arxiv = metadata.get("arxiv_eprints") or []
    if arxiv:
        arxiv_id = str(arxiv[0]["value"])
        url = "https://arxiv.org/abs/" + quote(arxiv_id, safe="/")
        return f"[arXiv preprint]({url}), {year}.", doi
    if doi:
        return f"[Publication](https://doi.org/{quote(doi, safe='/:;')}), {year}.", doi
    raise GenerationError("publication has neither a DOI nor an arXiv identifier")


def render_page(records: list[dict], updated: str) -> str:
    ids = set()
    for record in records:
        try:
            rid = str(record["id"])
            metadata = record["metadata"]
            if not rid.isdigit() or rid in ids:
                raise ValueError("invalid or duplicate record ID")
            if not metadata["titles"][0]["title"].strip():
                raise ValueError("empty title")
            if not re.fullmatch(r"\d{4}(?:-\d{2}){0,2}", metadata["earliest_date"]):
                raise ValueError("invalid date")
            ids.add(rid)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationError("publication lacks valid identifying metadata") from exc
    if not records:
        raise GenerationError("empty publication list")
    ordered = sorted(records, key=lambda r: (r["metadata"]["earliest_date"], int(r["id"])), reverse=True)
    lines = [
        "---", "title: Publications", "date: 2026-11-18",
        "summary: Publications and preprints by Nhat-Minh Nguyen.",
        "hide_date: true", "reading_time: false", "share: false", "pager: false",
        "show_date_updated: false", "---", "",
        "<!-- Generated by scripts/build_publications_page.py; do not edit entries here. -->", "",
        f"All {len(records)} works listed on my [INSPIRE profile]({PROFILE_URL}), newest first. "
        "Journal references are used where available; other entries link to arXiv preprints.", "",
        f"Updated {updated}. Refreshed monthly from INSPIRE.", "",
    ]
    for number, record in enumerate(ordered, 1):
        metadata = record["metadata"]
        author_line = authors(metadata)
        ref, doi = reference(metadata, metadata["earliest_date"][:4])
        recognition = RECOGNITION_BY_DOI.get(doi or "")
        title = text(metadata["titles"][0]["title"])
        if not title.endswith((".", "?", "!")):
            title += "."
        entry = f'{number}. {author_line.rstrip(".")}. “{title}” {ref}'
        if recognition:
            entry += f" {recognition}."
        lines.extend([entry, ""])
    return "\n".join(lines)


def atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(value)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--snapshot-output", type=Path, help="Save retrieved records for inspection")
    parser.add_argument("--from-snapshot", type=Path, help="Render a previously retrieved snapshot offline")
    args = parser.parse_args()
    try:
        if args.from_snapshot:
            snapshot = json.loads(args.from_snapshot.read_text(encoding="utf-8"))
            if snapshot["author_id"] != AUTHOR_ID:
                raise GenerationError("snapshot belongs to a different author")
        else:
            snapshot = {"author_id": AUTHOR_ID, "updated": date.today().isoformat(), "records": fetch_records()}
        page = render_page(snapshot["records"], snapshot["updated"])
        # No destination is changed until the complete list has been validated.
        atomic_write(args.output, page)
        if args.snapshot_output:
            atomic_write(args.snapshot_output, json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
        print(f"Wrote {len(snapshot['records'])} INSPIRE publications to {args.output}")
    except (GenerationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Publication refresh failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
