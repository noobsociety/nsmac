# Helper subcommand classification

Classification of `commands/collab/engine/registry.py` subcommands by operational role. Operators troubleshooting a failed seal or reopen can use this table to identify which subcommands are safe to invoke directly.

## Classes

| Class | Definition |
|---|---|
| `route-backend` | Invoked by a named route step; produces structured output consumed by the calling route |
| `recovery` | Used to inspect, repair, or validate state outside normal route flow |
| `utility` | Stateless helpers that generate values or render fragments; no registry mutation |

## Subcommand table

| Subcommand | Class | Invoked by |
|---|---|---|
| `activate` | `route-backend` | `/collab activate` |
| `advance` | `route-backend` | `/collab advance` (phase transition side-effect) |
| `archive` | `route-backend` | `/collab archive` |
| `audit-closed` | `recovery` | diagnostic / CI |
| `audit-effort-matrix` | `recovery` | diagnostic / CI |
| `banner-timestamp` | `utility` | header render |
| `close` | `route-backend` | `/collab run plan` auto-close |
| `delete` | `route-backend` | `/collab delete` |
| `effort-state` | `route-backend` | effort enforcement in `speak-render` |
| `execute-spawn` | `route-backend` | `/collab run plan` step 11 |
| `execution` | `route-backend` | `/collab run plan` step 15 |
| `flag-inventory` | `route-backend` | `/collab show flags` |
| `handoff-state` | `route-backend` | `/collab run plan` step 11; `/collab participant verify` |
| `init` | `route-backend` | `/collab init` |
| `join-participants` | `route-backend` | `/collab join` |
| `list` | `route-backend` | `/collab list` |
| `out-of-scope-patch` | `recovery` | manual state repair |
| `participant-verify-render` | `route-backend` | `/collab participant verify` step 14 |
| `participant-verify-state` | `route-backend` | `/collab participant verify` step 5; `/collab run plan` step 16 |
| `registry-path` | `utility` | registry path resolution |
| `render-participants` | `recovery` | transcript repair / re-render |
| `render-status` | `recovery` | transcript repair / re-render |
| `reopen` | `route-backend` | `/collab reopen` |
| `retract-speak` | `route-backend` | `/collab retract speak` |
| `reviewer-state` | `route-backend` | reviewer gate checks |
| `rewrite-speak-render` | `route-backend` | `/collab rewrite speak` |
| `rewrite-summary` | `route-backend` | `/collab rewrite summary` |
| `role-row` | `utility` | participant table render |
| `roles` | `utility` | role list |
| `seal-render` | `route-backend` | `/collab seal verification` |
| `seal-state` | `route-backend` | `/collab seal verification`; stale-seal checks |
| `set` | `route-backend` | `/collab set` |
| `show-verdict` | `route-backend` | `/collab show verdict` |
| `speak-lifecycle` | `route-backend` | lifecycle computation (consumed by `speak-lifecycle-live`) |
| `speak-lifecycle-live` | `route-backend` | `/collab speak` step 13 |
| `speak-render` | `route-backend` | `/collab speak` step 11 |
| `speak-state` | `route-backend` | `/collab speak` step 8; `--resume` signal after context-changing events |
| `summary-role` | `utility` | role summary fragment |
| `timestamp` | `utility` | RFC-format timestamp generation |
| `transcript-repair` | `recovery` | manual transcript state repair |
| `transcript-view` | `recovery` | raw transcript inspection |
| `unset` | `route-backend` | `/collab unset` |
| `validate` | `recovery` | registry consistency check; CI |
| `write-guard` | `route-backend` | write-scope enforcement in all mutating routes |
