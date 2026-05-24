# /doc

Route documentation workflows through one singular namespace so the command palette stays compact.

## Trigger

**Slash:** `/doc`
**Signature:** `/doc <assess | compact | compare | write changelog | write manual | write readme>`
**Prose dispatch:** `(doc <assess | compact | compare | write changelog | write manual | write readme>)` — prose routing hint; not a terminal command.
**Search phrases:** docs workflow, documentation command, markdown workflow

## Steps

1. Resolve `<route>` from the first token after `/doc`; `write` consumes the next token as its target. If missing or invalid, **ABORT** naming the token received and emit the allowed route set in **Route**.
2. Load the mapped route file under this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `assess` -> [assess](assess/index.md); `compact` -> [compact](compact/index.md); `compare` -> [compare](compare/index.md); `write changelog` -> [write-changelog](write-changelog/index.md); `write manual` -> [write-manual](write-manual/index.md); `write readme` -> [write-readme](write-readme/index.md).
- **Parameters:** route selector from the signature above.
- **Bare namespace help:** A bare `/doc` invocation aborts and emits the route roster in **Route**.
- **Examples:** `/doc write readme`, `/doc write manual`, `/doc write changelog atomic`, `/doc assess README.md`, `/doc compare old.md new.md`, `/doc compact README.md`.
