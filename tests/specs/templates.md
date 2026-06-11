# QA — command templates

Deterministic QA for scaffold template sources projected to `~/.cursor/platform/templates/`.

## Procedure

1. Load every `*.md` under the tracked source directory `platform/templates/`.
2. Validate the source roster is exact.
3. Validate each template file has one H1 and is <= 250 lines.
4. Validate `CLAUDE.md` is routing-only and points to `AGENTS.md`.
5. Validate `AGENTS.md` references `~/.cursor/commands/commands.md` and `REPOSITORY.md`.
6. Validate `AGENTS.md` contains `<!-- TODO(install): ... -->` placeholders for install-time scaffold authoring and `REPOSITORY.md` contains `<!-- TODO(patch): ... -->` placeholders for repo-specific authoring.
7. Validate `GEMINI.md` is routing-only, points to `AGENTS.md`, and carries the runtime `dp` projector definition pointer.

## Required roster

Tracked scaffold template files under `platform/templates/`:

- `CLAUDE.md`
- `AGENTS.md`
- `GEMINI.md`
- `REPOSITORY.md`

## Output

Return pass/fail per check and list exact failing file paths.
