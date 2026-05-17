# Collab glossary

One canonical term per concept. Use these phrases in route prose, error messages, tests, and docs. Deviations are vocabulary defects.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab glossary, collab vocabulary, project identity terms, user-scope collab state root

## Steps

1. Read this document when choosing terminology for collab route prose, helper output, tests, or source comments.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

**Canonical terms:**

- **project identity** — The concept of binding a repository to a persistent user-scope collab state root. Use in prose that describes the binding relationship or refers to the concept in the abstract. Example: "Resolving a collab starts from the repository's project identity." Related: [project id](#project-id), [`projectId`](#projectid).

- **project id** — The specific opaque identifier value recorded in `projectId`. Use when citing or referencing the runtime value itself. Example: "The project id is `a13dba4ca8714205b217dca31da96eee`." Related: [project identity](#project-identity), [`projectId`](#projectid).

- **`projectId`** — The JSON field key in `.collab.json` that holds the project id value. Always use the backtick-quoted form when referring to the field name in prose or error messages. Do not use `projectId` as a synonym for "project identity" (the concept) or "project id" (the value). Related: [project identity](#project-identity), [project id](#project-id).

- **user-scope collab state root** — The per-project directory at `$HOME/.collabs/<projectId>/`. Contains `registry.json`, `records/*.md`, and `label` for one project identity. Deliberately non-XDG: records are user-browsed, repo-independent operational state. Location encoding: `$HOME/.collabs/` base, `<projectId>` subdir. The helper honors `CURSOR_COLLAB_STATE_HOME` only as an explicit test or emergency recovery base override; default operator guidance stays `$HOME/.collabs/<projectId>/`. Use this term everywhere this directory is described; do not substitute: "state directory", "resolved state directory", "home state root", "collab state root", or "resolved state root path". Related: [project id](#project-id).

- **reviewer assessment** — The second ordered sub-phase of `Completion.verification` (`verification.subState == assessment`): the reviewer evaluates whether discussion goals were met and records a `verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }`. Opens after `verification.seal`; re-opens when the seal becomes stale or a cap-exit is recorded. Budget-exempt when a cap-exit trigger opened it. The reviewer writes verdict fields only (evaluation); all correction work at the restored phase belongs to participants. See [`_verification.md`](_verification.md) for the verdict field schema and trigger conditions.

**Retired terms:**

- **~~global home~~ (retired 2026-05-16)** — Replaced by [user-scope collab state root](#user-scope-collab-state-root). "Global home" refers informally to `$HOME/.collabs/` as a monolithic location. Retired because it conflates location (`$HOME`) with scope (user-level) and hides the directory's purpose (collab state storage). The replacement term encodes scope, domain, and role, and includes the required `<projectId>` subdir that is the actual per-project unit.
