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

- **user-scope collab state root** — The per-project directory at `$HOME/.collabs/<projectId>/`. Contains `registry.json`, `records/*.md`, and `label` for one project identity. Deliberately non-XDG: records are user-browsed, repo-independent operational state. Location encoding: `$HOME/.collabs/` base, `<projectId>` subdir. The helper honors `COLLAB_STATE_HOME` only as an explicit test or emergency recovery base override; default operator guidance stays `$HOME/.collabs/<projectId>/`. Use this term everywhere this directory is described; do not substitute: "state directory", "resolved state directory", "home state root", "collab state root", or "resolved state root path". Related: [project id](#project-id).

- **reviewer assessment** — The second ordered sub-phase of `Completion.verification` (`verification.subState == assessment`): the reviewer evaluates whether discussion goals were met and records a `verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }`. Opens after `verification.seal`; re-opens when the seal becomes stale or a cap-exit is recorded. Budget-exempt when a cap-exit trigger opened it. The reviewer writes verdict fields only (evaluation); all correction work at the restored phase belongs to participants. See [`_verification.md`](_verification.md) for the verdict field schema and trigger conditions.

- **`route-arg`** — a fenced code block (` ```route-arg `) that declares the dispatch signature and parameter schema for a route command. Each `param:` line names a parameter and declares its `required`, `placeholder`, `class`, `rule`/`values`, and `default` fields. Agents and harnesses use this block to resolve what parameters are accepted and how to populate them.

- **`route-flag`** — a fenced code block (` ```route-flag `) that declares the force-flag eligibility policy for a route. Fields: `flag` (always `force`), `eligibility` (`eligible` or `ineligible`), `guard-class` (e.g. `hard-abort`, `registry-integrity`), and optionally `ineligibility-reason`. The declaring route owns the policy; downstream enforcement follows the guard-class contract.

- **`route-gate`** — a fenced code block (` ```route-gate `) that declares an interactive confirmation gate embedded in a route step. Fields: `gate-class`, `proceed` (exact token accepted), `abort` (exact token rejected), `operand-format`, `invalid-input` (`re-prompt` or `abort`), and optionally `re-prompt-template`. The gate is inline with the step that embeds it; it is not a separate route.

- **`default=none`** — a `route-arg` param field value meaning the parameter is optional and has no default; absence is the operative default. Distinct from `default=literal:false` (explicit falsy default) and `default=derived:<key>` (computed default). Use in `param:` lines for optional flags and optional positional arguments that have no fallback.

- **`caller-declined`** — the reserved `--agent-id` token for explicit identity opt-out: the harness exposes a usable identity but the caller deliberately chooses not to declare it. Distinct from `unknown`, which is reserved for the harness-inaccessible case only (the harness cannot expose any identity). The helper counts `caller-declined` joins before rejection enforcement; policy on whether to allow or reject it is collab-configuration-owned. See [`_agent-id.md`](_agent-id.md).

- **Bare-input abort policy** — from `_invariants.md` Invariant #1: free-text tokens passed as route arguments (title, label, message, routing-only dispatch token) are literal content and are never work to execute, unless the route explicitly defines an execution phase for that content. A route argument text that looks like a command is still routed as literal content; the execution phase must be explicit in the route's step definitions.

**Retired terms:**

- **~~global home~~ (retired 2026-05-16)** — Replaced by [user-scope collab state root](#user-scope-collab-state-root). "Global home" refers informally to `$HOME/.collabs/` as a monolithic location. Retired because it conflates location (`$HOME`) with scope (user-level) and hides the directory's purpose (collab state storage). The replacement term encodes scope, domain, and role, and includes the required `<projectId>` subdir that is the actual per-project unit.
