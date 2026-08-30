# Cleaner Professional Homepage Design

## Goal

Make Minh Nguyen's homepage cleaner, easier to scan, and more professional for a balanced academic and public audience without changing the landing page's established visual identity.

The audience includes academic collaborators, funding agencies, hiring committees, general visitors, and prospective students or postdocs. The page should explain the research plainly, establish scholarly credibility quickly, and make the next useful actions obvious.

## Approved Direction

Use a theme-preserving hierarchy cleanup. Retain the current cosmic background, dark palette, portrait treatment, pronunciation, social icons, typography, two-column desktop composition, and stacked mobile composition.

This is an editorial refinement, not an aesthetic redesign. Do not add cards, a new visual section, a new color system, new imagery, new JavaScript, or a replacement landing-page component.

## Navigation

Navigation labels name destinations, so they use nouns rather than action verbs.

The final navigation is:

1. Research
2. Travel
3. Teaching
4. Visualization
5. Outreach
6. Blog
7. Contact

`Visualization` remains a main navigation component. Rename `Teach` to `Teaching`. Remove `Bio` because the site name/logo already links to the homepage.

## Hero Identity

Replace the technical research-area role with the plain professional identity `Cosmologist`.

Give the two current appointments equal prominence beneath it:

- `Kavli IPMU Fellow, University of Tokyo`, linked to `https://www.ipmu.jp/en`
- `Faculty and Group Leader, IFIRSE at ICISE`, linked to `https://ifirse.icise.vn/astrophysics-cosmology-group.html`

Keep the name pronunciation, portrait, and existing social profile icons unchanged.

## Homepage Copy

Replace the current biography, career chronology, and `Research Program` list with the following three short paragraphs:

> I am a cosmologist developing forward-modeling and field-level Bayesian inference methods for galaxy surveys. I use them to extract more information from cosmic structure and test gravity, dark energy, and primordial physics.
>
> My work includes the first [4-sigma evidence for suppressed late-time growth of large-scale structure](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.131.111001) and [field-level inference methods](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.133.221006) that extract substantially more cosmological information than standard analyses. These results appeared in two *Physical Review Letters* papers; the suppressed-growth result received coverage in [*Scientific American*](https://www.scientificamerican.com/article/a-possible-crisis-in-the-cosmos-could-lead-to-a-new-understanding-of-the-universe/) and [*New Scientist*](https://www.newscientist.com/article/2391414-the-universes-evolution-seems-to-be-slowing-and-we-dont-know-why/), while the field-level inference work was recognized with the [2024 Buchalter Cosmology Prize](https://www.buchaltercosmologyprize.org/).
>
> I welcome inquiries from prospective students and postdocs, and from researchers interested in collaboration.

The five existing destination URLs embedded in the two PRL references, two media references, and the Buchalter Prize reference must remain exactly as written above.

## Primary Actions

Render four actions immediately after the short biography, using the existing CV button's visual style:

| Label | Destination | New tab |
|---|---|---|
| Research | `/research/` | No |
| Publications | `https://scholar.google.com/citations?hl=en&user=Wfr8DzAAAAAJ` | Yes |
| Download CV | `/cv/Nhat-Minh-Nguyen-academic-cv.pdf` | Yes |
| Contact | `/contact/` | No |

The actions wrap onto additional lines when necessary. Internal navigation remains in the current tab. Google Scholar and the CV open in a new tab with `rel="noopener"`.

## Interests, Education, and Metadata

Do not render the Interests or Education panels on the homepage. Preserve the `interests`, `education`, and `work` data in `content/authors/admin/_index.md`; this change affects presentation, not the underlying academic profile data.

The landing block opts out through explicit `hide_interests` and `hide_education` flags. The custom biography partial continues to render those panels by default for any use that does not set the flags.

## Implementation Boundaries

### `content/authors/admin/_index.md`

- Change the role to `Cosmologist`.
- Represent the Kavli IPMU and IFIRSE appointments equally in the organizations list.
- Replace the rendered biography with the approved copy.
- Preserve the existing Interests, Education, and Work metadata.

### `content/_index.md`

- Replace the single CV-button configuration with the four approved actions.
- Set `hide_interests: true` and `hide_education: true` for the homepage block.
- Preserve the existing avatar, background, brightness, sizing, position, spacing, and dark CSS class.

### `layouts/partials/blox/resume-biography-3.html`

- Preserve the present profile and biography markup and styling.
- Render a wrapping list of configured actions using the existing button classes.
- Respect each action's explicit new-tab behavior.
- Retain compatibility with the existing singular `button` field so the local override remains safe for another landing-block use.
- Suppress Interests and Education only when the corresponding hide flags are true.
- Avoid outputting an empty lower grid when both panels are hidden.

### `config/_default/menus.yaml`

- Remove `Bio`.
- Rename `Teach` to `Teaching`.
- Preserve `Visualization` as a top-level item and keep all other destinations and their relative order.

## Accessibility and Responsive Behavior

- Every action uses descriptive visible text rather than an icon alone.
- External and PDF actions use `target="_blank" rel="noopener"`.
- The action container wraps on narrow widths without horizontal overflow.
- Existing heading order, image alternative text, keyboard focus styles, and responsive column behavior remain intact.
- The homepage must remain readable in both light and dark system modes, although its configured landing block remains visually dark.

## Verification

Add an automated homepage regression test that builds the Hugo site into a temporary destination and checks the generated homepage for:

- both current appointments and the `Cosmologist` role;
- all four action labels and exact destinations;
- all five preserved PRL, media, and prize URLs;
- `Teaching` and `Visualization` in navigation;
- absence of the `Bio` and `Teach` navigation labels;
- absence of rendered `Interests` and `Education` headings;
- presence of the Interests and Education metadata in the author source file.

Run the existing Python and JavaScript test suites and the Hugo production build. Then inspect desktop and mobile screenshots to confirm that the existing theme and split composition are unchanged, the shorter content is easier to scan, and the action row wraps without overlap or overflow.

## Success Criteria

- A first-time visitor can identify Minh as a cosmologist and understand his research purpose from the opening paragraph.
- Both current appointments are visible with equal prominence.
- Academic credibility is established without presenting a mini-CV.
- Prospective students, postdocs, and collaborators receive an explicit invitation to make contact.
- Research, publications, CV, and contact information are directly accessible from the landing block.
- The homepage retains its current visual identity while removing repeated research descriptions and rendered Interests/Education panels.
