# /agent patch

Patch `REPOSITORY.md` in the current repository with repo-specific multi-agent mutation protocol and ownership rules.

## Trigger

**Slash:** `/agent patch`
**Signature:** `/agent patch [--force]`
**Prose dispatch:** `(agent patch [--force])` — prose routing hint; not a terminal command.
**Search phrases:** agent patch, patch repository, fill agent placeholders

## Steps

1. Resolve the repo root as the directory where the command runs.
2. Parse flags immediately after the route selector and before any positional arguments per [core/framework/command-argument.md](../../../core/framework/command-argument.md). `--force` is supported only in that pre-positional slot. Unsupported or misplaced flags **ABORT** before any route mutation.
3. Verify `REPOSITORY.md` exists in the repo root. If absent, **ABORT**: `REPOSITORY.md` not found; run `/agent install` first.
4. Read `REPOSITORY.md` in full.
5. Locate all `<!-- TODO(patch): <description> -->` placeholders. If none are found, **ABORT**: no `<!-- TODO(patch): ... -->` placeholders found; `REPOSITORY.md` may already be patched or was not installed via `/agent install`.
6. For each placeholder, infer repo-specific content from the current repository context. For validation commands, include a command path only when that exact path exists in the target repo; see **Validation inference scope** in **Notes**. When no eligible command is found, leave a bounded `<!-- TODO(patch): list repo-specific validation commands -->` placeholder. Use the `<description>` as the inference prompt. Display all inferred values. For placeholders that cannot be inferred, collect the values from the user before presenting the gate. When `--force` is supplied, compute `the candidate patch`, render the diff from `the candidate patch`, then present the same gate. Gate the write per `core/framework/command-argument.md`:

   ```route-gate
   gate-class: destructive
   proceed: overwrite REPOSITORY.md
   abort: cancel
   operand-format: REPOSITORY.md
   invalid-input: re-prompt
   re-prompt-template: Type "overwrite REPOSITORY.md" to confirm writing all inferred sections, or "cancel" to abort.
   ```

   If the user does not type the exact proceed token, stop without any change.
7. Replace each `<!-- TODO(patch): <description> -->` marker with the supplied repo-specific content. Do not edit any text outside placeholder blocks. When `--force` is supplied, apply `the candidate patch` without recomputation or re-read of source.
8. Write the updated `REPOSITORY.md`.
9. Validate scaffold-local patch state: confirm `REPOSITORY.md` still exists and no `<!-- TODO(patch): ... -->` markers remain.
10. Report each placeholder resolved and confirm no `<!-- TODO(patch): ... -->` markers remain.

## Notes

- **Placeholder standard:** Sections requiring repo-specific content are marked `<!-- TODO(patch): <description> -->`. Only these markers are replaced; all surrounding text is preserved exactly.
- **Idempotency:** Re-running patch on a `REPOSITORY.md` with no remaining placeholders aborts at step 4 rather than producing duplicate sections or overwriting custom content.
- **Parameters:** `--force` — optional pre-positional flag. Default target is `REPOSITORY.md` in the repo root.
- **Examples:** `/agent patch`, `/agent patch --force`.
- **Boundary:** Edits `REPOSITORY.md` only. Leaves `CLAUDE.md`, `AGENTS.md`, template sources, command sources, rule sources, and agent settings JSON unchanged.
- **Validation:** The patch workflow validates scaffold-local state only: `REPOSITORY.md` remains present and every `<!-- TODO(patch): ... -->` marker is resolved after the write.
- **Validation inference scope:** Validation commands may be inferred only from the target repo — do not copy command paths from sibling route playbooks or any other source outside the target repo root. Concrete failed example: copying a command path from a sibling route file that resolves under `~/.cursor/` but does not exist in the target repo. When the exact path does not resolve under the target repo, leave a bounded `<!-- TODO(patch): list repo-specific validation commands -->` placeholder.
- **Confirm-before-write:** `patch.md` is a confirm-before-write route; the confirmation step is mandatory and not optional for any placeholder. Gate contract: `core/framework/command-argument.md`.
- **Force flag:** `--force` is eligible only for the route's gated overwrite path. It does not bypass missing-file, idempotency, inference, validation, or permission failures.

```route-arg
dispatch: (agent patch [--force])
param: name=--force; required=optional; placeholder=--force; class=literal; values=present; default=literal:false
```

```route-flag
flag: force
eligibility: eligible
guard-class: gated-overwrite
```
