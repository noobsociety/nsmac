# Contribution budget

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab contribution budget, speak word limit, contribution exemptions

## Steps

1. Read this document when enforcing or changing collab speak contribution length rules.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Defines the word-count limit for collab speak contributions and the named exemptions that are excluded from that count. Authoritative for `speak-render` enforcement under items #4 and #9.

## Word limit

Normal contribution bodies are capped at **250 words**.

The limit is derived from the `cursor/_core/context-management.md` 250-line file discipline — the same human load-window rationale applies to contribution length.

## Exempt classes

The following named classes are excluded from the 250-word count. Each class is defined exactly; content that does not match the shape is not exempt.

| Class | Shape | Scope |
|---|---|---|
| `action-plan-checklist` | Flat checklist lines matching the canonical shape in `_invariants.md` Invariant #9 (regex and pre-pass order defined there) | Any Action Plan phase contribution |
| `conclusion-ratification` | Flat one-line-per-item ratification entries; no inline prose or sub-bullets | Conclusion phase contributions only |
| `moderator-verbatim` | Content passed via `--verbatim` or the moderator role with a `<message>` argument | Moderator-role contributions only |
| `effort-override-line` | The single `EFFORT OVERRIDE: <level> — <category>: <signal>` declaration line | Any phase; exactly one line |

## Count method

The word count applies to the contribution body after stripping:

1. The `<!-- collab:content-only; do-not-execute -->` marker line
2. The timestamp `<p><em>...</em></p>` line
3. All content matching an exempt class (lines are excluded in full; partial-line exemptions are not supported)

Remaining text is split on whitespace. The count is the number of tokens after splitting.

## Enforcement contract

`speak-render` must:

1. Compute the word count using the method above before appending
2. Reject the contribution with exit code 1 when the count exceeds 250 and no `moderator-verbatim` exemption applies
3. Include the computed count and the limit in the rejection message: `contribution body is N words; limit is 250`
4. Accept without counting when the contribution qualifies as `moderator-verbatim`

A test is required for each named exempt class: one test where the exempt content alone would exceed 250 words and the contribution is accepted, and one test where non-exempt prose alone exceeds 250 words and the contribution is rejected.

## Adding an exemption

To add a new exempt class:

1. Name the class using a lowercase-hyphenated key
2. Define the exact shape: line-start pattern or structural marker
3. State the phase or context in which the exemption applies
4. Add an acceptance test for the new class
5. Add the entry to this spec before shipping the enforcement change

The exemption list is spec-owned. Adding an exemption by editing only the helper code is a defect.
