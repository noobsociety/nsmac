# Devblog discipline

Generic rules for devblog entry structure, ordering, and foreword form. Project-specific
values — canvas constraints, naming conventions, milestone links, chronology windows —
belong in the project devblog contract. Generic prose mechanics (em-dash discipline,
link-then-italic first mention, bold-colon run-in labels, parenthetical form, backtick
usage, heading-length caps, no-H4, TOC slug and anchor rules) are governed by the system
framework canon: `author-voice.md` (voice and typography) and `markdown-workflow.md`
(formatting and heading rules). Cite those files by name and role — do not restate them
here.

## Weekly entry structure

- **BLUF:** `## Summary` opens with what the reader gets and why it matters. Place it
  immediately after H1. Each prose paragraph in `## Summary` is at most five sentences.
- **TOC:** weekly entries only; placed inside `## Summary` — prose, `---`,
  `**Table of contents:**`, anchor list, `---`. TOC outside this structure is a hard fail.
- **`## Next up`:** one or two short paragraphs in flowing prose, no flat bullet
  backlogs. When the next entry exists, close with:
  `What shipped in the following week is documented in **Week N+1: Title**.`
- **Optional body sections** (appear only when warranted, between the last content `##`
  and `## Next up`): `## Surprises`, `## Lessons`, `## Deferred`, `## Self-assessment`.

## Chronology and artifact ordering

- Chronology claims belong in the first week they are true. A repo-backed artifact
  belongs to the week where the repo (or a related repo) first shows evidence.
- Notes-to-artifact migrations require explicit timing. Name a checking tool, command, or
  playbook only in the week where the checked-in artifact first exists.
- Artifact-only `## Shipped` `###` subsections and their TOC child entries are ordered
  oldest to newest by first supporting commit in the audited weekly window.
- Never use implicit back-references (`named there`, `as above`, `from the previous
  milestone`, `the spread from X`) — cite the durable source directly.
- `N-week.md` must never link to `M-week.md` with M < N.

## Foreword criteria

Foreword entries satisfy all bullets below in addition to frontmatter and voice rules:

- States what the blog covers and what it will not cover.
- Author background present without over-qualifying; no apologies for posting frequency
  or polish.
- A general reader orients within two paragraphs.
- Constraints section reads as personal, not as project policy.
- Two to four paragraphs minimum; no entry in the series is shorter than the foreword.
- Revisions are limited to the foreword's own content — never retroactive edits.
- No `## Summary` section; omit `**Table of contents:**` entirely.

## Hard fails

- TOC appears outside `## Summary`, or `**Table of contents:**` is absent from a weekly
  entry.
- Artifact-only `## Shipped` `###` subsections are not ordered oldest to newest by first
  supporting commit in the audited weekly window.
- `N-week.md` links to `M-week.md` with M < N.
- Implicit back-reference appears in any entry.
- Any list item has a nested sub-bullet.
