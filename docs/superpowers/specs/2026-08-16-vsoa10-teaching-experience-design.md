# VSOA10 Teaching Experience Design

## Goal

Add VSOA10: Cosmology as a teaching experience on the homepage's Teach page, using the supplied `teach_profile.jpg` photograph to showcase the experience.

## Content Structure

Keep the existing `Teaching` section and divide its experiences into two newest-first subsections:

1. `VSOA10: Cosmology`
2. `Michigan Math and Science Scholars (MMSS)`

The VSOA10 subsection will state that Minh Nguyen taught the three-part Large-scale Structure lecture series and led its hands-on session at ICISE in Quy Nhon, Viet Nam, during July–August 2026. The event title will link to the official VSOA10 program.

The existing MMSS teaching text and student-feedback image will remain, reorganized beneath the MMSS subsection heading without changing their meaning.

## Image Handling

Copy `public/images/teach_profile.jpg` into `static/images/teach_profile.jpg`, because `static/images/` is the repository's tracked source for Hugo-served page images. The VSOA10 subsection will reference `/images/teach_profile.jpg` and use descriptive alt text identifying Minh Nguyen teaching at VSOA10 at ICISE.

## Presentation

Use the Teach page's existing Markdown and centered full-width image pattern. Do not introduce custom cards, CSS, or layout overrides. Place the VSOA10 photograph directly after its description, followed by the MMSS subsection and its existing image.

## Verification

- Run `hugo --gc --minify`.
- Confirm the generated Teach page contains the VSOA10 program link and `/images/teach_profile.jpg`.
- Confirm the copied source image matches the supplied file.
- Preserve the unrelated uncommitted author-avatar change.
