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
