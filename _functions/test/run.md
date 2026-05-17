# /test

Run QA harnesses by target so maintainers can execute canonical test checklists without prompt copy-paste.

## Trigger

**Slash:** `/test`
**Signature:** `/test <commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>`
**Prose dispatch:** `(test <commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** `run tests`, `cursor qa run`, `harness run`, `test target`

## Steps

1. Resolve `<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>` from the first argument. If missing or invalid, **ABORT** naming the token received and emit the allowed target set: `commands`, `rules`, `_functions`, `_mdc`, `_core`, `_roles`, `_settings`, `repo`, `all`.
2. Route by target:
   - `commands` → load and execute `~/.cursor/_tests/commands.md` full procedure and invariants.
   - `rules` → load and execute `~/.cursor/_tests/rules.md` full procedure and invariants.
   - `_functions` → load and execute `~/.cursor/_tests/_functions.md` full procedure and invariants.
   - `_mdc` → load and execute `~/.cursor/_tests/_mdc.md` full procedure and invariants.
   - `_core` → load and execute `~/.cursor/_tests/_core.md` full procedure and invariants.
   - `_roles` → load and execute `~/.cursor/_tests/_roles.md` full procedure and invariants.
   - `_settings` → load and execute `~/.cursor/_tests/_settings.md` full procedure and invariants.
   - `repo` → load `REPOSITORY.md` at repository root. If missing, **ABORT** naming the expected path.
   - `all` → run `commands`, then `rules`, then `_functions`, then `_mdc`, then `_core`, then `_roles`, then `_settings`, then `repo` in that order.
3. If any target fails, patch the governed files and rerun that target’s full harness procedure until pass or documented blockers.
4. For target `repo` or `all`, run `./tools/cursor/audit.sh` and `./tests/run.sh`.
5. Return harness-required output blocks per executed targets plus a concise consolidated status.

## Notes

- **Route:** `commands` | `rules` | `_functions` | `_mdc` | `_core` | `_roles` | `_settings` | `repo` | `all`.
- **Parameters:** `<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>` — required QA target selector.
- **Missing target help:** A bare `/test` invocation aborts before any harness command and emits the allowed target set.
- **Required authorities:** `~/.cursor/_tests/commands.md`, `~/.cursor/_tests/rules.md`, `~/.cursor/_tests/_functions.md`, `~/.cursor/_tests/_mdc.md`, `~/.cursor/_tests/_core.md`, `~/.cursor/_tests/_roles.md`, `~/.cursor/_tests/_settings.md`, and `REPOSITORY.md` at repo root.
- **Dependencies:** If any required harness context is unreadable, **ABORT** per **`auto-context-gate.mdc`**.

```cursor-arg
dispatch: (test <commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>)
param: name=<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>; required=required; placeholder=<commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all>; class=literal; values=commands | rules | _functions | _mdc | _core | _roles | _settings | repo | all
```
