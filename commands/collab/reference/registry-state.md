# Registry state

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** registry state, state root resolution, project identity, user-scope collab state root, resolve_default_registry_path

## Steps

1. Read this document when auditing or changing `commands/collab/engine/registry_state.py` behavior.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Spec for `commands/collab/engine/registry_state.py` — state-root and project-identity resolution. Extracted from `registry.py` in commit `a55380c`. This module handles path resolution only; it does not read or write registry or transcript data.

### Public entry

`resolve_default_registry_path(command: str | None) -> tuple[Path, bool]`

Called by `commands/collab/engine/registry.py` before any registry read or write. Returns the resolved path to `registry.json` (at `$STATE_HOME/<projectId>/registry.json`) and a boolean indicating a default-path resolution. The `projectId` is read from the `.collab.json` marker found by walking up from `cwd`.

On `init` commands, the `.collab.json` marker is written if absent. On all other commands, the marker must already exist; if it is not found, the module aborts.

### Firing point

Load-time, before any registry read. Fires on every registry-loading command.

### State-root resolution

The state root is `$HOME/.collabs/<projectId>/` by default, or the path from the `COLLAB_STATE_HOME` environment variable when set. The `projectId` is opaque — a UUID hex generated once at `init` time and recorded in `.collab.json`. The marker is never changed after creation; `projectId` rebinding to a different state root is a hard rejection.

### Abort family

**Project marker missing**

Fires when `.collab.json` is not found from `cwd` upward (except on `init`).

Exit-1 message (exact): `project marker missing: .collab.json; run (collab init) from the project root`

**Project identity invalid JSON**

Exit-1 message (exact): `project identity invalid JSON: <path>: <detail>`

**Project identity malformed**

Exit-1 messages (exact):

- `project identity must be an object: <path>`
- `project identity contains disallowed version field: <path>`
- `project identity projectId must be an opaque lowercase id: <path>`
- `project identity label must be a non-empty string when present: <path>`
- `project identity state must be an object when present: <path>`

**Project identity mismatch (rebinding guard)**

Fires when the `projectId` recorded in the loaded registry does not match the `projectId` in `.collab.json`. Prevents using a registry file with a different project.

Exit-1 messages (exact):

- `<registry_path>: project must be an object when present`
- `project identity mismatch: registry <path> is bound to <actual>; marker .collab.json declares <expected>`

**Module-to-subcommand map row:** `participant-role-files` in `commands/collab/reference/helper-output.md` covers the registry-loading commands that invoke this module's validation path.

### Issue export evidence

`commands/collab/engine/registry.py export-issues <target> pe --evidence-file <path>` records the issue-terminal replacement close-gate in the resolved registry entry as `exportedIssues = { exportedAt, exportedBy, issues }`. The field is durable registry evidence, not transcript prose. Validation requires `exportedBy` to name a registered participant and `issues` to be a non-empty list of objects with a non-empty `title`; optional issue fields are normalized before storage.
