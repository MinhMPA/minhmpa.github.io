# DESI Berkeley Prize CV Update Design

## Goal

Add the DESI Collaboration's 2026 AAS Lancelot M. Berkeley Prize to Nhat-Minh Nguyen's public academic CV and refresh the PDF downloaded from the website landing page.

## Award wording

Use this one-line entry under **Selected Honors**, before the 2024 Buchalter Cosmology Prize:

> AAS Lancelot M. Berkeley Prize (DESI Collaboration), recognizing BAO results from DESI's first three years, including DESI 2024 VI.

Display the year as **2026**. Link the prize title to the official AAS prize page and link **DESI 2024 VI** to the published paper already listed under **Selected Publications**.

This wording attributes the prize to the full DESI Collaboration and connects the recognition to Nguyen's existing publication record without presenting the prize as an individual award. The existing **Survey Collaborations** section provides the membership context.

## Files and artifacts

- Edit `/Users/nguyenmn/academic-cv/index.md`, the public HTML CV source.
- Do not change `/Users/nguyenmn/academic-cv/full-cv.md`, which is the archived long-form CV.
- Rebuild `/Users/nguyenmn/academic-cv/cv/Nhat-Minh-Nguyen-academic-cv.pdf` from the rendered public CV.
- Copy the rebuilt PDF to `/Users/nguyenmn/minhmpa.github.io/static/cv/Nhat-Minh-Nguyen-academic-cv.pdf`, which is the file linked by the landing-page **Download CV** button.
- Do not change the landing-page URL because it already points to the correct stable filename.

## Verification

1. Build the Jekyll CV site and confirm the new honor, year, and both links in the generated HTML.
2. Generate the PDF from the same rendered page using the existing print stylesheet.
3. Confirm the two public PDF files are byte-identical.
4. Extract PDF text to verify the award wording and year.
5. Render all PDF pages to images and inspect them for clipping, overlap, broken page transitions, or illegible text.
6. Build the Hugo website and confirm the landing-page download still targets the refreshed PDF.

## Non-goals

- No changes to other CV content, collaboration dates, publication wording, CSS, or page layout unless a minimal adjustment is required to prevent a rendering defect.
- No changes to application-specific CVs or PDFs.
