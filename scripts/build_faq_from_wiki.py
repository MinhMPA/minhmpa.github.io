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
    parts = re.split(r"^##\s+Summary\s*$", text, maxsplit=1, flags=re.MULTILINE)
    if len(parts) < 2:
        return ""
    body = parts[1].strip()
    return body


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


def main(argv: list[str]) -> int:  # placeholder; filled in by later tasks
    raise NotImplementedError("filled in by subsequent tasks")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
