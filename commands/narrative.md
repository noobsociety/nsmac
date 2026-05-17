# /narrative

Route narrative rewrite workflows through one public slash so staged text-content work stays grouped.

## Trigger

**Slash:** `/narrative`
**Signature:** `/narrative <rewrite content>`
**Prose dispatch:** `(narrative <rewrite content>)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** narrative rewrite workflow, staged narrative rewrite, narrative content rewrite

## Steps

1. Resolve `<rewrite content>` from the first token after `/narrative`. If missing or invalid, **ABORT** naming the token received and emit the allowed route set: `rewrite content`.
2. Load `../_functions/narrative/rewrite-content.md` from the Cursor config root.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `rewrite content` -> [_functions/narrative/rewrite-content](../_functions/narrative/rewrite-content.md).
- **Parameters:** `<rewrite content>` — required route selector.
- **Bare namespace help:** A bare `/narrative` invocation aborts and emits `rewrite content`.
- **Examples:** `/narrative rewrite content audit --role pa`, `/narrative rewrite content align --role tw`, `/narrative rewrite content gate --role pe`.
