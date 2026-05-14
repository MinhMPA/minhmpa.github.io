# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Personal academic website for Minh Nguyen (cosmologist at Kavli IPMU). Built with Hugo and the Hugo Blox (Academic CV) theme, deployed via GitHub Pages.

## Commands

- **Local preview:** `hugo server -D` → http://localhost:1313 (live-reload)
- **Build check:** `hugo --gc --minify` (catch errors before pushing)
- **Hugo version:** 0.149.0 (set in `.github/workflows/jekyll.yml`; netlify.toml uses 0.126.1 but deployment is via GitHub Pages)

## Architecture

- **Hugo Modules:** Theme pulled via Go modules (`go.mod`). Two HugoBlox modules: `blox-plugin-netlify` and `blox-tailwind`.
- **Config:** Split across `config/_default/` — `hugo.yaml` (core), `params.yaml` (site appearance/SEO), `menus.yaml` (navbar), `languages.yaml`, `module.yaml` (module imports and mounts).
- **Content sections:** `content/` has `authors/admin/` (bio), `research/`, `travel/`, `teach/`, `outreach/`, `blog/`, `contact/`. The homepage (`content/_index.md`) is a landing page using the `resume-biography-3` block.
- **Layout overrides:** `layouts/` contains custom overrides of the HugoBlox theme — notably `partials/blox/resume-biography-3.html` (landing bio block), `partials/page-avatar.html`, `partials/portrait-background.html`, and `blog/list.html`.
- **Static assets:** `static/images/` for page images, `static/cv/` for CV PDF. `assets/media/` for landing page background images.
- **Deployment:** GitHub Actions workflow (`.github/workflows/jekyll.yml`) builds Hugo and deploys to GitHub Pages on push to master/main.

## Key Patterns

- Blog posts use Hugo page bundles: each post is a directory under `content/blog/` with `index.md` and co-located assets.
- Section pages (`research/`, `teach/`, etc.) are single `index.md` files using raw HTML in markdown (unsafe rendering enabled in `hugo.yaml`).
- Profile images are referenced from `static/images/` in layout partials — if changing avatar images, check both `content/authors/admin/avatar.png` and the page-specific profile images in `static/images/`.

## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature-slug>/` in this repo. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
