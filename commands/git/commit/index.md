# /git commit

Split the working tree into atomic commits, or squash an inclusive `FROM..TO` range into one commit, using real `git` commands and subjects from [git-convention](../../../core/framework/git-convention.md).

## Trigger

**Slash:** `/git commit`
**Signature:** `/git commit <atomic | squash>`
**Prose dispatch:** `(git commit <atomic | squash>)` — prose routing hint; not a terminal command.
**Search phrases:** `atomic commits`, `split into atomic commits`, `commit by logical change`, `squash commits`, `squash these commits`, `combine commits`

## Steps

1. Load [git-convention](../../../core/framework/git-convention.md). If it is not directly readable, **ABORT** per **`context-gate.md`**.
2. Resolve mode from the first argument: `atomic` → **Atomic path**; `squash` → **Squash path**. If the mode keyword is missing or invalid, **ABORT** and emit the allowed value set: `atomic | squash`. For `squash`, accept either no extra args (auto mode) or both `<from>` and `<to>` (range mode); **ABORT** if exactly one SHA is provided and emit the range shape `squash <from> <to>`.
3. Execute the chosen path in **Notes** end to end. Do not skip safety checks there.
4. Keep chat output for subjects aligned with **`git-convention.md`** **Output contract**. On the **Squash path**, a multi-line message with `- ` body bullets is permitted per that rule and this playbook.

## Notes

- **Route (atomic vs squash).** Determined by the required mode arg. Carry **`FROM`**, **`TO`**, file subsets, or subjects from the message into the path.
- **Parameters:** `<atomic | squash>` — mode keyword (required): `atomic` splits the working tree. `squash` supports auto mode (no SHAs) and range mode (`<from> <to>` both required). See **Stage signatures** below.
- **Missing mode help:** A bare `/git commit` invocation aborts before any git command and emits `<atomic | squash>`.
- **Stage signatures:** `/git commit atomic` — no extra arguments; splits the working tree. `/git commit squash` — no extra arguments; auto mode, builds from current working-tree changes. `/git commit squash <from> <to>` — both `<from>` and `<to>` required; range mode collapses `FROM..TO`; **ABORT** if exactly one SHA is provided.
- **Dependencies:** Subjects and squash body lines follow **`git-convention.md`** **Format** and **Compliance**. Summary and each squash bullet line stay ≤72 characters including `type(scope): `. Squash bodies use Markdown `- ` bullets; that exception does not change Conventional Commit subject rules.
- **Scope:** Applies on **`/git commit`** and when natural language clearly means atomic-only or squash-only work.
- **Atomic path.** Run from repo root. If `git status` is clean, report and stop. Run `git status --porcelain` and count dirty files. If the count exceeds 40, do not proceed to diff inspection yet: group dirty files by top-level directory, display a phase plan showing each directory with its file count and estimated commit count, then gate the scope confirmation per `core/framework/command-argument.md` — ask once and do not ask again between phases. On confirmation, execute each phase sequentially in one continuous run; each phase follows the full atomic path below. Inspect `git status --porcelain`, unstaged diff, and staged diff before grouping. Build an outcome-based grouping plan before any staging: list each proposed commit in buildable order, the paths or hunks included, and the diff evidence showing that every included change supports the same user-visible behavior, documentation change, test change, or structural change. Show that grouping plan to the user before the first `git add`. Do not run `git add .`, `git add -A`, or broad path staging in this route. Stage only the paths or hunks named in the displayed grouping plan; use `git add -p` when one file contains hunks for multiple outcomes. If a mixed file cannot be split safely, **ask one focused question** before committing. For each group: `git commit -m "type(scope): description"` per **`git-convention.md`** with whole subject ≤72 characters. Repeat until clean. Do **not** push, force-push, amend, or rebase unless the user explicitly asks. Prefer diff evidence; **ask one focused question** when grouping is ambiguous; honor user file subsets.
- **Atomic-path scope gate.** Applied when dirty-file count exceeds 40; gate contract: `core/framework/command-argument.md`.

  ```route-gate
  gate-class: standard
  proceed: confirm
  abort: cancel
  operand-format: none
  invalid-input: re-prompt
  re-prompt-template: Type "confirm" to proceed with all phases, or "cancel" to abort.
  ```

- **Squash path.** Two execution modes:
- **Squash auto mode (`/git commit squash`).** Build a meaningful one-commit summary from current file changes, not from pre-existing commit boundaries. Procedure: (1) Require dirty tree; if clean, report and stop. (2) Snapshot candidate paths from current status (`git status --porcelain` plus staged/unstaged file lists) and treat that as the exact allowed set for this operation. (3) Run the **Atomic path** against only that snapshot set: create minimal logical commits; never stage files outside the snapshot; never create or resurrect old files outside the snapshot. (4) Collect the new atomic subjects verbatim, in chronological order, before the soft reset. (5) Let `FROM` be the first new atomic commit and `TO` be `HEAD`; compute `base=$(git rev-parse FROM^)`; `git reset --soft "$base"`. (6) Compose one message: first line compliant summary ≤72 chars; blank line; body `- ` lines from the collected atomic subjects exactly as collected, one per atomic outcome and in chronological order. (7) Commit with `git commit -F` or equivalent; do **not** collapse to summary-only unless the user asks. (8) Show `git log --oneline -3` and report the snapshot path count plus `FROM`, `TO`, and `base`.
- **Squash range mode (`/git commit squash <from> <to>`).** User supplies inclusive **`FROM..TO`** (often `TO` is `HEAD`). Meaning: `git reset --soft FROM^` stages all changes from `FROM` through `TO`; requires `FROM` ancestor of `TO` and linear history; **`FROM^` must exist**. Prefer clean `git status`; if dirty, stop and ask to stash, discard, or abort. Procedure: (1) `git log --reverse --format=%s FROM^..TO` collecting subjects (strip `fixup!` / `squash!` when building bullets). (2) `base=$(git rev-parse FROM^)`. (3) `git reset --soft "$base"`. (4) Compose one message: first line compliant summary ≤72 chars; blank line; body `- ` lines one per squashed subject in chronological order, each line a compliant subject or shortened equivalent. (5) Commit with `git commit -F` or equivalent; do **not** collapse to summary-only unless the user asks. (6) Show `git log --oneline -3`. Echo **`FROM`**, **`TO`**, **`base`** before reset. If range was pushed, warn about force-push; never force-push unless asked. If ancestry fails or history is merge-heavy, stop and suggest interactive rebase.
- **Handoff (squash):**

```text
/git commit squash
FROM: <sha>
TO: <sha>
```

Optional subject hint on the next line.

```route-arg
dispatch: (git commit <atomic | squash>)
param: name=<atomic | squash>; required=required; placeholder=<atomic | squash>; class=literal; values=atomic | squash
```
