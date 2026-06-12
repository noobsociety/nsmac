# (collab write summary)

Write a human-readable reference summary from an existing collaboration record.

## Trigger

**Dispatch:** `(collab write summary)` — routing-only command form; not a shell command.
**Search phrases:** collab summarize, summarize collaboration, collaboration wrap up

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the full resolved transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Draft a concise reference summary from the record's existing content.
4. Write the summary under `## Completion`. If `## Completion` already has content, append a new `### Summary — YYYY-MM-DD` subsection.
5. Preserve all previous participant contributions.
6. Stop after writing the summary.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `write summary`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Closed records:** Summaries are allowed on closed records.
- **Fact boundary:** Summarize only what the record supports. Do not mark unaccepted proposals as accepted decisions.
