# Collab project identity contract

The checked-in repo marker (`.collab.json`) binds a repository to its user-scope collab state root. This contract governs the file schema, the `projectId` binding rules, and the state-root resolver's behavior.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab project identity contract, collab repo marker schema, projectId binding rules

## Steps

1. Read this document when changing `.collab.json`, project id resolution, state-root binding, or worktree-sharing behavior.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

- **Identity file:** `.collab.json` is placed at the repository root and tracked in version control.

  | Field | Type | Description |
  | --- | --- | --- |
  | `projectId` | string | Opaque identifier. Never derived from directory name, path, remote URL, basename, or worktree. Set once at project initialization; never changed. |
  | `label` | string | Human-readable project name; used for display only, not resolution. |
  | `state.mode` | string | Worktree sharing mode: `"shared"` (default) or `"isolated"`. |
  | `state.isolation` | string | Isolation opt-in policy: `"opt-in"` means isolation requires explicit configuration per worktree. |

- **Identity properties:** `projectId` is opaque — tooling must not derive or infer it from path, basename, remote URL, or worktree location. The id follows git history: a renamed or forked repository carries the same id and resolves to the same state root. `projectId` is written once at initialization and never changed, even when `label` is updated or the repository is moved.

- **State root:** The resolver maps `projectId` → `$HOME/.collabs/<projectId>/`. This user-scope collab state root is deliberately non-XDG because records are user-browsed, repo-independent operational state. The `$HOME` expansion happens at runtime; the absolute path is not stored in the repo. The resolver accepts a `COLLAB_STATE_HOME` environment variable that replaces `$HOME/.collabs/` as the base path; this is a test-isolation hook and is not a supported production configuration surface.

  | Path under state root | Description |
  | --- | --- |
  | `registry.json` | Registry backing all collab routes. |
  | `records/` | Transcript files (`*.md`). |
  | `label` | Non-authoritative plain-text projection of the project label; updated on each resolver invocation when the content differs from `.collab.json`. |

- **Worktree behavior:** The default mode is `"shared"`: all worktrees of a repository resolve to the same state root and share `registry.json` and `records/`. A worktree may opt into isolation explicitly (`state.mode: "isolated"`); no per-worktree root is created automatically. The isolation opt-in is scoped to the worktree configuration and does not change the identity file.

- **Label projection:** The `label` field is display metadata only. The helper projects it from `.collab.json` into registry project metadata during writes, uses the identity-file value for list display when available, and synchronizes the user-scope collab state root `label` file whenever the resolver runs. Updating `label` never changes `projectId` or the resolved path.

- **Repo-local state:** Repo-local `.collabs/` state is retired. New records are created only under the user-scope collab state root, and the resolver does not read `.collabs/project.json` or `.collabs/registry.json` as a fallback.
