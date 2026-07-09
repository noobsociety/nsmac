# Helper output

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab helper output, advisory line ordering, helper exit codes

## Steps

1. Read this document when auditing or changing collab helper output contracts.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The document defines the collab helper exit-code semantics, the advisory line ordering, and the module-to-subcommand audit map. The definitions are authoritative for platform-engineer role audits under item #5. Exact per-command output and abort message strings are deliberately not mirrored here: the engine source owns them, and the shell suite under `tests/` pins the load-bearing ones. Route docs cite the sections below rather than restating them.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success or eligible; output is valid and the caller may proceed |
| 1 | Blocked, invalid input, or precondition failed; output names the reason |

Any command that exits non-zero must print a human-readable error message. Silent non-zero exits are a defect.

## Advisory line ordering

Advisory lines follow every successful mutating action. Order is fixed; consumers parse by prefix label, not line index.

| Position | Prefix | Required by |
|---|---|---|
| 1 | `NEXT:` | All mutating commands |
| 2 | `EFFORT:` | All mutating commands |
| 3 | `EFFICIENCY:` | Commands that cross a lifecycle boundary |
| 4 | `IDENTITY:` | `join` only |

`EFFICIENCY:` is suppressed when no lifecycle boundary is crossed in the action. `IDENTITY:` records the `agentId` captured at join time.

Advisory lines are suppressed on failed eligibility checks, duplicate contributions, or any gate failure. The output on failure shows only the blocker.

Pre-write advisory lines (`speak-render`'s `BOUNDARY:`, `SUCCINCTLY:`, `RETRACT:`) are owned by the emitting route's doc; they appear before any write and before any post-write advisory line.

## Defect definition

A command has a helper-output defect when any of the following is true:

- A non-zero exit prints no human-readable error message
- Advisory lines appear out of the fixed order
- Exit code does not match the semantic table above
- A pre-write advisory line appears after a post-write advisory line
- A suppressed line appears on a failed-gate output

## Module-to-subcommand map

Maps each helper module family to its implementing subcommand(s) and key function(s). Most functions reside in `registry.py`; rows that resolve to a sibling helper note the containing module in the Key function(s) column. Use this table to locate the code that owns a family's behavior and abort strings when auditing spec-to-code alignment.

| Module | Subcommand(s) | Key function(s) |
|---|---|---|
| `speak-render` / `rewrite-speak-render` | `speak-render`, `rewrite-speak-render` | `render_speak()`, `render_re_speak()` |
| `seal-state` | `seal-state` | `seal_state()` |
| `seal-write` | `seal-write` | `seal_write()` |
| `record-verdict` | `record-verdict` | `record_verdict()` |
| `handoff-shape` | `speak-render`, `rewrite-speak-render` | `parse_handoff_content()`, `validate_handoff_write_scope()`, `validate_handoff_validation_commands()`, `validate_handoff_state()` |
| `participant-verify-state` | `participant-verify-state` | `participant_verify_state()` |
| `participant-verify-render` | `participant-verify-render` | `participant_verify_render()` |
| `reopen` | `reopen` | `reopen_collab()` |
| `show-verdict` | `show-verdict` | `show_verdict()` |
| `init` | `init` | `init_collab()`, `parse_init_tokens()` |
| `contribution-budget` | `speak-render`, `rewrite-speak-render` | `enforce_contribution_budget()`, `read_budget_spec()` |
| `command-default` | all commands | `load_registry()`, `resolve_config_root()` |
| `participant-role-files` | all registry-loading commands | `registry_validation.validate_registry()`, `validate_participant_role_files()` |

**How to diff:** For each module row, open the named key function(s) in `registry.py` or the named helper module; the `die()` / `sys.exit(1)` call strings in those functions are the authoritative abort messages, and the shell tests under `tests/commands/collab/` pin the load-bearing ones. Any doc or spec that quotes a message diverging from the code is the drift candidate — the code is correct.
