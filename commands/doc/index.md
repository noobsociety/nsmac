# (doc)

Route documentation workflows through one namespace so the command palette stays compact.

## Trigger

**Dispatch:** `(doc <write changelog | write manual | write readme>)` — routing-only command form; not a shell command.
**Search phrases:** docs workflow, documentation command, markdown workflow

## Steps

1. Resolve `<route>` from the first token after `(doc)`; `write` consumes the next token as its target. If missing or invalid, **ABORT** naming the token received and emit the allowed route set in **Route**.
2. Load the mapped route file under this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `write changelog` -> [write-changelog](write-changelog/index.md); `write manual` -> [write-manual](write-manual/index.md); `write readme` -> [write-readme](write-readme/index.md).
- **Parameters:** route selector from the Dispatch line above.
- **Bare namespace help:** A bare `(doc)` invocation aborts and emits the route roster in **Route**.
- **Examples:** `(doc write readme)`, `(doc write manual)`, `(doc write changelog atomic)`.
