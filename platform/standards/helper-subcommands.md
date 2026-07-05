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
| `activate` | `route-backend` | `(collab activate)` |
| `advance` | `route-backend` | `(collab advance)` (phase transition side-effect) |
| `archive` | `route-backend` | `(collab archive)` |
| `audit-closed` | `recovery` | diagnostic / CI |
| `audit-effort-matrix` | `recovery` | diagnostic / CI |
| `banner-timestamp` | `utility` | header render |
| `close` | `route-backend` | `(collab run plan)` auto-close |
| `delete` | `route-backend` | `(collab delete)` |
| `diff` | `route-backend` | `(collab diff)` |
| `effort-state` | `route-backend` | effort enforcement in `speak-render` |
| `execute-spawn` | `route-backend` | `(collab run plan)` step 11 |
| `execution` | `route-backend` | `(collab run plan)` step 15 |
| `flag-inventory` | `route-backend` | `(collab show flags)` |
| `handoff-state` | `route-backend` | `(collab run plan)` step 11; `(collab participant verify)` |
| `help` | `utility` | route playbook lookup |
| `init` | `route-backend` | `(collab init)` |
| `join-participants` | `route-backend` | `(collab join)` |
| `list` | `route-backend` | `(collab list)` |
| `log` | `route-backend` | `(collab log)` |
| `open` | `route-backend` | `(collab open)` |
| `out-of-scope-patch` | `recovery` | manual state repair |
| `participant-verify-render` | `route-backend` | `(collab participant verify)` step 14 |
| `participant-verify-state` | `route-backend` | `(collab participant verify)` step 5; `(collab run plan)` step 16 |
| `registry-path` | `utility` | registry path resolution |
| `registry-cli-doc` | `utility` | generated registry CLI documentation |
| `render-participants` | `recovery` | transcript repair / re-render |
| `render-status` | `route-backend` | transcript status mirroring after metadata writes |
| `remove-participant` | `route-backend` | `(collab remove participant)` |
| `repair-execution-provenance` | `recovery` | manual execution provenance repair |
| `reopen` | `route-backend` | `(collab reopen)` |
| `restore` | `route-backend` | `(collab restore --to <eventIndex>)` |
| `retract-speak` | `route-backend` | `(collab retract speak)` |
| `reviewer-state` | `route-backend` | reviewer gate checks |
| `rewrite-speak-render` | `route-backend` | `(collab rewrite speak)` |
| `restart-verification` | `recovery` | manual verification restart |
| `role-row` | `utility` | participant table render |
| `roles` | `utility` | role list |
| `record-verdict` | `route-backend` | `(collab seal verification)` |
| `seal-state` | `route-backend` | `(collab seal verification)`; stale-seal checks |
| `seal-write` | `route-backend` | `(collab seal verification)` |
| `set` | `route-backend` | `(collab set)` |
| `show-verdict` | `route-backend` | `(collab show verdict)` |
| `speak-lifecycle` | `route-backend` | lifecycle computation (consumed by `speak-lifecycle-live`) |
| `speak-lifecycle-live` | `route-backend` | `(collab speak)` step 13 |
| `speak-render` | `route-backend` | `(collab speak)` step 11 |
| `speak-state` | `route-backend` | `(collab speak)` step 8; `--resume` signal after context-changing events |
| `status-view` | `route-backend` | `(collab status)` |
| `summary-role` | `utility` | role summary fragment |
| `summarize` | `route-backend` | `(collab summarize)` |
| `tag` | `route-backend` | `(collab tag)` |
| `timestamp` | `utility` | RFC-format timestamp generation |
| `transcript-repair` | `recovery` | manual transcript state repair |
| `transcript-view` | `recovery` | raw transcript inspection |
| `unset` | `route-backend` | `(collab unset)` |
| `validate` | `recovery` | registry consistency check; CI |
| `write-guard` | `route-backend` | write-scope enforcement in all mutating routes |
