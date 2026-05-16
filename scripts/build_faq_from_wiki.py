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

import argparse
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
    """Return lowercase content tokens from a title (length >= 3, no stopwords)."""
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

    # bucket validation: filter each bucket's SRC list to those present in records.
    # Buckets with zero present members are skipped. We do NOT exit 5 here
    # because the bucket map is a static config that may name SRCs not yet
    # in the wiki; that is desirable. Exit 5 stays reserved for structurally
    # malformed bucket maps, e.g. non-list values — defensive only.
    filtered_buckets: dict[str, list[str]] = {}
    for bucket_id, srcs in BUCKETS.items():
        if not isinstance(srcs, list):
            print(f"error: bucket {bucket_id!r} value is not a list", file=sys.stderr)
            return 5
        present = [s for s in srcs if s in records]
        if present:
            filtered_buckets[bucket_id] = present

    per_paper_entries = [
        build_per_paper_entry(src_id, rec, buckets_membership=_buckets_for(src_id))
        for src_id, rec in sorted(records.items())
    ]
    bucket_entries = [
        build_bucket_entry(bucket_id, srcs, records)
        for bucket_id, srcs in filtered_buckets.items()
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
