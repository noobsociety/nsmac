# /git

Route Git and issue workflows through one namespace so source-control commands stay grouped.

## Trigger

**Slash:** `/git`
**Signature:** `/git <commit | issue>`
**Prose dispatch:** `(git <commit | issue>)` — prose routing hint; not a terminal command.
**Search phrases:** git workflow, issue workflow, source control workflow

## Steps

1. Resolve `<route>` from the first token after `/git`. If missing or invalid, **ABORT** naming the token received and emit the allowed route set: `commit`, `issue`.
2. Load `../_functions/git/<route>.md` from the command config root.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `commit` -> [_functions/git/commit](../_functions/git/commit.md); `issue` -> [_functions/git/issue](../_functions/git/issue.md).
- **Parameters:** `<commit | issue>` — required Git route.
- **Bare namespace help:** A bare `/git` invocation aborts and emits `commit | issue`; it must not dispatch to a mutating route.
- **Examples:** `/git commit atomic`, `/git commit squash`, `/git commit squash <from> <to>`, `/git issue create <goal>`, `/git issue implement <goal>`.
