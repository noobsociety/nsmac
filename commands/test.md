# /test

Route repository QA harnesses through one namespace so validation commands stay grouped.

## Trigger

**Slash:** `/test`
**Signature:** `/test <commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>`
**Prose dispatch:** `(test <commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** run tests, cursor qa run, harness run, test target

## Steps

1. Resolve `<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>` from the first token after `/test`. If missing or invalid, **ABORT** naming the token received and emit the allowed target set: `commands`, `rules`, `_functions`, `_mdc`, `_core`, `_roles`, `_settings`, `repo`, `all`.
2. Load [_functions/test](../_functions/test/run.md) from the Cursor config root.
3. Execute the harness route with the resolved target.

## Notes

- **Route:** all targets execute through [_functions/test](../_functions/test/run.md).
- **Parameters:** `<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>` — required QA target selector.
- **Bare namespace help:** A bare `/test` invocation aborts and emits the allowed target set; it must not default to `all` or any other target.
- **Examples:** `/test _core`, `/test commands`, `/test all`.
