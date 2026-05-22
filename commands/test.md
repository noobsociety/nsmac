# /test

Route repository QA harnesses through one namespace so validation commands stay grouped.

## Trigger

**Slash:** `/test`
**Signature:** `/test <commands | _functions | _core | _roles | _settings | repo | all>`
**Prose dispatch:** `(test <commands | _functions | _core | _roles | _settings | repo | all>)` — prose routing hint; not a terminal command.
**Search phrases:** run tests, qa run, harness run, test target

## Steps

1. Resolve `<commands | _functions | _core | _roles | _settings | repo | all>` from the first token after `/test`. If missing or invalid, **ABORT** naming the token received and emit the allowed target set: `commands`_functions`, `_core`, `_roles`, `_settings`, `repo`, `all`.
2. Load [_functions/test](../_functions/test/run.md) from the command config root.
3. Execute the harness route with the resolved target.

## Notes

- **Route:** all targets execute through [_functions/test](../_functions/test/run.md).
- **Parameters:** `<commands | _functions | _core | _roles | _settings | repo | all>` — required QA target selector.
- **Bare namespace help:** A bare `/test` invocation aborts and emits the allowed target set; it must not default to `all` or any other target.
- **Examples:** `/test _core`, `/test commands`, `/test all`.
