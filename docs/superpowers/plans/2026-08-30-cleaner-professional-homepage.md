# Cleaner Professional Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the homepage cleaner and easier to scan for academic and public visitors while preserving its existing cosmic visual identity.

**Architecture:** Keep the current Hugo Blox `resume-biography-3` landing block and make only data-driven refinements. Author front matter owns the public identity and biography, homepage front matter owns action and visibility settings, and the local biography partial renders those settings with backward compatibility for the existing singular button interface.

**Tech Stack:** Hugo 0.149.0, Hugo Blox, Go templates, YAML/Markdown content, Tailwind utility classes, Python 3 with pytest, Node.js built-in test runner

**Spec:** `docs/superpowers/specs/2026-08-30-cleaner-professional-homepage-design.md`

## Global Constraints

- Preserve the current cosmic background, dark palette, portrait treatment, pronunciation, social icons, typography, two-column desktop composition, and stacked mobile composition.
- Do not add cards, a new visual section, a new color system, new imagery, new JavaScript, a replacement landing-page component, or a new dependency.
- Keep `Visualization` as a top-level navigation item and use the approved noun-based navigation order: Research, Travel, Teaching, Visualization, Outreach, Blog, Contact.
- Give `Kavli IPMU Fellow, University of Tokyo` and `Faculty and Group Leader, IFIRSE at ICISE` equal visual prominence.
- Preserve the exact two PRL URLs, two media URLs, and Buchalter Prize URL from the specification.
- Preserve the `interests`, `education`, and `work` data in `content/authors/admin/_index.md`; hide only the rendered Interests and Education panels on the homepage.
- Render Research and Contact in the current tab. Render Publications and Download CV with `target="_blank" rel="noopener"`.
- Reuse the current CV button's Tailwind classes for all four visible actions and wrap the action row on narrow screens.

## File Map

- `tests/test_homepage.py` — builds the site in a temporary directory, parses the generated homepage with the Python standard library, and guards approved content, links, navigation, action behavior, metadata retention, and panel visibility.
- `content/authors/admin/_index.md` — owns the public role, two equal appointments, preserved profile metadata, and concise biography with the approved research-impact links.
- `config/_default/menus.yaml` — owns the noun-based primary navigation and keeps Visualization top-level.
- `content/_index.md` — configures the four homepage actions and the two homepage-only panel opt-outs while retaining the current visual settings.
- `layouts/partials/blox/resume-biography-3.html` — renders the action list, new-tab semantics, legacy singular-button fallback, and conditional Interests/Education grid without changing the landing-page aesthetic.

---

### Task 1: Clarify the public identity, biography, and navigation

**Files:**
- Create: `tests/test_homepage.py`
- Modify: `content/authors/admin/_index.md:8-12,66-78`
- Modify: `config/_default/menus.yaml:6-30`
- Test: `tests/test_homepage.py`

**Interfaces:**
- Consumes: Hugo CLI from the project environment and the existing `resume-biography-3` rendering path.
- Produces: `ParsedHomePage`, the module-scoped `homepage` fixture, final author front-matter fields `role: str` and `organizations: list[{name: str, url: str}]`, and the final primary-navigation labels used by Task 2.

- [ ] **Step 1: Create the homepage regression-test harness and content assertions**

Create `tests/test_homepage.py` with this complete content:

```python
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
```

- [ ] **Step 2: Run the identity test and verify the old homepage fails it**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_homepage.py::test_homepage_identity_copy_and_navigation -v
```

Expected: FAIL because the rendered hero does not yet contain `Cosmologist` and the navigation still begins with `Bio` and contains `Teach`.

- [ ] **Step 3: Replace the hero identity and biography while preserving all profile metadata**

In `content/authors/admin/_index.md`, replace the current `role` and `organizations` fields with:

```yaml
role: Cosmologist
avatar_alt: Portrait of Minh Nguyen
organizations:
  - name: Kavli IPMU Fellow, University of Tokyo
    url: https://www.ipmu.jp/en
  - name: Faculty and Group Leader, IFIRSE at ICISE
    url: https://ifirse.icise.vn/astrophysics-cosmology-group.html
```

Leave the complete `profiles`, `interests`, `education`, and `work` mappings unchanged. Replace the Markdown body after the closing front-matter delimiter with:

```markdown
## About Me

I am a cosmologist developing forward-modeling and field-level Bayesian inference methods for galaxy surveys. I use them to extract more information from cosmic structure and test gravity, dark energy, and primordial physics.

My work includes the first [4-sigma evidence for suppressed late-time growth of large-scale structure](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.131.111001) and [field-level inference methods](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.133.221006) that extract substantially more cosmological information than standard analyses. These results appeared in two *Physical Review Letters* papers; the suppressed-growth result received coverage in [*Scientific American*](https://www.scientificamerican.com/article/a-possible-crisis-in-the-cosmos-could-lead-to-a-new-understanding-of-the-universe/) and [*New Scientist*](https://www.newscientist.com/article/2391414-the-universes-evolution-seems-to-be-slowing-and-we-dont-know-why/), while the field-level inference work was recognized with the [2024 Buchalter Cosmology Prize](https://www.buchaltercosmologyprize.org/).

I welcome inquiries from prospective students and postdocs, and from researchers interested in collaboration.
```

- [ ] **Step 4: Replace the primary-navigation mapping with the approved noun labels and order**

In `config/_default/menus.yaml`, keep the existing comments and replace the `main` mapping with:

```yaml
main:
  - name: Research
    url: research/
    weight: 20
  - name: Travel
    url: travel/
    weight: 30
  - name: Teaching
    url: teach/
    weight: 40
  - name: Visualization
    url: https://minhmpa.github.io/lss-lab/
    weight: 45
  - name: Outreach
    url: outreach/
    weight: 50
  - name: Blog
    url: blog/
    weight: 60
  - name: Contact
    url: contact/
    weight: 70
```

- [ ] **Step 5: Run the focused homepage tests and Hugo build**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_homepage.py -v
hugo --gc --minify
git diff --check
```

Expected: all 3 homepage tests PASS; Hugo reports `Pages │ 32` and completes without an error; `git diff --check` produces no output. The existing Hugo sitemap-template warning may still appear.

- [ ] **Step 6: Commit the public identity and navigation slice**

```bash
git add tests/test_homepage.py content/authors/admin/_index.md config/_default/menus.yaml
git commit -m "feat: clarify homepage identity and navigation"
```

Expected: one commit containing the regression harness, the concise biography, equal dual appointments, and noun-based navigation.

---

### Task 2: Add the action row and homepage-only profile-panel controls

**Files:**
- Modify: `tests/test_homepage.py`
- Modify: `content/_index.md:9-28`
- Modify: `layouts/partials/blox/resume-biography-3.html:120-162`
- Test: `tests/test_homepage.py`

**Interfaces:**
- Consumes: `ParsedHomePage` and `homepage` from Task 1; the existing `wcBlock.content.button` singular mapping; author fields `interests` and `education`.
- Produces: `wcBlock.content.buttons: list[{text: str, url: str, new_tab?: bool}]`, `wcBlock.content.hide_interests: bool`, `wcBlock.content.hide_education: bool`, rendered action hook class `homepage-action`, action-container class `homepage-actions`, and optional detail-grid class `homepage-profile-details`.

- [ ] **Step 1: Add failing tests for action semantics, hidden panels, and unchanged visual configuration**

Append the following tests to `tests/test_homepage.py`:

```python
def test_homepage_actions_and_target_behavior(homepage: ParsedHomePage) -> None:
    expected_actions = {
        "Research": ("/research/", False),
        "Publications": (
            "https://scholar.google.com/citations?hl=en&user=Wfr8DzAAAAAJ",
            True,
        ),
        "Download CV": ("/cv/Nhat-Minh-Nguyen-academic-cv.pdf", True),
        "Contact": ("/contact/", False),
    }
    action_links = {
        str(link["text"]): link
        for link in homepage.links
        if "homepage-action"
        in str(link["attrs"].get("class", "")).split()
    }

    assert set(action_links) == set(expected_actions)
    assert "homepage-actions" in homepage.classes

    for label, (expected_href, opens_new_tab) in expected_actions.items():
        attrs = action_links[label]["attrs"]
        assert attrs["href"] == expected_href
        if opens_new_tab:
            assert attrs["target"] == "_blank"
            assert "noopener" in str(attrs["rel"]).split()
        else:
            assert "target" not in attrs
            assert "rel" not in attrs


def test_homepage_hides_profile_detail_panels(homepage: ParsedHomePage) -> None:
    assert "Interests" not in homepage.visible_text
    assert "Education" not in homepage.visible_text
    assert "homepage-profile-details" not in homepage.classes

    author_source = AUTHOR_SOURCE.read_text(encoding="utf-8")
    assert "\ninterests:\n" in author_source
    assert "\neducation:\n" in author_source


def test_homepage_keeps_visual_configuration_and_legacy_button_support() -> None:
    homepage_source = (ROOT / "content" / "_index.md").read_text(
        encoding="utf-8"
    )
    partial_source = (
        ROOT / "layouts" / "partials" / "blox" / "resume-biography-3.html"
    ).read_text(encoding="utf-8")

    for setting in (
        'spacing: "5rem"',
        "avatar: /images/blog_profile.png",
        "css_class: dark",
        "color: black",
        "filename: cosmic-surprise.png",
        "brightness: 0.55",
        "size: cover",
        "position: center",
        "parallax: false",
    ):
        assert setting in homepage_source

    assert "{{ with $block.content.button }}" in partial_source
```

- [ ] **Step 2: Run the new action test and verify the singular-button homepage fails it**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_homepage.py::test_homepage_actions_and_target_behavior -v
```

Expected: FAIL because no rendered link has the `homepage-action` class and only the singular Download CV button exists.

- [ ] **Step 3: Configure the four actions and the two homepage-only hide flags**

In `content/_index.md`, replace the current singular `button` mapping with the following fields under the existing `content` mapping. Leave every field under `design` unchanged.

```yaml
      buttons:
        - text: Research
          url: /research/
        - text: Publications
          url: https://scholar.google.com/citations?hl=en&user=Wfr8DzAAAAAJ
          new_tab: true
        - text: Download CV
          url: /cv/Nhat-Minh-Nguyen-academic-cv.pdf
          new_tab: true
        - text: Contact
          url: /contact/
      hide_interests: true
      hide_education: true
```

The complete `content` mapping after the change is:

```yaml
    content:
      username: admin
      avatar: /images/blog_profile.png
      text: ""
      buttons:
        - text: Research
          url: /research/
        - text: Publications
          url: https://scholar.google.com/citations?hl=en&user=Wfr8DzAAAAAJ
          new_tab: true
        - text: Download CV
          url: /cv/Nhat-Minh-Nguyen-academic-cv.pdf
          new_tab: true
        - text: Contact
          url: /contact/
      hide_interests: true
      hide_education: true
```

- [ ] **Step 4: Replace the singular-button renderer with a wrapping action list and legacy fallback**

In `layouts/partials/blox/resume-biography-3.html`, replace lines 120-125, the existing `with $block.content.button` block, with:

```go-html-template
    {{ $buttons := $block.content.buttons }}
    {{ $legacy_button := false }}
    {{ if not $buttons }}
      {{ with $block.content.button }}
        {{ $buttons = slice . }}
        {{ $legacy_button = true }}
      {{ end }}
    {{ end }}

    {{ with $buttons }}
    <div class="homepage-actions flex flex-wrap gap-2 mt-4">
      {{ range . }}
      {{ $target := "" }}
      {{ if or .new_tab $legacy_button }}
        {{ $target = "target=\"_blank\" rel=\"noopener\"" }}
      {{ end }}
      <a href="{{ .url | safeURL }}" {{ $target | safeHTMLAttr }} class="homepage-action inline-flex items-center px-4 py-2 text-sm font-medium text-gray-900 bg-white border border-gray-200 rounded-lg hover:bg-gray-100 hover:text-primary-700 focus:z-10 focus:ring-4 focus:outline-none focus:ring-gray-200 focus:text-primary-700 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:text-white dark:hover:bg-gray-700 dark:focus:ring-gray-700">{{ .text }}</a>
      {{ end }}
    </div>
    {{ end }}
```

This keeps the existing button classes, gives the new actions descriptive text, wraps the row with `flex-wrap`, and preserves the old singular button's new-tab behavior.

- [ ] **Step 5: Make the Interests/Education grid conditional without deleting author data**

In the same partial, replace the existing grid from lines 130-162 with:

```go-html-template
  {{ $show_interests := and (not $block.content.hide_interests) $person.interests }}
  {{ $show_education := and (not $block.content.hide_education) $person.education }}

  {{ if or $show_interests $show_education }}
  <div class="homepage-profile-details grid grid-cols-2 gap-4 justify-between mt-6 dark:text-gray-300">

    {{ if $show_interests }}
    <div class="">
      <div class="section-subheading mb-3">{{ i18n "interests" | markdownify }}</div>
      <ul class="list-disc list-inside space-y-1 pl-5">
        {{ range $person.interests }}
        <li>
          {{ . | markdownify | emojify }}
        </li>
        {{ end }}
      </ul>
    </div>
    {{ end }}

    {{ if $show_education }}
    <div class="">
      <div class="section-subheading mb-3">{{ i18n "education" | markdownify }}</div>
      <ul class="">
        {{ range $person.education }}
        <li class="flex items-start gap-3">
          {{ partial "functions/get_icon" (dict "name" "academic-cap" "attributes" "style=\"\" class='flex-shrink-0 w-5 h-5 me-2 mt-1'") }}
          <div class="description">
            <p class="course">{{ .area }}{{ with .year }}, {{ . }}{{ end }}</p>
            <p class="text-sm">{{ .institution }}</p>
          </div>
        </li>
        {{ end }}
      </ul>
    </div>
    {{ end }}

  </div>
  {{ end }}
```

The default remains unchanged when either hide flag is absent. When both homepage flags are true, no empty details grid is emitted.

- [ ] **Step 6: Run the homepage tests and production build**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest tests/test_homepage.py -v
hugo --gc --minify
git diff --check
```

Expected: all 6 homepage tests PASS; Hugo reports `Pages │ 32` and completes without an error; `git diff --check` produces no output. The existing sitemap-template warning may still appear.

- [ ] **Step 7: Commit the reusable landing-block controls**

```bash
git add tests/test_homepage.py content/_index.md layouts/partials/blox/resume-biography-3.html
git commit -m "feat: streamline homepage actions and profile details"
```

Expected: one commit containing the four-action interface, explicit new-tab semantics, legacy singular-button fallback, and homepage-only panel suppression.

---

### Task 3: Run full regression and responsive acceptance checks

**Files:**
- Verify: `content/authors/admin/_index.md`
- Verify: `content/_index.md`
- Verify: `config/_default/menus.yaml`
- Verify: `layouts/partials/blox/resume-biography-3.html`
- Verify: `tests/test_homepage.py`

**Interfaces:**
- Consumes: the final homepage implementation and all six homepage regression tests from Tasks 1-2.
- Produces: a clean, production-buildable branch with desktop and mobile evidence that the established landing-page design is preserved.

- [ ] **Step 1: Run every automated test and the production build**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q
node --test tests/research-bot-matcher.test.mjs
hugo --gc --minify
git diff --check
```

Expected:

- pytest: `46 passed`;
- Node.js: `27` tests, `27` pass, `0` fail; the existing module-type warning may appear;
- Hugo: `Pages │ 32`, no build error, and only the existing sitemap-template warning;
- `git diff --check`: no output.

- [ ] **Step 2: Start a local Hugo preview for responsive inspection**

Run in a persistent terminal:

```bash
hugo server -D --bind 127.0.0.1 --port 1315 --disableFastRender
```

Expected: `Web Server is available at http://localhost:1315/`.

- [ ] **Step 3: Capture desktop and mobile screenshots of the final homepage**

Run in a second terminal:

```bash
/Users/nguyenmn/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell --headless --hide-scrollbars --disable-gpu --window-size=1440,1200 --screenshot=/tmp/minh-homepage-final-desktop.png http://127.0.0.1:1315/
/Users/nguyenmn/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell --headless --hide-scrollbars --disable-gpu --window-size=390,1600 --screenshot=/tmp/minh-homepage-final-mobile.png http://127.0.0.1:1315/
```

Expected: both commands report that PNG bytes were written to the named files.

- [ ] **Step 4: Inspect both screenshots against the approved visual constraints**

Open `/tmp/minh-homepage-final-desktop.png` and `/tmp/minh-homepage-final-mobile.png` with the agent's image viewer and verify every item:

- the existing cosmic background, brightness, portrait, pronunciation, dark palette, and typography are unchanged;
- desktop retains the left-profile/right-biography split;
- mobile retains the stacked profile-then-biography flow;
- both appointments appear with equal prominence;
- the shorter biography contains no Research Program, career chronology, Interests panel, or Education panel;
- Research, Publications, Download CV, and Contact appear after the biography;
- buttons wrap without overlap or horizontal overflow at 390 px;
- text remains legible and keyboard focus classes remain on every action.
- switching once between the light and dark theme controls leaves all landing-page text legible.

Expected: every item passes. Do not complete the task while any approved visual constraint is violated.

- [ ] **Step 5: Stop the preview and confirm the branch is clean**

Press `Ctrl-C` in the Hugo-server terminal, then run:

```bash
git status --short
git log -4 --oneline
```

Expected: `git status --short` produces no output. The log shows the design-spec commit, implementation-plan commit, Task 1 implementation commit, and Task 2 implementation commit.

## Coverage Map

- Navigation and noun labels: Task 1, Steps 1-5.
- Equal appointments and plain professional identity: Task 1, Steps 1-5.
- Approved concise copy and five exact impact URLs: Task 1, Steps 1-5.
- Preserved pronunciation, social links, Interests, Education, and Work metadata: Task 1, Steps 1 and 5; Task 2, Step 6.
- Four visible actions and exact tab behavior: Task 2, Steps 1-6.
- Homepage-only Interests/Education suppression with default rendering preserved: Task 2, Steps 1 and 5-6.
- Existing visual design and responsive behavior: Task 2, Step 6; Task 3, Steps 2-4.
- Full regression and production readiness: Task 3, Steps 1 and 5.
