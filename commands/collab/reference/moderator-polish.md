# Moderator polish

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** moderator polish, collab moderator formatting, moderator typo dictionary

## Steps

1. Read this document when applying or changing moderator-role readability formatting.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The allowed transformations the helper may apply to moderator-role contribution text, and the bounded typo dictionary, are defined here. The rules are authoritative for helper implementation under items #13 and #14.

## Opt-out

When `--verbatim` is passed to `speak-render` or `rewrite-speak-render`, all polish transforms are bypassed entirely. The contribution is written exactly as supplied. No transform — including whitespace normalization — is applied.

## Allowed transformations

The helper may apply only transformations from this list. Any change not in this list is prohibited.

### Whitespace normalization

- Collapse two or more consecutive blank lines to one blank line
- Strip trailing whitespace from each line
- Ensure the file ends with exactly one newline

### List glyph cleanup

- Normalize unordered list markers to `-` (dash-space)
- Accepted input glyphs: `*`, `+`, `-`
- Do not change ordered list markers

### Sentence-start capitalization

- Capitalize the first letter of the first word in a sentence
- A sentence starts after `.`, `?`, or `!` followed by a space or line break
- Do not alter mid-sentence capitalization or ALL-CAPS sequences

### Terminal punctuation

- Add a period to the end of a line that ends a sentence but has no terminal punctuation (`.`, `?`, `!`)
- Apply only to prose lines; do not add punctuation to headings, list item markers, or code blocks

## Typo dictionary

Entries are matched case-insensitively unless noted. The fix preserves the case pattern of the match (lower → lower; title → title; ALL → ALL).

| Observed typo | Correction |
|---|---|
| `collab record` | `collab record` (no change; canonical form) |
| `speek` | `speak` |
| `Compeletion` | `Completion` |
| `Concusion` | `Conclusion` |
| `Acton Plan` | `Action Plan` |
| `Hanoff` | `Handoff` |
| `moderetor` | `moderator` |
| `participent` | `participant` |
| `registery` | `registry` |
| `contribuiton` | `contribution` |

## Adding an entry

To add a typo entry:

1. Confirm the typo appears in at least one observed collab record
2. Add the row to the table above with the observed form and the correction
3. Add a fixture test: input containing the typo, expected output containing the correction, assertion that substance is unchanged
4. Ship the spec change before or alongside the helper change

Dictionary entries are spec-owned. Adding a correction by editing only the helper code is a defect.

## Substance-preservation requirement

No transform, including typo correction, may change the semantic content of the contribution. Tests must assert that the post-transform text has the same meaning as the pre-transform text by diffing the non-typo, non-whitespace, non-glyph content.

A fixture test must cover each allowed transform class with a case that confirms substance is unchanged after the transform.
