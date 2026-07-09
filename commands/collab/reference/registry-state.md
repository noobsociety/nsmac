# Registry state

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** registry state, state root resolution, project identity, user-scope collab state root, resolve_default_registry_path, collab project identity contract, collab repo marker schema, projectId binding rules

## Steps

1. Read this document when auditing or changing `commands/collab/engine/registry_state.py` behavior.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The spec covers `commands/collab/engine/registry_state.py` — state-root and project-identity resolution. Extracted from `registry.py` in commit `a55380c`. The module handles path resolution only; it does not read or write registry or transcript data.

### Public entry

`resolve_default_registry_path(command: str | None) -> tuple[Path, bool]`

Called by `commands/collab/engine/registry.py` before any registry read or write. Returns the resolved path to `registry.json` (at `$STATE_HOME/<projectId>/registry.json`) and a boolean indicating a default-path resolution. The `projectId` is read from the `.collab.json` marker found by walking up from `cwd`.

On `init` commands, the `.collab.json` marker is written if absent. On all other commands, the marker must already exist; if it is not found, the module aborts.

### Firing point

Load-time, before any registry read. Fires on every registry-loading command.

### State-root resolution

The state root is `$HOME/.collabs/<projectId>/` by default, or the path from the `COLLAB_STATE_HOME` environment variable when set. The `projectId` is a readable, collision-safe slug seeded once at `init` time and recorded in `.collab.json`. The marker is never changed after creation; `projectId` rebinding to a different state root is a hard rejection.

The user-scope collab state root is deliberately non-XDG because records are user-browsed, repo-independent operational state. The `$HOME` expansion happens at runtime; the absolute path is not stored in the repo. `COLLAB_STATE_HOME` is a test-isolation hook, not a supported production configuration surface. Repo-local `.collabs/` state has been retired; new records are created only under the user-scope collab state root, and the resolver reads no repo-local fallback.

| Path under state root | Description |
| --- | --- |
| `registry.json` | Registry backing all collab routes. |
| `records/` | Transcript files (`*.md`). |
| `label` | Non-authoritative plain-text projection of the project label; updated on each resolver invocation when the content differs from `.collab.json`. |

### Project identity file

`.collab.json` is placed at the repository root and tracked in version control.

| Field | Type | Description |
| --- | --- | --- |
| `projectId` | string | Readable, collision-safe slug. Seeded once at init; never re-derived from the live directory, path, basename, remote, or worktree; never changed on rename/move/fork. |
| `label` | string | Human-readable project name; used for display only, not resolution. |
| `state.mode` | string | Worktree sharing mode: `"shared"` (default) or `"isolated"`. |
| `state.isolation` | string | Isolation opt-in policy: `"opt-in"` means isolation requires explicit configuration per worktree. |

A renamed or forked repository carries the same `projectId` and resolves to the same state root.

**Slug generation:** At `init`, the `projectId` is derived from the project label (or directory name when no label is given) by lowercasing, replacing non-alphanumeric runs with hyphens, stripping leading and trailing hyphens, and padding to at least 4 characters. When the preferred slug is already occupied by another project's state-root directory, a deterministic 8-character suffix — the sha256 of the project's absolute path, truncated — is appended (e.g., `noobsociety-com-3f4a1b2c`). The suffix is reproducible: the same project root always produces the same disambiguator. If that slot is also taken, a numeric ordinal follows (`-2`, `-3`, …).

### Worktree behavior

The default mode is `"shared"`: all worktrees of a repository resolve to the same state root and share `registry.json` and `records/`. A worktree may opt into isolation explicitly (`state.mode: "isolated"`); no per-worktree root is created automatically. The isolation opt-in is scoped to the worktree configuration and does not change the identity file.

**Label projection:** The `label` field is display metadata only. The helper projects it from `.collab.json` into registry project metadata during writes, uses the identity-file value for list display when available, and synchronizes the state root's `label` file whenever the resolver runs. Updating `label` never changes `projectId` or the resolved path.

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
- `project identity projectId must be a readable, collision-safe slug: <path>`
- `project identity label must be a non-empty string when present: <path>`
- `project identity state must be an object when present: <path>`

**Project identity mismatch (rebinding guard)**

Fires when the `projectId` recorded in the loaded registry does not match the `projectId` in `.collab.json`. Prevents using a registry file with a different project.

Exit-1 messages (exact):

- `<registry_path>: project must be an object when present`
- `project identity mismatch: registry <path> is bound to <actual>; marker .collab.json declares <expected>`

**Module-to-subcommand map row:** `participant-role-files` in `commands/collab/reference/helper-output.md` covers the registry-loading commands that invoke this module's validation path.
