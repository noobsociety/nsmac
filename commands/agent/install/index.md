# /agent install

Install the multi-agent scaffold into the current repository from `~/.cursor/platform/templates/`.

## Trigger

**Slash:** `/agent install`
**Signature:** `/agent install [--force]`
**Prose dispatch:** `(agent install [--force])` — prose routing hint; not a terminal command.
**Search phrases:** agent install, bootstrap multi-agent setup, install agent scaffold

## Steps

1. Resolve the repo root as the target repository root by running `git rev-parse --show-toplevel` from the current working directory. The current working directory may be the repo root or any nested path inside the target git work tree; scaffold files are written to the resolved repo root. This may be the same path as the global runtime root at `~/.cursor`. If the current working directory is not inside a git work tree, **ABORT**: current working directory is not inside a git work tree; navigate to the target repository root or a nested path within it and re-run.
2. Verify `~/.cursor/platform/templates/CLAUDE.md`, `~/.cursor/platform/templates/AGENTS.md`, `~/.cursor/platform/templates/GEMINI.md`, and `~/.cursor/platform/templates/REPOSITORY.md` all exist. If any is missing, **ABORT** naming the missing path.
3. Parse flags immediately after the route selector and before any positional arguments per [platform/standards/command-argument.md](../../../platform/standards/command-argument.md). `--force` is supported only in that pre-positional slot. Unsupported or misplaced flags **ABORT** before any route mutation.
4. For each of `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `REPOSITORY.md`, check whether the file already exists in the repo root. If any exists and `--force` is absent, **ABORT**: file already exists; name every conflicting path. Do not overwrite.
5. Compute `the candidate patch` for all four scaffold writes from the template contents. During candidate-patch computation, resolve every `<!-- TODO(install): ... -->` marker in `CLAUDE.md` and `AGENTS.md` from the target repository identity, then remove the marker. If any `TODO(install)` marker would survive in the candidate patch, **ABORT**: unresolved install placeholder. When `--force` is supplied and any scaffold file exists, render the diff from `the candidate patch`, and gate the write per [platform/standards/command-argument.md](../../../platform/standards/command-argument.md):

   ```route-gate
   gate-class: standard
   proceed: confirm
   abort: cancel
   operand-format: none
   invalid-input: re-prompt
   re-prompt-template: Type "confirm" to overwrite scaffold files, or "cancel" to abort.
   ```

   If the user does not type the exact proceed token, leave all files untouched. If confirmed, continue to the copy steps.
6. Copy `~/.cursor/platform/templates/CLAUDE.md` to `<repo-root>/CLAUDE.md`.
7. Copy `~/.cursor/platform/templates/AGENTS.md` to `<repo-root>/AGENTS.md`.
8. Copy `~/.cursor/platform/templates/GEMINI.md` to `<repo-root>/GEMINI.md`.
9. Copy `~/.cursor/platform/templates/REPOSITORY.md` to `<repo-root>/REPOSITORY.md`. These copy steps apply `the candidate patch` without recomputation or re-read of source.
10. Validate scaffold-local install state: confirm `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `REPOSITORY.md` exist in the repo root, confirm `CLAUDE.md` routes to `AGENTS.md`, confirm `GEMINI.md` routes to `AGENTS.md`, confirm `AGENTS.md` references `~/.cursor/commands/commands.md`, confirm `AGENTS.md` contains the canonical routing-only prose dispatch sentence (the line beginning `To invoke a global command, resolve any routing-only prose dispatch hint`), confirm `AGENTS.md` contains the `<!-- scaffolded-at: <ISO-date> -->` marker line, confirm no installed scaffold file contains unresolved `<!-- TODO(install): ... -->` markers, confirm `REPOSITORY.md` still contains unresolved `<!-- TODO(patch): ... -->` placeholders, and confirm every Markdown link in the installed `AGENTS.md` whose target does not begin with `~` or `http` resolves as a file path relative to the repo root; if any link does not resolve, **ABORT** naming the unresolvable path.
11. Report the four files written and list any unresolved `<!-- TODO(patch): ... -->` placeholders remaining in `REPOSITORY.md`.

## Notes

- **Precondition:** The global command surface (`~/.cursor/`) must be reachable before this route is invoked. In environments without it on the command path, invoke explicitly (e.g., `~/.cursor/...`) on first use. The requirement is reachability; the invocation form depends on the agent surface.
- **Invocation context:** Run this command from the target git work tree. The current directory may be the target repository root or a nested path inside it; scaffold files are written to the resolved repository root. A checkout developed in place at `~/.cursor` is a valid target repository root, so a target path of `~/.cursor` is permitted.
- **Placeholder standard:** `AGENTS.md` and `CLAUDE.md` use `<!-- TODO(install): <description> -->` markers resolved during install candidate-patch computation. `REPOSITORY.md` uses `<!-- TODO(patch): <description> -->` markers resolved by `/agent patch`.
- **Parameters:** `--force` — optional pre-positional flag. Default target is the repo root where the command runs.
- **Examples:** `/agent install`, `/agent install --force`.
- **Validation:** The install workflow uses scaffold-local checks only: file presence, `CLAUDE.md` → `AGENTS.md` routing, `GEMINI.md` → `AGENTS.md` routing, the `AGENTS.md` reference to `~/.cursor/commands/commands.md`, the `AGENTS.md` prose dispatch sentence, no unresolved `TODO(install)` markers, and unresolved `REPOSITORY.md` `TODO(patch)` placeholders.
- **Force flag:** `--force` is eligible only for existing scaffold-file conflicts. It does not bypass missing-template, repository-root, validation, or permission failures.
- **Scaffold marker:** The `<!-- scaffolded-at: ... -->` marker line is present in `~/.cursor/platform/templates/AGENTS.md` and copied verbatim to the installed `AGENTS.md`. This marker is used by `/agent upgrade` to detect when an upgrade is needed.
- **Next step:** Run `/agent patch` to fill `<!-- TODO(patch): ... -->` placeholders in `REPOSITORY.md` with repo-specific mutation protocol and ownership rules.

```route-arg
dispatch: (agent install [--force])
param: name=--force; required=optional; placeholder=--force; class=literal; values=present; default=literal:false
```

```route-flag
flag: force
eligibility: eligible
guard-class: hard-abort
```
