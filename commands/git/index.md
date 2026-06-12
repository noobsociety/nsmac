# (git)

Route Git and issue workflows through one namespace so source-control commands stay grouped.

## Trigger

**Dispatch:** `(git <commit | issue>)` — routing-only command form; not a shell command.
**Search phrases:** git workflow, issue workflow, source control workflow

## Steps

1. Resolve `<route>` from the first token after `(git)`. If missing or invalid, **ABORT** naming the token received and emit the allowed route set: `commit`, `issue`.
2. Load the mapped route file under this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `commit` -> [commit](commit/index.md); `issue` -> [issue](issue/index.md).
- **Parameters:** `<commit | issue>` — required Git route.
- **Bare namespace help:** A bare `(git)` invocation aborts and emits `commit | issue`; it must not dispatch to a mutating route.
- **Examples:** `(git commit atomic)`, `(git commit squash)`, `(git commit squash <from> <to>)`, `(git issue create <goal>)`, `(git issue implement <goal>)`.
