# Migrate collab state dirs

`migrate-collab-state-dirs.sh` rebinds a project from its existing `projectId` to the readable, collision-safe slug that `project_id_for_project()` assigns today. Run it once per repo after upgrading from a registry seeded with UUID-hex ids. It is the sole authority for the atomic three-surface rewrite: directory rename + registry `project.projectId` + `.collab.json` `projectId`. It also handles empty-orphan cleanup via `--delete-empty-orphan`.

## Preconditions

- **Quiesce agents.** No agent may hold a lock on the user-scope collab state root during migration. A held `registry.json.lock` causes the script to abort without making any changes.
- **One project at a time.** Migrate each repo to completion before starting the next. No cross-repo coordination is built in.
- **Writable surfaces.** The invoking process must have write access to `.collab.json` and to the user-scope collab state root directory.

## Migration steps

**Step 1.** Run from the repo root, or pass `--project-root` explicitly:

```
platform/tooling/migrate-collab-state-dirs.sh [--project-root <path>] [--state-home <path>]
```

Omit `--state-home` to use `$HOME/.collabs/`.

**Step 2.** Inspect the JSON output on stdout:

- `"status": "migrated"` — all three surfaces rewritten; the old directory is gone.
- `"status": "already-complete"` — the project was already on its readable slug; no changes made.
- `ABORT: ...` on stderr — no change committed; see the message for the cause.

**Step 3.** If the migration left an empty UUID directory behind, clean it up:

```
platform/tooling/migrate-collab-state-dirs.sh --state-home <path> --delete-empty-orphan <old-id>
```

The script refuses to delete non-empty directories; only empty orphans are eligible.

**Step 4.** Verify binding coherence by running `platform/tooling/audit.sh`. The registry-lock check reads `.collab.json`, resolves the user-scope collab state root, and validates the registry.

## Collision suffixing

`project_id_for_project()` derives the preferred slug from the project label or directory name: lowercase, non-alphanumeric runs replaced with hyphens, stripped of leading and trailing hyphens, padded to at least 4 characters. A project labeled `nsmac` gets slug `nsmac`; one labeled `noobsociety.com` gets `noobsociety-com`.

When the preferred slug is already occupied by another project's user-scope collab state root directory, a deterministic 8-character disambiguator is appended — derived from the sha256 of the project's absolute path. Example: `noobsociety-com-3f4a1b2c`. The suffix is reproducible: re-running `project_id_for_project()` on the same project root always produces the same disambiguator. The "readable" half of the name remains human-recognizable; the disambiguator makes it collision-safe.

If the suffixed slug is also occupied (in practice, two distinct repos whose absolute paths share the same 8-character sha256 prefix), a numeric ordinal follows: `noobsociety-com-3f4a1b2c-2`, then `noobsociety-com-3f4a1b2c-3`, and so on until an unoccupied slot is found.

`migrate-collab-state-dirs.sh` uses the same `project_id_for_project()` call as `init`. If the current `projectId` already matches the computed slug, the script reports `"already-complete"` and exits without making any changes.

## Rollback and fail-loud behavior

The rename and two-surface update execute under an exclusive `flock` on `registry.json.lock`. If any step fails after the directory rename but before both writes complete, the script rolls back: restores the original registry text, renames the directory back to the old `projectId`, and re-writes `.collab.json`. The repo and user-scope collab state root are left in their pre-migration state.

`ABORT:` on stderr always signals no committed change. A stale zero-byte lock file from a prior crash is tolerated; the script detects it by size and age and proceeds rather than blocking.

Post-migration, `registry.json` gains a `projectIdMigrations` array entry recording `oldProjectId`, `newProjectId`, `sourceMarker`, `registryPath`, and `timestamp`. `.collab.json` gains `state.previousProjectId` and `state.projectIdMigratedAt` for audit.
