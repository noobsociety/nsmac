# Collab project identity contract

The checked-in repo marker (`.collab.json`) binds a repository to the repository's user-scope collab state root. The contract governs the file schema, the `projectId` binding rules, and the state-root resolver's behavior.

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
  | `projectId` | string | Readable, collision-safe slug. Seeded once at init from a sanitized slug; never re-derived from the live directory, path, basename, remote, or worktree; never changed on rename/move/fork. |
  | `label` | string | Human-readable project name; used for display only, not resolution. |
  | `state.mode` | string | Worktree sharing mode: `"shared"` (default) or `"isolated"`. |
  | `state.isolation` | string | Isolation opt-in policy: `"opt-in"` means isolation requires explicit configuration per worktree. |

- **Identity properties:** `projectId` is a readable, collision-safe slug, seeded once at init; never re-derived from the live directory, path, basename, remote, or worktree; never changed on rename/move/fork. A renamed or forked repository carries the same `projectId` and resolves to the same state root.

- **Slug generation:** At `init`, the `projectId` is derived from the project label (or directory name when no label is given) by lowercasing, replacing non-alphanumeric runs with hyphens, stripping leading and trailing hyphens, and padding to at least 4 characters. When the preferred slug is already occupied by another project's user-scope collab state root directory, a deterministic 8-character suffix — the sha256 of the project's absolute path, truncated — is appended (e.g., `noobsociety-com-3f4a1b2c`). The suffix is reproducible: the same project root always produces the same disambiguator. If that slot is also taken, a numeric ordinal follows (`-2`, `-3`, …). The algorithm ensures every slug is human-readable at its preferred name and collision-safe through deterministic disambiguation. See [`migrate-collab-state-dirs.md`](../../../platform/tooling/migrate-collab-state-dirs.md) for the operator migration procedure.

- **State root:** The resolver maps `projectId` → `$HOME/.collabs/<projectId>/`. This user-scope collab state root is deliberately non-XDG because records are user-browsed, repo-independent operational state. The `$HOME` expansion happens at runtime; the absolute path is not stored in the repo. The resolver accepts a `COLLAB_STATE_HOME` environment variable that replaces `$HOME/.collabs/` as the base path; the variable is a test-isolation hook and is not a supported production configuration surface. An established `projectId` is never rebound except by `migrate-collab-state-dirs.sh` (in `platform/tooling/`), the sole authority, via atomic rewrite of directory name + `.collab.json` marker + `registry.json.project.projectId`.

- **Collision suffix:** When two project roots sanitize to the same `projectId`, the second root receives a short SHA-256 suffix derived from its resolved path. The suffix is deliberately path-based rather than ordinal-based so the same project path keeps the same disambiguator without a separate allocation ledger.

- **Migration operation:** `platform/tooling/migrate-collab-state-dirs.sh` is a thin shell entrypoint for `platform/tooling/migrate_collab_state_dirs.py`. Run it with `--project-root <repo>` for the primary consuming repo and repeat `--extra-project-root <repo>` for additional checked-out repos whose `.collab.json` points at the same old `projectId`; the tool rewrites all listed markers in the same rollback-protected transaction. Empty orphan roots are deleted only by explicit `--delete-empty-orphan <projectId>`. A successful migration reports JSON containing `oldProjectId`, `newProjectId`, `sourceMarkers`, `registryPath`, and `timestamp`.

  | Path under state root | Description |
  | --- | --- |
  | `registry.json` | Registry backing all collab routes. |
  | `records/` | Transcript files (`*.md`). |
  | `label` | Non-authoritative plain-text projection of the project label; updated on each resolver invocation when the content differs from `.collab.json`. |

- **Worktree behavior:** The default mode is `"shared"`: all worktrees of a repository resolve to the same state root and share `registry.json` and `records/`. A worktree may opt into isolation explicitly (`state.mode: "isolated"`); no per-worktree root is created automatically. The isolation opt-in is scoped to the worktree configuration and does not change the identity file.

- **Label projection:** The `label` field is display metadata only. The helper projects it from `.collab.json` into registry project metadata during writes, uses the identity-file value for list display when available, and synchronizes the user-scope collab state root `label` file whenever the resolver runs. Updating `label` never changes `projectId` or the resolved path.

- **Repo-local state:** Repo-local `.collabs/` state has been retired. New records are created only under the user-scope collab state root, and the resolver does not read `.collabs/project.json` or `.collabs/registry.json` as a fallback.
