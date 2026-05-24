# /quality

Route specialist quality workflows through one namespace so review commands stay grouped.

## Trigger

**Slash:** `/quality`
**Signature:** `/quality <assess interface | assess web | assess game | assess operations | tune | show notes>`
**Prose dispatch:** `(quality <assess interface | assess web | assess game | assess operations | tune | show notes>)` — prose routing hint; not a terminal command.
**Search phrases:** evaluation workflow, principal review, rubric review

## Steps

1. Resolve `<route>` from the first token after `/quality`; `assess` and `show` consume the next token as their target. If missing or invalid, **ABORT** naming the token received and emit the allowed route set in **Route**.
2. Load the mapped route file under this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `assess interface` -> [assess-interface](assess-interface/index.md); `assess web` -> [assess-web](assess-web/index.md); `assess game` -> [assess-game](assess-game/index.md); `assess operations` -> [assess-operations](assess-operations/index.md); `tune` -> [tune](tune/index.md); `show notes` -> [show-notes](show-notes/index.md).
- **Parameters:** route selector from the signature above.
- **Bare namespace help:** A bare `/quality` invocation aborts and emits the route roster in **Route**.
- **Examples:** `/quality assess interface screenshot.png /path/to/project`, `/quality assess web /path/to/project`, `/quality tune web /path/to/project`.
