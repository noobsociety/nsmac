# /collab

Route moderated collaboration-record workflows through one public slash command.

## Trigger

**Slash:** `/collab`
**Signature:** `/collab <init | join | speak | retract speak | rewrite speak | advance | restore | set | unset | list | activate | open | reopen | close | remove participant | archive | delete | write summary | rewrite summary | run plan | aggregate | export-issues | rewrite execution | participant verify | show policy | show flags | show verdict | seal verification>`
**Prose dispatch:** `(collab <init | join | speak | retract speak | rewrite speak | advance | restore | set | unset | list | activate | open | reopen | close | remove participant | archive | delete | write summary | rewrite summary | run plan | aggregate | export-issues | rewrite execution | participant verify | show policy | show flags | show verdict | seal verification>)` — prose routing hint; not a terminal command.
**Search phrases:** collab workflow, collaboration record, moderated agent discussion

## Steps

<!-- abort: collab-invalid-route -->
1. Resolve a route from the first token after `/collab`; routes with a target token (`retract speak`, `rewrite speak`, `remove participant`, `write summary`, `run plan`, `rewrite execution`, `participant verify`, `show policy`, `show flags`, `show verdict`, `seal verification`) consume the next token as part of the route selector. If missing or invalid, **ABORT** (agent-honor-system): name the token received and emit the route roster in **Route**.
2. Load the mapped route file under this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `init` -> [init](init/index.md); `join` -> [join](join/index.md); `speak` -> [speak](speak/index.md); `retract speak` -> [retract-speak](retract-speak/index.md); `rewrite speak` -> [rewrite-speak](rewrite-speak/index.md); `advance` -> [advance](advance/index.md); `restore` -> [restore](restore/index.md); `set` -> [set](set/index.md); `unset` -> [unset](unset/index.md); `list` -> [list](list/index.md); `activate` -> [activate](activate/index.md); `open` -> [open](open/index.md); `reopen` -> [reopen](reopen/index.md); `close` -> [close](close/index.md); `remove participant` -> [remove-participant](remove-participant/index.md); `archive` -> [archive](archive/index.md); `delete` -> [delete](delete/index.md); `write summary` -> [write-summary](write-summary/index.md); `rewrite summary` -> [rewrite-summary](rewrite-summary/index.md); `run plan` -> [run-plan](run-plan/index.md); `aggregate` -> [aggregate](aggregate/index.md); `export-issues` -> [export-issues](export-issues/index.md); `rewrite execution` -> [rewrite-execution](rewrite-execution/index.md); `participant verify` -> [participant-verify](participant-verify/index.md); `show policy` -> [show-policy](show-policy/index.md); `show flags` -> [show-flags](show-flags/index.md); `show verdict` -> [show-verdict](show-verdict/index.md); `seal verification` -> [seal-verification](seal-verification/index.md).
- **Parameters:** route selector from the signature above.
- **Bare namespace help:** A bare `/collab` invocation aborts without mutation and emits the route roster in **Route**. It must not dispatch to any collab route by default.
- **Examples:** `/collab init "Slash Command UX and DX Polish"`, `/collab join --role tw`, `/collab activate slash-command-ux-and-dx-polish`, `/collab set turn-order tw pe`, `/collab unset reviewer`, `/collab speak`, `/collab retract speak`, `/collab rewrite speak`, `/collab restore`, `/collab list`, `/collab archive 1`, `/collab delete slash-command-ux-and-dx-polish`, `/collab run plan`, `/collab aggregate`, `/collab export-issues issues.json`, `/collab rewrite execution`, `/collab reopen handoff`, `/collab show flags`, `/collab show verdict`.
- **Registry model:** The default registry is resolved from the checked-in `.collab.json` repo marker to `$HOME/.collabs/<projectId>/registry.json` in the user-scope collab state root; `--registry` is the explicit override. The registry stores one top-level `activeCollabId` pointer plus a `collabs[]` roster keyed by stable `id` and user-facing `slug`. Transcript files under the resolved `records/*.md` mirror selected metadata for human context only.
- **Lifecycle:** `init` → `join × N` → `speak × N` → `advance` / `restore` / `set` → `close` (or `run plan` then `close` for action-plan collabs). Use `list` and `activate` for active-collab management instead of filesystem navigation.
- **Phase commands:** Per-role command sequence by phase: [`commands/collab/reference/phase-commands.md`](../../commands/collab/reference/phase-commands.md).
- **Glossary:** Canonical collab vocabulary: [`commands/collab/reference/glossary.md`](../../commands/collab/reference/glossary.md).
- **Boundary:** `/collab` maintains a registry-backed collab transcript. `/collab run plan` and `/collab rewrite execution` are the exceptions: they implement action-plan items assigned to the executing agent's role, run repository validation, and record the result. All other routes mutate registry state and sync the transcript only.
