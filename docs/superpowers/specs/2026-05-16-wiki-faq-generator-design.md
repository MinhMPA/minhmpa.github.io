# Wiki → FAQ Generator Design

**Status:** Draft, awaiting user review
**Date:** 2026-05-16
**Author:** brainstorming session with Claude (Opus 4.7)

## Goal

Let visitors to the `/contact/` page of `minhmpa.github.io` ask questions about
Minh's papers and topics by expanding the existing deterministic FAQ keyword
matcher with content derived from the local LLM Wiki at
`/Users/nguyenmn/research-wiki/`. No LLM is added in this iteration; the
existing structural extension point for a server-side LLM (documented in
`docs/research-homepage-bot.md`) remains untouched.

## Non-Goals

- No LLM is wired up. Neither a server-side fallback nor a browser-side model.
- No changes to `assets/js/research-bot.js`, `layouts/shortcodes/research-bot.html`,
  or the tests for the matcher.
- No automated CI/CD step. No Netlify build hook. No submodule.
- The wiki is not modified by anything in this design. The flow is one-way.

## High-Level Architecture

```
research-wiki/                                  minhmpa.github.io/
  wiki_records/sources/SRC-NNNN.yaml ─┐   ┌──> data/research_bot.yaml
  wiki_pages/sources/SRC-NNNN-...md   │   │     (hand entries untouched;
                                      ▼   │      wiki entries replaced)
                            scripts/build_faq_from_wiki.py
```

- **Boundary:** the generator reads from the wiki and rewrites only entries with
  the `source: wiki` field in `data/research_bot.yaml`. Hand-authored entries
  (those without that field) are preserved verbatim.
- **Trigger:** invoked manually by the maintainer. The maintainer reviews the
  resulting `git diff` and commits when satisfied.
- **Idempotent and deterministic:** running the generator twice in a row with
  the same wiki produces a byte-identical output. Diffs across runs reflect
  real wiki changes, not generator non-determinism.

## Inputs

### Wiki records

Each `wiki_records/sources/SRC-NNNN.yaml` provides:
- `title`
- `authors` (list)
- `raw_path` (used to extract the canonical arXiv ID via the filename)
- `page_path` (path to the matching summary page; the body source for the answer)
- `published_date` (used only for sort stability fallback)

If a record is missing `title`, `authors`, `raw_path`, or `page_path`, the
generator aborts with a clear error naming the SRC ID.

### Wiki summary pages

Each `wiki_pages/sources/SRC-NNNN-<slug>.md` has a `## Summary` heading
followed by 1–4 paragraphs of prose. The generator captures all prose between
that heading and EOF (excluding any frontmatter, the title block, and the
metadata bullet list above the heading).

### The bucket map

Hardcoded in the generator. Each bucket is
`bucket_id → (display_name, keywords, [SRC-NNNN, ...])`. Membership is
non-exclusive: a paper can appear in multiple buckets. The initial map:

| Bucket | SRC-IDs |
|---|---|
| `field-level-inference` | 0002, 0003, 0004, 0006, 0010, 0014, 0016, 0019, 0020, 0024, 0025, 0026, 0027, 0032, 0033, 0034, 0037 |
| `eft-bias-modeling` | 0001, 0002, 0004, 0005, 0008, 0009, 0026, 0027 |
| `bao-and-large-scale-clustering` | 0012, 0021, 0022, 0023, 0025, 0028, 0029, 0030 |
| `growth-of-structure` | 0013, 0015, 0017, 0018, 0031 |
| `desi-2024` | 0021, 0022, 0023, 0028, 0029, 0030 |
| `kinematic-sz` | 0007 |
| `intrinsic-alignment` | 0011, 0035 |
| `primordial-non-gaussianity` | 0035 |
| `redshift-space-modeling` | 0008 |
| `multi-tracer-fisher` | 0036 |

If a bucket references a SRC ID that does not resolve to a wiki record, the
generator aborts with a clear error naming the missing ID.

## Output: `data/research_bot.yaml`

The generator preserves the existing schema understood by the client-side
matcher in `assets/js/research-bot.js`. Each entry has:
- `id` (string, unique)
- `questions` (list of strings)
- `keywords` (list of strings)
- `answer` (multiline string)
- `url` (optional string)

Wiki-derived entries add three convenience fields the matcher does not
consume: `source: wiki`, `arxiv_id`, and `authored`. They exist for
debugging and for future server-side use. **Precondition**, to be verified
in the first implementation task: the matcher in `assets/js/research-bot.js`
must ignore unknown YAML fields rather than failing or factoring them into
scoring. If it does not, the plan must either (a) tighten the matcher to
ignore unknowns, or (b) drop these extra fields and key off entry id prefix
(`wiki-` / `wiki-bucket-`) instead.

### Per-paper entry (37 total, one per SRC-NNNN)

```yaml
- id: wiki-2403-03220
  source: wiki
  arxiv_id: "2403.03220"
  authored: true
  questions:
    - Tell me about "How much information can be extracted from galaxy clustering at the field level?"
    - What is 2403.03220 about?
    - Tell me about your field-level information paper
  keywords:
    - 2403.03220
    - galaxy clustering
    - field level
    - information
    - sigma_8
    - Nguyen
  answer: >
    Minh and collaborators (arXiv:2403.03220) ask how much cosmological
    information can be extracted from nonlinear galaxy clustering by
    performing optimal Bayesian field-level inference of sigma_8 from
    simulated halos, using the LEFTfield forward model.
  url: https://arxiv.org/abs/2403.03220
```

Generation rules:

- `id`: `wiki-<arxiv_id with dot replaced by dash>` (e.g., `wiki-2403-03220`).
- `arxiv_id`: the bare arXiv ID extracted from `raw_path` (drop any trailing
  `vN` version).
- `authored`: `true` iff any author in the record matches one of
  `{"Nhat-Minh Nguyen", "N. Nguyen", "Minh Nguyen", "Nhat Minh Nguyen"}`,
  case-insensitive and with diacritics stripped.
- `questions[0]`: `Tell me about "<title>"`.
- `questions[1]`: `What is <arxiv_id> about?`.
- `questions[2]`: a curated topic-flavored phrasing, generated only when the
  paper appears in exactly one bucket. Templates per bucket are listed below.
- `keywords`: union of (a) the arxiv ID, (b) the surname `Nguyen` if authored,
  (c) the canonical keywords from every bucket the paper belongs to, (d)
  content words from the title (length ≥ 4, with the stoplist below removed),
  then deduplicated, lowercased, and truncated to 12 entries.
- `answer`: see "Answer distillation" below.
- `url`: `https://arxiv.org/abs/<arxiv_id>`.

#### Bucket-specific `questions[2]` templates

When a paper belongs to exactly one bucket:

| Bucket | `questions[2]` template |
|---|---|
| `field-level-inference` | `Tell me about your field-level inference paper` |
| `eft-bias-modeling` | `Tell me about your work on EFT galaxy bias` |
| `bao-and-large-scale-clustering` | `Tell me about your BAO paper` |
| `growth-of-structure` | `Tell me about your work on the growth of structure` |
| `desi-2024` | `Tell me about your DESI 2024 paper` |
| `kinematic-sz` | `Tell me about your work on the kinematic SZ effect` |
| `intrinsic-alignment` | `Tell me about your work on galaxy shapes and sizes` |
| `primordial-non-gaussianity` | `Tell me about your work on primordial non-Gaussianity` |
| `redshift-space-modeling` | `Tell me about your work on the EFT likelihood in redshift space` |
| `multi-tracer-fisher` | `Tell me about your multi-tracer forecast` |

When the paper appears in multiple buckets (most LEFTfield papers do), the
generator emits only `questions[0]` and `questions[1]`.

#### Stoplist for keyword extraction

A fixed stoplist of common English words plus a few cosmology-talk fillers:

```
a, an, the, and, or, but, of, for, with, without, to, from, in, on, at, by,
as, is, are, was, were, be, been, has, have, had, do, does, did, this, that,
these, those, it, its, into, onto, over, under, between, using, used, via,
based, model, models, paper, papers, study, analysis, results, new,
beyond, towards, toward, about, what, which, who, where, when, why, how
```

The intent is to keep substantive cosmology words ("field", "inference",
"bias", "BAO", "redshift", "growth") and discard scaffolding.

### Answer distillation

The answer text is an excerpt from the wiki summary, not a paraphrase. This
keeps the generator deterministic and audit-friendly.

1. Locate `## Summary` in the page. Take all text below it.
2. Strip leading/trailing whitespace and any trailing `_PDF could not be read._`-style
   placeholders. If the *entire* summary body is one of the known failure
   markers, emit the fallback answer (see below).
3. Split on sentence boundaries (`re.split(r'(?<=[.!?])\s+')`). Trim
   any inline LaTeX-y residues by collapsing runs of `[$\{\}^_\\]+[A-Za-z]*`
   to a single space — purely cosmetic; we still pass through almost
   everything.
4. Walk sentences in order, accumulating words. Stop at the first boundary
   where cumulative word count ≥ 60. If the first sentence alone already
   exceeds 80 words, truncate it at the 80th word and append `…`.
5. Prepend an author-tone prefix:
   - Authored: `Minh and collaborators (arXiv:NNNN.NNNNN): <excerpt>`
   - Not authored: `<first-author surname> et al. (arXiv:NNNN.NNNNN): <excerpt>`

Fallback answer (when no usable summary text exists):

```
<title> by <first author> et al. (arXiv:NNNN.NNNNN). A summary is not yet
available; see the arXiv abstract.
```

The fallback intentionally omits "Minh and collaborators" framing even for
authored papers, because we want visitors to see a clear "this is incomplete"
signal rather than an authoritative-sounding stub.

Note: with SRC-0009 dropped from `redshift-space-modeling`, that bucket has
exactly one paper (SRC-0008). It still earns a bucket entry — a visitor
asking "do you work on redshift-space modeling?" gets a deterministic yes
pointing at the EFT-redshift-space paper, instead of falling back to the
generic no-match string.

### Topic-bucket entry (10 total, one per bucket)

```yaml
- id: wiki-bucket-field-level-inference
  source: wiki
  questions:
    - Tell me about field-level inference
    - What's your work on field-level inference?
    - What is FLI?
  keywords:
    - field-level inference
    - FLI
    - LEFTfield
    - Bayesian
    - posterior
    - forward model
  answer: >
    Minh works on field-level Bayesian inference of cosmological parameters
    from nonlinear galaxy clustering, primarily via the LEFTfield EFT-based
    forward model. Relevant papers include arXiv:1808.02002, 1906.07143,
    2403.03220, and 2407.01524.
  url: /research/
```

Bucket answer rules:

- The bucket-specific intro sentence is hand-curated in the script (per-bucket
  template). It is *not* derived from the wiki.
- The "Relevant papers" list is generated: pick up to 5 SRC-IDs from the bucket,
  prioritising authored papers, ordered by `published_date` descending, and
  format as `arXiv:NNNN.NNNNN` joined with commas. If the bucket has > 5
  papers, append `and <N> others — see /research/`.
- `url` is always `/research/` for bucket entries (per the earlier decision
  to send paper-specific links to arxiv but topic links to the internal page).

Per-bucket curated text and keywords are codified in a table inside the
generator script (`BUCKETS` dict).

### Co-existence with hand entries

The existing `data/research_bot.yaml` already contains hand-authored entries
including a `field-level-inference` topic entry. The new wiki bucket entry
uses the id `wiki-bucket-field-level-inference` and so does not collide.

Both entries are visible to the matcher. The hand entry's keywords are general
("field-level inference", "FLI", "Bayesian inference", "simulations", ...);
the wiki bucket entry's keywords overlap but add specific arxiv IDs and
paper-flavored terms. Per the matcher's scoring rule, the entry that wins
depends on the visitor's query. We are explicitly designing for this overlap:
short generic queries surface the hand entry's polished answer; queries
that mention an arxiv ID or paper title surface the wiki entry. The
implementation plan must include a regression test that this ordering still
holds after the generator runs.

## Generator: `scripts/build_faq_from_wiki.py`

Runtime: Python 3, stdlib + `pyyaml` (already installed in the repo via
operator usage; pin in `scripts/requirements.txt` if not).

### Invocation

```bash
python3 scripts/build_faq_from_wiki.py            # defaults to /Users/nguyenmn/research-wiki/
python3 scripts/build_faq_from_wiki.py /custom/path/to/wiki
```

Exit codes:
- `0`: success; either wrote a new `data/research_bot.yaml` or printed `no changes`.
- `2`: usage/argument error.
- `3`: wiki root invalid, missing required structure, or no SRC records found.
- `4`: a SRC record is malformed (missing required field).
- `5`: a bucket map entry references an unknown SRC ID.

### Pipeline

1. Resolve wiki root; validate `wiki_records/sources/`, `wiki_pages/sources/`
   are present.
2. Load every `SRC-*.yaml`. Build an `arxiv_id → record` map.
3. Load every corresponding summary page; extract the `## Summary` body.
4. Build per-paper entries (sorted by arxiv ID ascending).
5. Build topic-bucket entries (sorted by bucket id; reuses per-paper records
   already loaded, so it can't desynchronize with paper data).
6. Parse the existing `data/research_bot.yaml` into a list. Drop entries with
   `source == "wiki"`. Append new wiki entries (per-paper first, then
   buckets). Write back with `yaml.safe_dump(stream, sort_keys=False,
   allow_unicode=True, width=80)`.
7. Print a summary to stdout: number of per-paper entries written, number of
   bucket entries, total file size, and whether the result is unchanged from
   the previous run.

### What the script does NOT do

- It does not call any LLM. The answer text is an excerpt of the wiki summary
  you have already reviewed.
- It does not modify the matcher JS, the shortcode, or any test files.
- It does not commit anything.
- It does not write to the wiki.

### Edge cases (explicit)

- **Summary body is a failure marker** (`_PDF could not be read._`,
  `_PDF text extraction was unusable._`, or `_Not yet written._`) → emit a
  fallback answer (see "Answer distillation").
- **Single very-long sentence** → truncate at 80 words and append `…`.
- **arXiv ID with version suffix** (e.g., `1611.09787v5`) → strip the `vN`
  for both the `arxiv_id` field and the URL.
- **Multiple authors named "Nguyen"** → the surname `Nguyen` still appears in
  keywords, but it's just one of up to 12 — no special-casing needed.
- **Title containing double quotes** → YAML emitter escapes correctly; verify
  with a unit test using a fabricated record.

## Testing

The implementation must pass three test layers before the design is met:

1. **Existing matcher tests stay green.** Run
   `node --test tests/research-bot-matcher.test.mjs` after regeneration.
2. **New generator unit tests** under `tests/build_faq_from_wiki.test.py` (or
   `.mjs` wrapper if the repo prefers node-only tests; implementation plan
   decides):
   - Authorship detection on the four normalised name forms.
   - Excerpt-and-truncate on a synthetic summary with a 120-word first sentence.
   - Fallback answer when the summary body is `_Not yet written._`.
   - Idempotency: running the generator twice produces a byte-identical file.
   - Bucket-with-unknown-SRC-ID aborts with exit code 5.
3. **End-to-end matcher regression**: after running the generator against the
   real wiki, dispatch a small set of queries to the matcher (via the existing
   test harness) and assert the expected entry wins:
   - `"field-level inference"` (short, generic) → hand entry.
   - `"tell me about 2403.03220"` → `wiki-2403-03220` per-paper entry.
   - `"tell me about your DESI 2024 BAO paper"` → one of the DESI-2024
     per-paper entries (any of the three is acceptable).
   - `"who won the world cup"` → no match (fallback).

The implementation plan must wire (2) and (3) into the same CI lane that
already runs (1).

## Operator workflow after this is built

1. Update the wiki (`/llm-wiki ...`) as usual.
2. From inside the `minhmpa.github.io` repo:
   `python3 scripts/build_faq_from_wiki.py`
3. `git diff data/research_bot.yaml` — review the changes.
4. If acceptable: `hugo server -D`, walk the manual UI checklist in
   `docs/research-homepage-bot.md`, then commit.
5. Push. Netlify rebuilds.

The bucket map and the bucket-specific text live inside the generator script.
Adjusting them is a code change to `scripts/build_faq_from_wiki.py`, not a
data change.

## Open questions

- Should `pyyaml` be vendored, or are you happy adding a `scripts/requirements.txt`?
  (Implementation plan will choose; default is the requirements file.)
- The repo's existing test runner is `node --test`. Are you OK with a Python
  test file for the generator, or should the generator's tests be ported to
  node? (Implementation plan will choose; default is Python, since the
  generator itself is Python.)

Both can be deferred to the implementation plan stage.
