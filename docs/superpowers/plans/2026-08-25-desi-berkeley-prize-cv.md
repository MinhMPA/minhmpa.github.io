# DESI Berkeley Prize CV Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the DESI Collaboration's 2026 AAS Lancelot M. Berkeley Prize to the public academic CV and refresh the PDF served by the website landing page.

**Architecture:** The public CV remains authored once in `/Users/nguyenmn/academic-cv/index.md` and rendered by Jekyll with the existing `research-cv` layout. A headless Chrome print of that rendered page becomes the canonical academic CV PDF, which is stored in the academic CV repository and copied byte-for-byte to the Hugo website's stable download path.

**Tech Stack:** Markdown with embedded HTML, Jekyll, existing print CSS, headless Google Chrome, Poppler (`pdfinfo`, `pdftotext`, `pdftoppm`), Hugo

**Spec:** `docs/superpowers/specs/2026-08-25-desi-berkeley-prize-cv-design.md`

## Global Constraints

- Use the approved one-line wording exactly: "AAS Lancelot M. Berkeley Prize (DESI Collaboration), recognizing BAO results from DESI's first three years, including DESI 2024 VI."
- Display the year as `2026` and place the entry before the 2024 Buchalter Cosmology Prize.
- Link the prize title to the official AAS prize page and `DESI 2024 VI` to its existing JCAP publication URL.
- Do not change `/Users/nguyenmn/academic-cv/full-cv.md`, application-specific CVs, collaboration dates, publication wording, CSS, or the landing-page URL.
- Preserve all unrelated working-tree changes in both repositories.

## File responsibilities

- `/Users/nguyenmn/academic-cv/index.md`: canonical public academic CV content.
- `/Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf`: canonical generated PDF for the academic CV repository.
- `/Users/nguyenmn/minhmpa.github.io/static/cv/Nhat-Minh-Nguyen-academic-cv.pdf`: byte-identical landing-page download artifact.
- `/Users/nguyenmn/minhmpa.github.io/content/_index.md`: existing landing-page link; inspect only.

---

### Task 1: Add the collaboration-wide award to the public CV source

**Files:**
- Modify: `/Users/nguyenmn/academic-cv/index.md:20-27`
- Test: content assertions against `/Users/nguyenmn/academic-cv/index.md`

**Interfaces:**
- Consumes: the existing `.entry`, `.entry-title`, and `.entry-date` HTML structure under `## Selected Honors`.
- Produces: a linked 2026 award entry that the Jekyll build and PDF print consume.

- [ ] **Step 1: Run the content assertion before editing**

```bash
ruby -e 's = File.read("index.md"); required = ["AAS Lancelot M. Berkeley Prize (DESI Collaboration)", "recognizing BAO results from DESI\x27s first three years, including", ">DESI 2024 VI</a>.", "<div class=\"entry-date\">2026</div>"]; missing = required.reject { |text| s.include?(text) }; abort("missing award content: #{missing.join(" | ")}") unless missing.empty?'
```

Expected: FAIL with `missing award content` because the award has not yet been added.

- [ ] **Step 2: Add the minimal approved entry**

Insert this block immediately below `## Selected Honors`:

```html
<div class="entry">
<div><span class="entry-title"><a href="https://aas.org/grants-and-prizes/lancelot-m-berkeley-new-york-community-trust-prize-meritorious-work-astronomy">AAS Lancelot M. Berkeley Prize (DESI Collaboration)</a></span>, recognizing BAO results from DESI's first three years, including <a href="https://iopscience.iop.org/article/10.1088/1475-7516/2025/02/021">DESI 2024 VI</a>.</div>
<div class="entry-date">2026</div>
</div>
```

- [ ] **Step 3: Re-run the content assertion and verify ordering**

```bash
ruby -e 's = File.read("index.md"); required = ["AAS Lancelot M. Berkeley Prize (DESI Collaboration)", "recognizing BAO results from DESI\x27s first three years, including", ">DESI 2024 VI</a>.", "<div class=\"entry-date\">2026</div>"]; missing = required.reject { |text| s.include?(text) }; abort("missing award content: #{missing.join(" | ")}") unless missing.empty?; abort("award is not before Buchalter") unless s.index("AAS Lancelot") < s.index("Buchalter Cosmology Prize")'
```

Expected: exit 0 with no output.

- [ ] **Step 4: Build the Jekyll site and inspect generated HTML**

```bash
RBENV_VERSION=3.2.2 jekyll build --destination /tmp/academic-cv-site
rg -n -F 'AAS Lancelot M. Berkeley Prize (DESI Collaboration)' /tmp/academic-cv-site/index.html
rg -n -F 'DESI 2024 VI</a>.' /tmp/academic-cv-site/index.html
```

Expected: Jekyll 3.10.0 exits 0; both searches return the new entry in the generated page.

---

### Task 2: Generate and visually verify the refreshed PDF

**Files:**
- Modify: `/Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf`
- Create temporarily: `/tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf`
- Create temporarily: `/tmp/academic-cv-pdf/rendered/page-*.png`

**Interfaces:**
- Consumes: `/tmp/academic-cv-site/index.html` produced by Task 1 and the existing `media/research-cv-print.css` loaded by that page.
- Produces: a visually verified PDF containing the exact approved award entry.

- [ ] **Step 1: Print the generated HTML with the existing browser/PDF pipeline**

```bash
mkdir -p /tmp/academic-cv-pdf/rendered
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' --headless --disable-gpu --no-pdf-header-footer --user-data-dir=/tmp/academic-cv-chrome-profile --print-to-pdf=/tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf file:///tmp/academic-cv-site/index.html
```

Expected: Chrome reports that it wrote `/tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf`.

- [ ] **Step 2: Verify PDF metadata and text**

```bash
pdfinfo /tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf
pdftotext -layout /tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf - | rg -n -C 2 'AAS Lancelot M. Berkeley Prize|DESI 2024 VI|SELECTED HONORS'
```

Expected: Letter-sized PDF with readable text showing the 2026 award under `SELECTED HONORS` and the `DESI 2024 VI` reference.

- [ ] **Step 3: Render every page for visual inspection**

```bash
pdftoppm -png /tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf /tmp/academic-cv-pdf/rendered/page
```

Expected: one PNG per PDF page. Inspect every PNG for clipping, overlap, broken page transitions, black boxes, missing glyphs, or illegible text.

- [ ] **Step 4: Install the verified canonical PDF in the academic CV repository**

```bash
cp /tmp/academic-cv-pdf/Nhat-Minh-Nguyen-academic-cv.pdf /Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf
```

- [ ] **Step 5: Commit only the public CV source and canonical PDF**

```bash
git -C /Users/nguyenmn/academic-cv add index.md cv/Nhat-Minh-Nguyen-academic-cv.pdf
git -C /Users/nguyenmn/academic-cv commit -m "Add DESI Berkeley Prize to CV"
```

Expected: the commit contains exactly `index.md` and `cv/Nhat-Minh-Nguyen-academic-cv.pdf`; pre-existing JPL and untracked changes remain untouched.

---

### Task 3: Refresh and verify the landing-page download

**Files:**
- Modify: `/Users/nguyenmn/minhmpa.github.io/static/cv/Nhat-Minh-Nguyen-academic-cv.pdf`
- Inspect: `/Users/nguyenmn/minhmpa.github.io/content/_index.md:16-17`

**Interfaces:**
- Consumes: the verified canonical PDF from Task 2.
- Produces: the same PDF bytes at the Hugo landing page's stable `/cv/Nhat-Minh-Nguyen-academic-cv.pdf` path.

- [ ] **Step 1: Copy the verified PDF to the Hugo static asset path**

```bash
cp /Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf /Users/nguyenmn/minhmpa.github.io/static/cv/Nhat-Minh-Nguyen-academic-cv.pdf
```

- [ ] **Step 2: Prove the two PDF artifacts are identical and the link is unchanged**

```bash
shasum -a 256 /Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf /Users/nguyenmn/minhmpa.github.io/static/cv/Nhat-Minh-Nguyen-academic-cv.pdf
rg -n -F 'url: /cv/Nhat-Minh-Nguyen-academic-cv.pdf' /Users/nguyenmn/minhmpa.github.io/content/_index.md
```

Expected: the SHA-256 hashes match and the landing page still points to the stable PDF URL.

- [ ] **Step 3: Build the Hugo website**

```bash
hugo --gc --minify
```

Expected: exit 0 with no build errors.

- [ ] **Step 4: Verify the built site contains the refreshed PDF**

```bash
shasum -a 256 static/cv/Nhat-Minh-Nguyen-academic-cv.pdf public/cv/Nhat-Minh-Nguyen-academic-cv.pdf
pdftotext -layout public/cv/Nhat-Minh-Nguyen-academic-cv.pdf - | rg -n -C 2 'AAS Lancelot M. Berkeley Prize|DESI 2024 VI'
git diff --check
git status --short
```

Expected: source and built PDFs have matching hashes; built PDF text contains the award; no whitespace errors; only the planned PDF and pre-existing unrelated changes remain uncommitted.

- [ ] **Step 5: Commit only the implementation plan and landing-page PDF**

```bash
git add docs/superpowers/plans/2026-08-25-desi-berkeley-prize-cv.md static/cv/Nhat-Minh-Nguyen-academic-cv.pdf
git commit -m "Update CV with DESI Berkeley Prize"
```

Expected: the commit contains exactly the implementation plan and refreshed landing-page PDF; the modified avatar and existing untracked plan remain untouched.
