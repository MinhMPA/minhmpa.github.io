# Wiki → FAQ generator — operator notes

This document covers the `scripts/build_faq_from_wiki.py` script that
expands the research-bot FAQ from the local LLM wiki.

## When to run

Run after the wiki at `/Users/nguyenmn/research-wiki/` changes in any
way the visitor-facing FAQ should reflect:

- new paper added to the wiki
- summary rewritten
- bucket map updated (this is a code change to the generator itself)

## How to run

From the repo root:

    python3 scripts/build_faq_from_wiki.py

This rewrites:

- `data/research_bot.yaml` (the Hugo data file that ships to the browser)
- `tests/fixtures/research_bot.json` (the JSON mirror used by node tests)

It never modifies the wiki and never touches hand-authored FAQ entries.

If `python3` on your machine cannot install PyYAML (e.g. macOS with PEP 668
externally-managed Python), use the project-local venv: `.venv/bin/python
scripts/build_faq_from_wiki.py`.

## Review workflow

1. `git diff data/research_bot.yaml` — confirm hand entries' *content* is
   unchanged. (Whitespace on hand entries was normalized on the very first
   generator run; subsequent runs are byte-stable. If you see content
   changes to a hand entry, something is wrong.)
2. `node --test tests/research-bot-matcher.test.mjs` — green.
3. `python3 -m unittest discover -s tests -v` (or `.venv/bin/python -m unittest
   discover -s tests -v`) — green.
4. `hugo server -D`, walk the manual UI checklist in
   `docs/research-homepage-bot.md`.
5. Commit and push.

## Extending the bucket map

The bucket map lives at the top of `scripts/build_faq_from_wiki.py`. To
add a new bucket:

1. Add an entry to `BUCKETS` (id → list of SRC-IDs).
2. Add an entry to `BUCKET_TEMPLATES` (the human prose, with `{papers}`
   placeholder).
3. Add an entry to `BUCKET_KEYWORDS`.
4. Add an entry to `BUCKET_QUESTIONS`.
5. Optionally add an entry to `BUCKET_PAPER_QUESTION` to give papers in
   that bucket a third, topic-flavored question phrasing.
6. Re-run the generator. Update tests in
   `tests/test_build_faq_from_wiki.py` if the new bucket should be in
   the synthetic-wiki test set.

## Matcher behavior

The matcher in `assets/js/research-bot.js` gives any entry whose `source`
field is *not* `"wiki"` a +50 score bonus when it has positive content
match. This preserves the design intent that hand-authored entries win
short generic queries while wiki entries win paper-specific queries
(e.g., a query that names an arxiv ID).

If you ever want a wiki entry to win over a hand entry on the same
generic query, edit the matcher constant — or simply remove the
overlapping hand entry.

## Quality caveats

Wiki summaries are AI-generated; the first 1–2 sentences of each summary
are excerpted verbatim into the FAQ answer field. If a summary has LaTeX
residues (e.g., `sigma_8`, `σ_8`, `Ω_m(a)^{γ_L}`), they will appear in
the answer text as-is. To improve a specific answer, edit the wiki
summary at `/Users/nguyenmn/research-wiki/wiki_pages/sources/SRC-NNNN-*.md`
and re-run the generator.
