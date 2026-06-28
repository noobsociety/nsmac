# (collab list)

List the registry-backed collabs so the moderator can inspect status and active selection without navigating the filesystem.

## Trigger

**Dispatch:** `(collab list [--status <open|closed|archived>])` — routing-only command form; not a shell command.
**Search phrases:** collab list, list collaborations, list collab records

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4).
2. Call `commands/collab/engine/registry.py list [--status <open|closed|archived>]`.
3. Display the helper output exactly. Stop without mutating the registry or any transcript.

## Notes

- **Parameters:** `--status <open|closed|archived>` — optional filter; when absent, all collabs are listed.
- **Output shape:** If project metadata is available, the first line is `Project: <label> · <projectId>`; the label is display-only and never a resolver key. Each entry spans two lines. Line 1: `[*]` (active) or `[ ]` (inactive), then `#N` (stable 1-based registry position), `-`, slug, title truncated to 20 characters followed by `…` if longer. Line 2: indented status, active phase (`—` when no phase applies), participant count, and `YYYY-MM-DD` init date. Example:

```
Project: dotcursor · a13dba4ca8714205b217dca31da96eee

[*] #3 - payment-refactor    Refactor payment pipeli…
         open · Discussion · 3 participants · 2025-04-28

[ ] #1 - onboarding-flow     User onboarding flow r…
         closed · — · 4 participants · 2025-03-10
```

- **Numeric selector stability:** The `#N` position is the collab's 1-based insertion index in the registry `collabs` array and never changes after `archive`, `delete`, or reordering. Pass `#N` or the bare number to any collab management command as a shorthand for the slug (e.g., `(collab activate 3)`).
- **Sort order:** Active collab always first. Among the rest: highest `#N` first (newest to oldest), then slug alphabetically as a tiebreaker when `#N` values are equal (not normally possible but stated for completeness).
- **Registry boundary:** `(collab list)` is read-only. `(collab list)` never creates, edits, archives, or selects a collab.

```route-arg
dispatch: (collab list [--status <open|closed|archived>])
param: name=--status; required=optional; placeholder=<open|closed|archived>; class=literal; values=open | closed | archived; default=literal:all
```
