"""Regression tests for the rendered homepage."""

from __future__ import annotations

import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
AUTHOR_SOURCE = ROOT / "content" / "authors" / "admin" / "_index.md"

IMPACT_URLS = {
    "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.131.111001",
    "https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.133.221006",
    "https://www.scientificamerican.com/article/a-possible-crisis-in-the-cosmos-could-lead-to-a-new-understanding-of-the-universe/",
    "https://www.newscientist.com/article/2391414-the-universes-evolution-seems-to-be-slowing-and-we-dont-know-why/",
    "https://www.buchaltercosmologyprize.org/",
}

SOCIAL_URLS = {
    "mailto:nhat.minh.nguyen@ipmu.jp",
    "https://x.com/MinhNguyenAstro",
    "https://github.com/MinhMPA",
    "https://www.linkedin.com/in/minhmpa/",
    "https://scholar.google.com/citations?hl=en&user=Wfr8DzAAAAAJ",
    "https://orcid.org/0000-0002-2542-7233",
}


class ParsedHomePage(HTMLParser):
    """Collect visible body text, links, and CSS classes from generated HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.text_parts: list[str] = []
        self.links: list[dict[str, object]] = []
        self.classes: set[str] = set()
        self._current_link: dict[str, object] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        self.classes.update((attributes.get("class") or "").split())

        if tag == "body":
            self.in_body = True

        if self.in_body and tag == "a":
            self._current_link = {"attrs": attributes, "text_parts": []}

    def handle_data(self, data: str) -> None:
        if not self.in_body:
            return

        self.text_parts.append(data)
        if self._current_link is not None:
            self._current_link["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link is not None:
            text_parts = self._current_link.pop("text_parts")
            self._current_link["text"] = " ".join("".join(text_parts).split())
            self.links.append(self._current_link)
            self._current_link = None

        if tag == "body":
            self.in_body = False

    @property
    def visible_text(self) -> str:
        return " ".join("".join(self.text_parts).split())

    @property
    def hrefs(self) -> set[str]:
        return {
            str(link["attrs"].get("href"))
            for link in self.links
            if link["attrs"].get("href")
        }


@pytest.fixture(scope="module")
def homepage(tmp_path_factory: pytest.TempPathFactory) -> ParsedHomePage:
    destination = tmp_path_factory.mktemp("hugo-homepage")
    result = subprocess.run(
        [
            "hugo",
            "--destination",
            str(destination),
            "--cleanDestinationDir",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    page = ParsedHomePage()
    page.feed((destination / "index.html").read_text(encoding="utf-8"))
    return page


def test_homepage_identity_copy_and_navigation(homepage: ParsedHomePage) -> None:
    assert "Cosmologist" in homepage.visible_text
    assert "Kavli IPMU Fellow, University of Tokyo" in homepage.visible_text
    assert "Faculty and Group Leader, IFIRSE at ICISE" in homepage.visible_text
    assert (
        "I am a cosmologist developing forward-modeling and field-level Bayesian "
        "inference methods for galaxy surveys."
        in homepage.visible_text
    )
    assert (
        "I welcome inquiries from prospective students and postdocs, and from "
        "researchers interested in collaboration."
        in homepage.visible_text
    )
    assert "Research Program" not in homepage.visible_text

    nav_labels = [
        str(link["text"])
        for link in homepage.links
        if "nav-link" in str(link["attrs"].get("class", "")).split()
    ]
    assert nav_labels == [
        "Research",
        "Travel",
        "Teaching",
        "Visualization",
        "Outreach",
        "Blog",
        "Contact",
    ]


def test_homepage_preserves_research_impact_links(
    homepage: ParsedHomePage,
) -> None:
    assert IMPACT_URLS <= homepage.hrefs


def test_author_metadata_and_profile_elements_are_preserved(
    homepage: ParsedHomePage,
) -> None:
    author_source = AUTHOR_SOURCE.read_text(encoding="utf-8")
    for field in ("\ninterests:\n", "\neducation:\n", "\nwork:\n"):
        assert field in author_source

    assert "/ˈmiːn ˈŋwɪn/" in homepage.visible_text
    assert SOCIAL_URLS <= homepage.hrefs
