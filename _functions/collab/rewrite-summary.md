# /collab rewrite summary

Rewrite the most recent summary in-place within the Completion section of a collaboration record.

## Trigger

**Slash:** `/collab rewrite summary`
**Signature:** `/collab rewrite summary`
**Prose dispatch:** `(collab rewrite summary)` — prose routing hint; not a terminal command.
**Search phrases:** collab rewrite-summary, rewrite collab summary, redo collab summarize

## Steps

**This command rewrites the summary only. Do not make file edits, run shell commands, or modify any codebase artifact outside the user-scope collab state root.**

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Locate the most recent `### Summary — YYYY-MM-DD` subsection under `## Completion`. If no such subsection exists, **ABORT**: nothing yet summarized; run `/collab write summary` first.
4. Draft the replacement reference summary from the full record content, write it to a temporary summary file, then call `tools/collab/registry.py rewrite-summary <target> --summary-file <path>`. The helper replaces the content of the located summary subsection and updates the date in the subsection heading to the current date.
5. Preserve all previous participant contributions, execution history, and any content outside the summary subsection.
6. Stop after rewriting the summary.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `rewrite summary`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Rewrite semantics:** `/collab rewrite summary` rewrites the most recent summary in-place rather than appending a new one. The summary subsection count does not change.
- **Open and closed records:** Re-summarize is allowed on both open and closed records, matching `/collab write summary` behavior.
- **Fact boundary:** Summarize only what the record supports. Do not mark unaccepted proposals as accepted decisions.
