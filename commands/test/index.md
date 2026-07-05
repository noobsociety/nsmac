# (test)

Run QA harnesses by target so maintainers can execute canonical test checklists without prompt copy-paste.

## Trigger

**Dispatch:** `(test <commands | core | roles | settings | repo | all>)` — routing-only command form; not a shell command.
**Search phrases:** `run tests`, `qa run`, `harness run`, `test target`

## Steps

1. Resolve `<commands | core | roles | settings | repo | all>` from the first argument. If missing or invalid, **ABORT** naming the token received and emit the allowed target set: `commands`, `core`, `roles`, `settings`, `repo`, `all`.
2. Route by target:
   - `commands` → load and execute `~/nsmac/tests/specs/commands.md` full procedure and invariants.
   - `core` → load and execute `~/nsmac/tests/specs/core.md` full procedure and invariants.
   - `roles` → load and execute `~/nsmac/tests/specs/roles.md` full procedure and invariants.
   - `settings` → load and execute `~/nsmac/tests/specs/settings.md` full procedure and invariants.
   - `repo` → load `REPOSITORY.md` at repository root. If missing, **ABORT** naming the expected path.
   - `all` → run `commands`, then `core`, then `roles`, then `settings`, then `repo` in that order.
3. If any target fails, patch the governed files and rerun that target’s full harness procedure until pass or documented blockers.
4. For target `repo` or `all`, run `./platform/tooling/audit.sh` and `./tests/run.sh`.
5. Return harness-required output blocks per executed targets plus a concise consolidated status.

## Notes

- **Route:** `commands` | `core` | `roles` | `settings` | `repo` | `all`.
- **Parameters:** `<commands | core | roles | settings | repo | all>` — required QA target selector.
- **Missing target help:** A bare `(test)` invocation aborts before any harness command and emits the allowed target set.
- **Required authorities:** `~/nsmac/tests/specs/commands.md`, `~/nsmac/tests/specs/core.md`, `~/nsmac/tests/specs/roles.md`, `~/nsmac/tests/specs/settings.md`, and `REPOSITORY.md` at repo root.
- **Dependencies:** If any required harness context is unreadable, **ABORT** per **`context-gate.md`**.
- **Internal harness specs:** `tests/specs/generated.md`, `tests/specs/templates.md`, and `tests/specs/tests.md` are intentionally not exposed as `(test) <target>` routing targets; they are harness-internal specifications swept by the full suite.

```route-arg
dispatch: (test <commands | core | roles | settings | repo | all>)
param: name=<commands | core | roles | settings | repo | all>; required=required; placeholder=<commands | core | roles | settings | repo | all>; class=literal; values=commands | core | roles | settings | repo | all
```
