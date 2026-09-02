"""Generate a publication-list PDF from Nhat-Minh Nguyen's INSPIRE profile."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

AUTHOR_ID = "1986925"
AUTHOR_NAME = "Nhat-Minh Nguyen"
API_ROOT = "https://inspirehep.net/api"
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "static"
    / "publications"
    / "Nhat-Minh-Nguyen-publications.pdf"
)

RECOGNITION_BY_DOI = {
    "10.1103/physrevlett.131.111001": "Editors’ Suggestion",
    "10.1103/physrevlett.133.221006": "Buchalter Cosmology Prize 2024",
}


class GenerationError(RuntimeError):
    """Raised when INSPIRE data or PDF generation is unusable."""


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


def _mathml_text(element: ET.Element) -> str:
    """Return a compact plain-text rendering for the MathML used by INSPIRE."""
    tag = element.tag.rsplit("}", 1)[-1]
    children = list(element)
    if tag == "msub" and len(children) >= 2:
        return f"{_mathml_text(children[0])}_{_mathml_text(children[1])}"
    if tag == "msup" and len(children) >= 2:
        return f"{_mathml_text(children[0])}^{_mathml_text(children[1])}"

    value = element.text or ""
    for child in children:
        value += _mathml_text(child)
        value += child.tail or ""
    return value


def _plain_mathml(match: re.Match[str]) -> str:
    try:
        return _mathml_text(ET.fromstring(match.group(0)))
    except ET.ParseError:
        return re.sub(r"<[^>]+>", "", match.group(0))


def _plain_tex_math(match: re.Match[str]) -> str:
    expression = match.group(1)
    expression = expression.replace(r"\phi", "φ").replace(r"\gamma", "γ")
    expression = re.sub(r"\\(?:rm|mathrm)\s*", "", expression)
    return expression.translate(str.maketrans("", "", "{}"))


def plain_title(value: object) -> str:
    """Turn occasional INSPIRE markup and TeX in titles into readable text."""
    title = html.unescape(str(value))
    title = re.sub(r"<math\b[^>]*>.*?</math>", _plain_mathml, title, flags=re.DOTALL)
    title = re.sub(r"\$([^$]*)\$", _plain_tex_math, title)
    title = re.sub(r"<[^>]+>", "", title)
    return title.replace("ϕ", "φ")


def render_latex(
    publications: list[Publication], metrics: Metrics, *, generated_on: str
) -> str:
    lines = [
        r"\documentclass[10pt,a4paper]{article}",
        r"\usepackage[a4paper,margin=19mm]{geometry}",
        r"\usepackage{fontspec}",
        r"\usepackage{newcomputermodern}",
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
        r"\setlist[itemize]{leftmargin=*,itemsep=0pt,topsep=6pt}",
        r"\begin{document}",
        r"\color{darktext}",
        r"{\LARGE\bfseries Nhat-Minh Nguyen \textemdash{} Publications}\par",
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
        title = latex_escape(plain_title(publication.title))
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
