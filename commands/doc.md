# /doc

Route documentation workflows through one singular namespace so the command palette stays compact.

## Trigger

**Slash:** `/doc`
**Signature:** `/doc <assess | compact | compare | write changelog | write manual | write readme>`
**Prose dispatch:** `(doc <assess | compact | compare | write changelog | write manual | write readme>)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** docs workflow, documentation command, markdown workflow

## Steps

1. Resolve `<route>` from the first token after `/doc`; `write` consumes the next token as its target. If missing or invalid, **ABORT** naming the token received and emit the allowed route set in **Route**.
2. Load the mapped file under `../_functions/doc/` from the Cursor config root.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `assess` -> [_functions/doc/assess](../_functions/doc/assess.md); `compact` -> [_functions/doc/compact](../_functions/doc/compact.md); `compare` -> [_functions/doc/compare](../_functions/doc/compare.md); `write changelog` -> [_functions/doc/write-changelog](../_functions/doc/write-changelog.md); `write manual` -> [_functions/doc/write-manual](../_functions/doc/write-manual.md); `write readme` -> [_functions/doc/write-readme](../_functions/doc/write-readme.md).
- **Parameters:** route selector from the signature above.
- **Bare namespace help:** A bare `/doc` invocation aborts and emits the route roster in **Route**.
- **Examples:** `/doc write readme`, `/doc write manual`, `/doc write changelog atomic`, `/doc assess README.md`, `/doc compare old.md new.md`, `/doc compact README.md`.
