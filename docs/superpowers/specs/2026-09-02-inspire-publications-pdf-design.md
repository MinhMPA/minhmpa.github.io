# INSPIRE Publications PDF Design

**Date:** 2026-09-02<br>
**Status:** Approved for implementation planning<br>
**Branch:** `homepage-cleanup-plan`<br>
**Pull request:** #3

## Objective

Replace the redundant `Research` and `Contact` actions on the landing biography with two focused document actions: `CV` and `Publications`. The `Publications` action will open a locally hosted PDF generated from Nhat-Minh Nguyen's public INSPIRE author profile.

The repository will include a reusable command that fetches current INSPIRE metadata, recalculates publication and citation metrics, and safely regenerates the PDF whenever the profile changes.

## Scope

This change includes:

- reducing the landing biography actions from four buttons to two;
- relabeling `Download CV` as `CV` while preserving the existing CV file and new-tab behavior;
- replacing the external Google Scholar destination with a local generated publications PDF;
- adding a reusable Python-to-LaTeX generation pipeline;
- committing the generated PDF so Hugo can serve it as a static asset;
- documenting the regeneration command; and
- adding automated tests for the data transformation and homepage contract.

It does not add a publications HTML page, automate regeneration on a schedule, modify the top navigation, or change the existing landing-page theme and layout.

## Homepage Actions

The landing biography will show exactly two buttons in this order:

1. `CV` → `/cv/Nhat-Minh-Nguyen-academic-cv.pdf`
2. `Publications` → `/publications/Nhat-Minh-Nguyen-publications.pdf`

Both PDFs will open in a new tab with `noopener` protection. `Research` and `Contact` will remain available in the top navigation and will no longer be duplicated in the biography actions.

The generic multi-button support in `resume-biography-3.html` will remain unchanged because the homepage configuration can express the new behavior without altering the component.

## Authoritative Data Source

The generator will use the official [INSPIRE REST API](https://github.com/inspirehep/rest-api-doc), not scrape the JavaScript-rendered profile page.

- Author record: `https://inspirehep.net/api/authors/1986925`
- Human-readable profile: `https://inspirehep.net/authors/1986925?ui-citation-summary=true`
- Author identity: resolve the `INSPIRE BAI` value from the author record, currently `Nhat.Minh.Nguyen.1`
- Literature search: query all records authored by the resolved BAI, requesting most-recent-first results and following pagination until no next page remains

The script will use only public, read-only endpoints and require no credentials.

## Publication Inclusion and Ordering

The PDF will include every literature record returned for the author, including journal articles, arXiv preprints, and other claimed publications such as community reports. It will not filter to peer-reviewed works.

Records will be ordered newest-first using `metadata.earliest_date`. The INSPIRE record ID will provide a deterministic secondary ordering when dates match. Citation counts default to zero if INSPIRE omits the field.

## Summary Metrics

At generation time, the script will compute:

- **Publications:** number of retrieved INSPIRE literature records;
- **Citations:** sum of each record's `metadata.citation_count`, including self-citations because this is INSPIRE's default total; and
- **h-index:** largest integer *h* for which at least *h* retrieved records each have at least *h* citations.

The opening line will use grouped numbers and this format:

> 24 publications · 4,444 citations · h-index 17

Those values are illustrative live values observed during design and must never be hard-coded. The PDF will also state its generation date and attribute the data to INSPIRE HEP so readers know when the metrics were refreshed.

## PDF Content and Presentation

The generated document will be a restrained, professional A4 publication list titled:

> Nhat-Minh Nguyen — Publications

It will use a single-column layout, readable academic typography, compact spacing, page numbers, and unobtrusive linked text. Each publication entry will contain:

- title, linked to its INSPIRE literature record;
- short author line: `Nhat-Minh Nguyen` for a sole-authored record or `Nhat-Minh Nguyen et al.` otherwise;
- linked arXiv identifier when `arxiv_eprints` is available, otherwise a linked `INSPIRE record` label;
- year derived from `earliest_date`; and
- current INSPIRE citation count with correct singular/plural wording.

Titles and metadata will be escaped safely for LaTeX. LuaLaTeX will provide robust Unicode handling.

## Stable Recognition Annotations

Two entries receive manually curated recognition notes. The mapping will be keyed by normalized DOI rather than title or list position so it remains stable as INSPIRE metadata and ordering change:

- `10.1103/PhysRevLett.131.111001` → `Editors’ Suggestion`
- `10.1103/PhysRevLett.133.221006` → `Buchalter Cosmology Prize 2024`

Annotations will be visually distinct but subordinate to the publication title. No other awards or media coverage are added to this PDF.

## Generator Interface and Build Flow

The reusable command will be:

```bash
python scripts/build_publications_pdf.py
```

The script will:

1. fetch and validate the author record;
2. resolve its INSPIRE BAI;
3. fetch every literature page for that BAI;
4. normalize and order the records;
5. calculate summary metrics;
6. render a temporary LaTeX document;
7. compile it with `latexmk` and LuaLaTeX; and
8. atomically replace `static/publications/Nhat-Minh-Nguyen-publications.pdf` only after a successful build.

Python's standard library will handle HTTP and JSON, avoiding a new runtime package. The documented system dependencies are `latexmk` and `lualatex`.

The generated `.tex`, auxiliary files, and logs will remain temporary and will not be committed.

## Failure Handling

The generator will fail with a nonzero exit status and a concise diagnostic when:

- INSPIRE cannot be reached within the configured timeout;
- the API returns a non-success response or invalid JSON;
- the author record lacks an INSPIRE BAI;
- a paginated response has an unexpected shape;
- no literature records are returned; or
- `latexmk`/LuaLaTeX is missing or compilation fails.

A failed run must leave the previously generated PDF untouched. Temporary build files will be cleaned automatically. The request volume will remain well below INSPIRE's documented rate limit for this profile.

## Testing and Verification

Implementation will follow test-first development using local JSON fixtures rather than live network calls.

Automated tests will cover:

- resolving the INSPIRE BAI from an author record;
- parsing all publications and following pagination;
- newest-first deterministic ordering;
- publication, citation, and h-index calculations;
- missing arXiv and missing citation-count fallbacks;
- singular and plural citation labels;
- DOI-based recognition annotations;
- LaTeX escaping for titles and metadata;
- preserving an existing output when generation or compilation fails; and
- the exact homepage button labels, order, destinations, and new-tab behavior.

Final verification will include:

- the complete Python test suite;
- the existing JavaScript tests;
- a live generator run against INSPIRE;
- PDF rendering and visual inspection across every page;
- `hugo --gc --minify`;
- `git diff --check`; and
- a browser check confirming that both homepage buttons open the intended PDFs.

## Acceptance Criteria

The change is complete when:

1. the landing biography shows only `CV` and `Publications`;
2. `Publications` opens the committed local PDF in a new tab;
3. the PDF contains all current INSPIRE works, including arXiv preprints;
4. its opening line reports live publication, citation, and h-index values;
5. each entry uses the approved compact citation format;
6. the two PRLs carry the correct recognition notes;
7. rerunning the documented command refreshes both records and metrics;
8. a failed regeneration cannot overwrite the last valid PDF; and
9. all automated, build, PDF, and browser checks pass.
