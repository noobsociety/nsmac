# (agent upgrade)

Apply current scaffold templates to an already-installed multi-agent scaffold in the current repository.

## Trigger

**Dispatch:** `(agent upgrade [--force])` — routing-only command form; not a shell command.
**Search phrases:** agent upgrade, upgrade multi-agent scaffold, upgrade scaffold templates

## Steps

1. Resolve the repo root as the target repository root: the git repository root for the project maintaining scaffold files. This may be the same path as the global runtime root at `~/nsmac`. If not inside a git repository, **ABORT**: must be run from a git repository root.
2. Parse flags immediately after the route selector and before any positional arguments per [platform/standards/command-argument.md](../../../platform/standards/command-argument.md). `--force` is supported only in that pre-positional slot. Unsupported or misplaced flags **ABORT** before any route mutation.
3. Verify `AGENTS.md`, `CLAUDE.md`, and `REPOSITORY.md` exist in the repo root. If any is missing, **ABORT** naming the missing path — run `(agent install)` first.
4. Read the installed `AGENTS.md` and locate the `<!-- scaffolded-at: <ISO-date> -->` marker line. If absent, **ABORT**: scaffolded-at marker not found in `AGENTS.md`; restore the marker manually or reinstall with `(agent install)` in a fresh repo.
5. Read `~/nsmac/platform/templates/AGENTS.md` and locate its `<!-- scaffolded-at: <ISO-date> -->` marker line.
6. Compare the two marker strings using lexicographic equality. Build the current candidate content for every scaffold file from its corresponding template, applying install-owned marker resolution to `AGENTS.md` and `CLAUDE.md`. If the markers match and every installed file is identical to its candidate content, report "scaffold is up to date" and exit.
7. For `REPOSITORY.md`: compare the installed file against `~/nsmac/platform/templates/REPOSITORY.md`. If the proposed change overlaps any section that has been patched beyond the scaffold-owned header — that is, any content that is not a `<!-- TODO(patch): ... -->` placeholder — and `--force` is absent, record a targeted skip message for `REPOSITORY.md` and exclude it from the confirmation step. Proceed to evaluate the remaining files. When `--force` is supplied, keep `REPOSITORY.md` in the collected overwrite set and defer the decision to the diff and gate.
8. For each of `AGENTS.md` and `CLAUDE.md` where the installed file differs from its candidate content, and for `REPOSITORY.md` when it remains eligible after step 7, collect the file and compute a per-file changed-block summary: file name, before/after view of the changed sections, and a statement of what will be overwritten; if any `TODO(install)` marker would survive in the candidate patch, **ABORT**: unresolved install placeholder.
9. If `AGENTS.md` is in the collected overwrite set and the installed `AGENTS.md` contains a link to `commands/commands.md` in the Entry points section: check whether the target repo's `AGENTS.md` file satisfies both (a) the `<!-- scaffolded-at: ... -->` marker is present and (b) the target repo does not contain `platform/templates/AGENTS.md` at any tracked path. When both conditions are met, add to the candidate patch: remove the `commands/commands.md` entry from the Entry points list. Do not apply this rewrite unless both conditions are met. Skip this step silently when `AGENTS.md` is not in the collected set or when the link is absent.
10. If no files remain after step 7 excludes `REPOSITORY.md` and no other file differs, report "scaffold is up to date" with a note that `REPOSITORY.md` was skipped due to patched-section overlap, and exit.
11. Present each collected file with its changed-block summary before presenting the gate. When `--force` is supplied, compute `the candidate patch` for the collected overwrite set and render the diff from `the candidate patch`, then present the same gate. Gate the overwrite per `platform/standards/command-argument.md`, using the repository path or name as the operand:

   ```route-gate
   gate-class: destructive
   proceed: overwrite <repo>
   abort: cancel
   operand-format: repository path or name displayed in context
   invalid-input: re-prompt
   re-prompt-template: Type "overwrite <repo>" (replacing <repo> with the repository path) to confirm overwriting scaffold files, or "cancel" to abort.
   ```

   If the user does not type the exact proceed token, leave all files and the marker untouched. Report which files had unconfirmed changes.
12. If confirmed: write every accepted file from the corresponding candidate content, with install-owned marker resolution already applied for `AGENTS.md` and `CLAUDE.md`. When `--force` is supplied, apply `the candidate patch` without recomputation or re-read of source. All writes are all-or-nothing — if any single write fails, treat the entire set as failed and do not leave a partial upgrade. The marker in the newly written `AGENTS.md` is the current template marker value; no separate marker update step is needed.
13. Report all files written and the new scaffold version marker value. If `REPOSITORY.md` was skipped, include the skip reason in the report.

## Notes

- **Parameters:** `--force` — optional pre-positional flag. Default target is the repo root where the command runs.
- **Examples:** `(agent upgrade)`, `(agent upgrade --force)`.
- **Invocation context:** Run this command from the target repository root. A checkout developed in place at `~/nsmac` is a valid target repository root, so a target path of `~/nsmac` is permitted.
- **Boundary:** Reads installed scaffold files and `~/nsmac/platform/templates/`; writes only `AGENTS.md`, `CLAUDE.md`, and (when overlap-free) `REPOSITORY.md` in the repo root. Leaves template sources, command sources, rule sources, and agent settings JSON unchanged.
- **Idempotency:** Re-running upgrade on an already-current scaffold reports "scaffold is up to date" and exits without modifying any file; install-owned marker resolution is part of this comparison.
- **Marker comparison:** Compare the full `<!-- scaffolded-at: <ISO-date> -->` comment line as a string using lexicographic equality. Do not parse the date or apply date arithmetic. Equal → up to date; not equal → present diff and confirm.
- **`REPOSITORY.md` overlap check:** `REPOSITORY.md` is upgraded only when the proposed change is confined to scaffold-owned text. If any patched section (consumer-authored content that replaced a `<!-- TODO(patch): ... -->` placeholder) falls inside the changed region, the upgrade for that file is aborted with a targeted message and the other files continue. The abort is file-scoped, not a full-route abort.
- **Install-owned marker resolution:** Upgrade reuses install-owned marker resolution for overwritten `AGENTS.md` and `CLAUDE.md` candidate content. An accepted upgrade must not write surviving `TODO(install)` markers.
- **Marker-missing abort:** A present `AGENTS.md` without the scaffolded-at marker line is an unknown-state scaffold. Do not infer an older version; abort with a specific message so the user can restore the marker manually.
- **Confirm-before-write:** The confirmation step is mandatory and not optional. Gate contract: `platform/standards/command-argument.md`. On refusal or absent confirmation, no file is written and the marker is untouched.
- **Force flag:** `--force` is eligible only for the route's gated overwrite path. `--force` does not bypass incomplete-scaffold, marker, unreadable-template, all-or-nothing, validation, or permission failures.
- **All-or-nothing write:** All confirmed files are written as a set. If any single write fails mid-set, the entire set is treated as failed; do not leave a partial upgrade.
- **Marker-as-comment risk:** The `<!-- scaffolded-at: ... -->` marker is an HTML comment with no structural protection. If `AGENTS.md` is ever edited by a tool that rewrites the file body, the marker could be moved or removed. Today `(agent patch)` does not edit `AGENTS.md`, so this is not a current failure mode — but if that changes, the marker becomes load-bearing surface that looks like a comment.
- **Next step after upgrade:** If `REPOSITORY.md` was skipped due to patched-section overlap and a scaffold change to that file is important, apply the change manually.
- **Upgrade rewrite rule for `commands/commands.md` link:** See step 9. Both conditions must be met for the rewrite to apply; otherwise the step is a no-op.

```route-arg
dispatch: (agent upgrade [--force])
param: name=--force; required=optional; placeholder=--force; class=literal; values=present; default=literal:false
```

```route-flag
flag: force
eligibility: eligible
guard-class: gated-overwrite
```
