# Minh Nguyen Homepage

This site is now built with Hugo and the Hugo Blox Academic CV theme, and is deployed through GitHub Pages.

## Local Preview

Run:

```bash
hugo server -D
```

Then open:

```text
http://localhost:1313
```

Hugo will live-reload the page whenever you edit content or config.

## Local Build Check

Run:

```bash
hugo --gc --minify
```

This is the quickest way to catch build errors before pushing.

## Publication page and monthly updates

The **Publication** navigation tab, immediately after Travel, opens
`/publications/`. It lists every work returned for
[INSPIRE author 1986925](https://inspirehep.net/authors/1986925?ui-citation-summary=true),
newest first, in the CV's author–title–journal/preprint format. Journal DOI
links replace arXiv preprint links when a journal reference becomes available.
Author order is preserved; collaboration papers use the collaboration name.

The page includes a download link to the publication-list PDF. The homepage
keeps the CV button; publications are reached through the navigation tab.

The **Deploy Hugo Site to GitHub Pages** workflow refreshes the page and PDF on the
first of each month at **02:17 UTC (09:17 Viet Nam time)**, and on ordinary site
deployments. It downloads the complete list with citation counts once, validates
it, generates both formats from the same records and update date, and deploys
the refreshed website. No API key or local computer is needed. The generated
page and PDF are updated in the deployed site; monthly runs do not commit to the
protected source branch. Each run retains an `inspire-publications` artifact
containing the generated page, PDF, and their source records.

To update it manually in GitHub:

1. Open [the website workflow](https://github.com/MinhMPA/minhmpa.github.io/actions/workflows/jekyll.yml).
2. Choose **Run workflow**, select **master**, and click **Run workflow**.
3. Wait for both the build and deployment to finish.

To refresh both local copies (Python 3.10 or newer, plus the LaTeX dependencies below):

```bash
python3 scripts/build_publications_page.py --snapshot-output /tmp/publications-source.json
python3 scripts/build_publications_pdf.py --from-snapshot /tmp/publications-source.json
hugo --gc --minify
```

Both generators accept `--from-snapshot /tmp/publications-source.json` to
reproduce the saved records and update date offline.
Failed downloads, incomplete lists, duplicate records, or missing citation data
stop the refresh before replacing the existing page. A failed PDF compilation
also stops the workflow before deployment. Failed workflow runs do
not deploy, leaving the last successful website available. Pull requests and
manual runs on other branches build for review without publishing.

GitHub can delay scheduled runs and
[disables schedules after 60 days without repository activity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
If that happens, re-enable this workflow in Actions. The schedule becomes active
once this change is merged into the default branch.

## Publications PDF

The PDF linked from the Publication tab is generated from INSPIRE author record
`1986925`. Install `latexmk`, LuaLaTeX, the LaTeX packages used by the generator,
and the New Computer Modern fonts. On Ubuntu, these are provided by `latexmk`,
`texlive-luatex`, `texlive-latex-extra`, and `texlive-fonts-extra`.
To refresh only the PDF directly from INSPIRE, run:

```bash
python scripts/build_publications_pdf.py
```

The command refreshes
`static/publications/Nhat-Minh-Nguyen-publications.pdf`. It reports the live
publication, citation, and h-index totals. Generation happens in a temporary
directory, so a failed API request or LaTeX build leaves the last valid PDF
untouched.

## Review Workflow

For a quick review after any change:

1. Run `hugo server -D`.
2. Open `http://localhost:1313`.
3. Check the changed page on desktop and mobile widths.
4. Run `hugo --gc --minify` before committing.

If you want an external review from Codex, ask for a review after your edits and point to the changed files or commit.

## Guest View

To view the site as a public visitor:

1. Push your changes to GitHub.
2. Wait for the GitHub Pages workflow to finish.
3. Open `https://minhmpa.github.io/` in an incognito/private window.

That is the closest match to what a guest will actually see.
