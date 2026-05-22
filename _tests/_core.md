# QA — command _core canon

Deterministic QA for `~/.cursor/_core/*.md` canon documents.

## Procedure

1. Load every `*.md` under `~/.cursor/_core/`.
2. Validate the roster is exact.
3. Validate each file has one H1 and is <= 250 lines.
4. Validate links in `_core/` stay self-contained (sibling `_core/*.md` links only).
5. Validate no `_core` file depends on `commands/`, `_functions/`, core policy, core policy, `_tests/`, or host runtime paths.
6. Validate owner consistency: style, document templates, command contract, context model, and voice guide do not conflict.
7. Validate `route-invariant.md` declares the four floor rules and that `tools/check-collab-floor-rules.py` covers the `/collab init`, `/collab join`, `/collab speak`, `/collab rewrite speak`, `/collab advance`, and `/collab restore` pilot routes for helper-owned mutations, stop conditions, resume signals, and declared link targets.
8. Validate `route-sufficiency.md` declares `## Mechanical sufficiency` and `## Execution sufficiency`, includes the self-application statement, and marks execution sufficiency as fixture-backed rather than lintable.

## Required roster

- `agent-role.md`
- `author-voice.md`
- `command-argument.md`
- `command-convention.md`
- `command-standard.md`
- `context-management.md`
- `document-standard.md`
- `flag-taxonomy.md`
- `framework-boundaries.md`
- `helper-subcommands.md`
- `route-invariant.md`
- `route-sufficiency.md`
- `style-guide.md`

## Output

Return pass/fail per check and list exact failing file paths.
