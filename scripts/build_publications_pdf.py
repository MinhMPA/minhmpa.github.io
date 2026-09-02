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


_LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(value: object) -> str:
    """Escape LaTeX-reserved characters in plain text in one pass."""
    return "".join(_LATEX_ESCAPES.get(char, char) for char in str(value))


def citation_label(count: int) -> str:
    return f"{count:,} citation" if count == 1 else f"{count:,} citations"


def render_latex(
    publications: list[Publication], metrics: Metrics, *, generated_on: str
) -> str:
    lines = [
        r"\documentclass[10pt,a4paper]{article}",
        r"\usepackage[a4paper,margin=19mm]{geometry}",
        r"\usepackage{fontspec}",
        r"\usepackage{microtype}",
        r"\usepackage{xcolor}",
        r"\usepackage{hyperref}",
        r"\usepackage{enumitem}",
        r"\usepackage{fancyhdr}",
        r"\definecolor{darktext}{HTML}{253047}",
        r"\definecolor{muted}{HTML}{667085}",
        r"\definecolor{linkblue}{HTML}{1769AA}",
        r"\definecolor{accent}{HTML}{9A6700}",
        r"\hypersetup{colorlinks=true,linkcolor=linkblue,urlcolor=linkblue}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyfoot[C]{\color{muted}\thepage}",
        r"\setlength{\headheight}{13pt}",
        r"\setlist[itemize]{leftmargin=*,itemsep=5pt,topsep=6pt}",
        r"\begin{document}",
        r"\color{darktext}",
        r"{\LARGE\bfseries Publications}\par",
        r"\vspace{3pt}",
        (
            f"{{\\color{{muted}}{metrics.publications:,} publications \\textbullet\\ "
            f"{metrics.citations:,} citations \\textbullet\\ h-index {metrics.h_index}}}\\par"
        ),
        f"{{\\small\\color{{muted}}Generated from INSPIRE HEP on {latex_escape(generated_on)}}}\\par",
        r"\vspace{8pt}",
        r"\begin{itemize}",
    ]
    for publication in publications:
        title = latex_escape(publication.title)
        title_link = f"\\href{{{publication.record_url}}}{{{title}}}"
        source_link = (
            f"\\href{{https://arxiv.org/abs/{publication.arxiv_id}}}"
            f"{{arXiv:{latex_escape(publication.arxiv_id)}}}"
            if publication.arxiv_id
            else f"\\href{{{publication.record_url}}}{{INSPIRE record}}"
        )
        lines.extend(
            [
                f"\\item {title_link}\\\\",
                f"{{\\small {latex_escape(publication.author_line)} · {source_link} · "
                f"{publication.year} · {citation_label(publication.citations)}}}",
            ]
        )
        if publication.recognition:
            lines.append(
                f"{{\\small\\color{{accent}}{latex_escape(publication.recognition)}}}"
            )
    lines.extend([r"\end{itemize}", r"\end{document}"])
    return "\n".join(lines) + "\n"
