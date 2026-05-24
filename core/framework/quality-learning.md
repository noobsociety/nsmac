# Quality learning

Quality learning governs rubric adaptation for review and assessment routes.

## When the policy applies

Apply this policy only when a rubric-based quality or documentation assessment
route has finished its primary review.

Current rubric routes are `/quality tune`, `/quality assess interface`,
`/quality assess web`, `/quality assess game`, `/quality assess operations`, and
`/doc assess`.

## Behavior

Run the workflow's normal rubric first.
Then extract up to three missing-check candidates from the reviewed project.
Classify each candidate as `command-local` or `cross-command`.
Keep candidates in the session until the user confirms a change.
Ask for explicit confirmation before changing any rubric or playbook file.
On confirmation, update only the target workflow rubrics.

Skip learning when the prompt includes `no-learn`, `static`, `one-off`, or
`do not adapt`.
In no-learn mode, do not append to `commands/quality/show-notes/index.md`.
In no-learn mode, do not edit target rubric definitions.

## Review workflow

Show this block before editing any target rubric:

```text
Learning candidates
- `id`: short candidate text
- Why it was missing
- Suggested targets
- Confidence
- Suggested default: accept/reject/defer
- notes: <concrete path or symbol from the reviewed project>
```

Ask whether the user agrees with adapting any candidates.
If the user agrees, ask for per-id choices: `accept`, `reject`, or `defer`.
Show a patch preview of exact edits before applying confirmed changes.
Discard candidates when the user gives no decision or cancels the preview.

## Governance

Use `commands/quality/show-notes/index.md` as the durable append-only log for
user-approved quality learning notes.
Never write quality learning notes to any other path.
Require at least one concrete path or symbol from the reviewed project in each
candidate's notes.
Accept `cross-command` candidates only after evidence from at least two
different projects unless the user overrides the threshold.
Keep `/doc assess` candidates documentation-focused.
Apply at most two accepted candidate IDs per run.
Defer remaining accepted IDs to the next run.

## Routing

Route role-specific checks to the matching workflow rubric.
Route generic quality checks to `quality`.
Do not copy checks across every command automatically.

## References

- [style-guide](style-guide.md)
- [document-standard](document-standard.md)
- [command-standard](command-standard.md)
- [context-management](context-management.md)
- [author-voice](author-voice.md)
