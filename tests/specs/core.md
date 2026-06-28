# QA — command core canon

Deterministic QA for `~/.cursor/platform/standards/*.md` canon documents.

## Procedure

1. Load every `*.md` under `~/.cursor/platform/standards/`.
2. Validate the roster is exact.
3. Validate each file has one H1 and is <= 250 lines.
4. Validate links in `platform/standards/` stay self-contained (sibling `platform/standards/*.md` links only).
5. Validate no platform standard depends on command routes, QA harnesses, host runtime paths, or retired root `core/` / `tools/` paths.
6. Validate owner consistency: style, document templates, command contract, context model, and voice guide do not conflict.
7. Validate `route-invariants.md` declares the four floor rules and that the floor-rules lint in `platform/tooling/` covers the `(collab init)`, `(collab join)`, `(collab speak)`, `(collab rewrite speak)`, `(collab advance)`, and `(collab restore)` pilot routes for helper-owned mutations, stop conditions, resume signals, and declared link targets.
8. Validate `route-sufficiency.md` declares `## Mechanical sufficiency` and `## Execution sufficiency`, includes the self-application statement, and marks execution sufficiency as fixture-backed rather than lintable.

## Required roster

- `author-voice.md`
- `command-argument.md`
- `command-convention.md`
- `command-default.md`
- `command-grammar.md`
- `command-standard.md`
- `context-gate.md`
- `context-management.md`
- `devblog-discipline.md`
- `doctrine.md`
- `document-standard.md`
- `flag-taxonomy.md`
- `framework-boundaries.md`
- `git-convention.md`
- `helper-subcommands.md`
- `markdown-workflow.md`
- `playbook-discipline.md`
- `quality-learning.md`
- `role-standard.md`
- `route-invariants.md`
- `route-sufficiency.md`
- `runtime-contract.md`
- `style-guide.md`

## Output

Return pass/fail per check and list exact failing file paths.
