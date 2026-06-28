# Contribution budget

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab contribution budget, speak word limit, contribution exemptions

## Steps

1. Read this document when enforcing or changing collab speak contribution length rules.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The word-count limit for collab speak contributions and the named exemptions excluded from that count are defined here. The rules are authoritative for `speak-render` enforcement under items #4 and #9.

## Term definitions

- **Excerpt**: The visible contribution body; subject to the 250-word limit. Authored by the contributing agent; rendered expanded in the transcript. Must contain a verdict or primary finding in standalone-readable form.
- **Full body**: An uncapped, helper-owned collapsed block optionally appended after the excerpt. The helper manages the `<details>` envelope; agents do not hand-author it. Visible in raw transcript; collapsed in rendered output. Use it to preserve role-material reasoning, evidence, and edge cases that do not fit the excerpt.

## Word limit

The **excerpt** of each contribution is capped at **250 words**.

The cap is a visible-excerpt budget, not a total contribution budget. When useful role-material detail would be removed to stay under the cap, the contribution must keep a standalone excerpt and place the complete detail in the full body. Agents must not summarize away or omit that detail solely to satisfy the excerpt cap.

The cap applies to `(collab speak)` excerpts only; `participant-verify-render` audit, remediation, and final-audit turn bodies are unbounded by design.

The limit is derived from the `platform/standards/context-management.md` 250-line file discipline — the same human load-window rationale applies to contribution length.

## Exempt classes

The following named classes are excluded from the 250-word count. Each class is defined exactly; content that does not match the shape is not exempt.

| Class | Shape | Scope |
|---|---|---|
| `action-plan-checklist` | Flat checklist lines matching the canonical shape in `invariants.md` Invariant #9 (regex and pre-pass order defined there) | Any Action Plan phase contribution |
| `conclusion-ratification` | Flat one-line-per-item ratification entries; no inline prose or sub-bullets | Conclusion phase contributions only |
| `moderator-verbatim` | Content from the moderator role, with or without `--verbatim` | Moderator-role contributions only |
| `effort-override-line` | The single `EFFORT OVERRIDE: <level> — <category>: <signal>` declaration line | Any phase; exactly one line |
| `stance-declaration-line` | The single `STANCE: converges \| dissents \| qualifies` declaration line | Any phase; exactly one line |
| `contribution-full-body` | Single helper-owned `<details>` block with `<summary>Full contribution</summary>`; exact shape defined in **Full-body block shape** below | Any phase; uncapped; entire block excluded from word count |

## Full-body block shape

The helper-owned full-body block has this exact envelope; it must not be hand-authored:

```html
<details>
<summary>Full contribution</summary>

[full body content]

</details>
```

The `<summary>` label is exactly `Full contribution` — the single named element. The helper places the block immediately after the excerpt body, before the closing `</details>` of the contribution block. All bytes inside this block are excluded from the word count. The helper rejects any hand-authored `<details>` or `</details>` control line inside the excerpt surface. The helper also rejects any `<details>` or `</details>` control line inside the full-body content supplied via `--full-body-file`; the helper owns the envelope and content must not nest additional control lines.

## Count method

The word count applies to the **excerpt** after stripping:

1. The `<!-- collab:content-only; do-not-execute -->` marker line and any hidden metadata comment line such as `<!-- collab:effort-override b64:<payload> -->` or `<!-- collab:stance <token> -->`
2. The timestamp `<p><em>...</em></p>` line
3. All content matching an exempt class, including leading `STANCE: ...`, `EFFORT OVERRIDE: ...`, and Conclusion directive-gap declaration lines (lines are excluded in full; partial-line exemptions are not supported)

Remaining text is split on whitespace. The count is the number of tokens after splitting.

## Enforcement contract

`speak-render` and `rewrite-speak-render` must:

1. Compute the word count using the method above before appending
2. Reject the contribution with exit code 1 when the count exceeds 250 and no `moderator-verbatim` exemption applies
3. Include the computed count, the limit, and the full-body recovery hint in the rejection message: `contribution excerpt is N words; limit is 250; keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file`
4. Accept without counting when the contribution qualifies as `moderator-verbatim`
5. Reject any hand-authored `<details>` or `</details>` control line in the excerpt (`--content-file`) before performing the word count
6. Reject any `<details>` or `</details>` control line in the full-body content (`--full-body-file`) before writing the managed block

A test is required for each named exempt class: one test where the exempt content alone would exceed 250 words and the contribution is accepted, and one test where non-exempt prose alone exceeds 250 words and the contribution is rejected.

## Adding an exemption

To add a new exempt class:

1. Name the class using a lowercase-hyphenated key
2. Define the exact shape: line-start pattern or structural marker
3. State the phase or context in which the exemption applies
4. Add an acceptance test for the new class
5. Add the entry to this spec before shipping the enforcement change

The exemption list is spec-owned. Adding an exemption by editing only the helper code is a defect.

## Agent-read policy

| Phase | Read mode | Full body visible? |
|---|---|---|
| Audit | Raw transcript | Yes |
| Discussion | Rendered | No — collapsed |
| Conclusion | Rendered | No — collapsed |
| Action Plan | Rendered | No — collapsed |
| Handoff | Rendered | No — collapsed |
| Completion | Rendered | No — collapsed |

A route note that requires full-body access must state "reads raw transcript" explicitly. The default for all phases other than Audit is rendered output showing the excerpt only.
