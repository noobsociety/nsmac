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

- **reviewer assessment** — The second ordered sub-phase of `Completion.verification` (`verification.subState == assessment`): the reviewer evaluates whether discussion goals were met and records a `verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }`. Opens after `verification.seal`; re-opens when the seal becomes stale or a cap-exit is recorded. Budget-exempt when a cap-exit trigger opened it. The reviewer writes verdict fields only (evaluation); all correction work at the restored phase belongs to participants. See [`verification.md`](verification.md) for the verdict field schema and trigger conditions.

- **`route-arg`** — a fenced code block (` ```route-arg `) that declares the dispatch signature and parameter schema for a route command. Each `param:` line names a parameter and declares its `required`, `placeholder`, `class`, `rule`/`values`, and `default` fields. Agents and harnesses use this block to resolve what parameters are accepted and how to populate them.

- **`route-flag`** — a fenced code block (` ```route-flag `) that declares a route flag's eligibility policy. Fields: `flag`, `eligibility` (`eligible` or `ineligible`), `guard-class` (e.g. `hard-abort`, `registry-integrity`), and optionally `ineligibility-reason`. The declaring route owns the policy; eligibility schema and guard-class tables are in [`platform/standards/command-argument.md`](../../../platform/standards/command-argument.md).

- **`route-gate`** — a fenced code block (` ```route-gate `) that declares an interactive confirmation gate embedded in a route step. Fields: `gate-class`, `proceed` (exact token accepted), `abort` (exact token rejected), `operand-format`, `invalid-input` (`re-prompt` or `abort`), and optionally `re-prompt-template`. The gate is inline with the step that embeds it; it is not a separate route.

- **`default=none`** — a `route-arg` param field value meaning the parameter is optional and has no default; absence is the operative default. Distinct from `default=literal:false` (explicit falsy default) and `default=derived:<key>` (computed default). Use in `param:` lines for optional flags and optional positional arguments that have no fallback.

- **`caller-declined`** — the reserved `--agent-id` token for explicit identity opt-out: the harness exposes a usable identity but the caller deliberately chooses not to declare it. Distinct from `unknown`, which is reserved for the harness-inaccessible case only (the harness cannot expose any identity). The helper counts `caller-declined` joins before rejection enforcement; policy on whether to allow or reject it is collab-configuration-owned. See [`agent-id.md`](agent-id.md).

- **Bare-input abort policy** — from `invariants.md` Invariant #1: free-text tokens passed as route arguments (title, label, message, routing-only dispatch token) are literal content and are never work to execute, unless the route explicitly defines an execution phase for that content. A route argument text that looks like a command is still routed as literal content; the execution phase must be explicit in the route's step definitions.

- **chartered deliverables** — an optional list of deliverables declared by the moderator in the Audit block of a collab record (`charteredDeliverables` field in the registry entry). When present, each item must be covered by at least one cited committed path in the execution record before a seal verdict of `success` can be recorded (Invariant #17). When absent, the coverage gate is a no-op (Invariant #19). Cannot be added retroactively by a reviewer finding; scope expansion at seal requires a new `(collab init)`. Related: [Invariant #17](invariants.md), [Invariant #19](invariants.md).

- **item tags** — recognized classification tokens required on every Action Plan checklist item, placed immediately after the role label: `[execute]` (implementation work), `[doc-fix]` (documentation correction), `[verify]` (verification pass), `[precondition]` (prerequisite that must be satisfied before execution), `[verify-precondition]` (verify a precondition is met), `[verify-objective]` (verify an objective was achieved). Items carrying `[defer]` or any unrecognized tag are malformed and rejected at speak-render (Invariant #18). Related: [Invariant #18](invariants.md).

- **context gate** — the hard-stop policy requiring agents to abort when any dependency is unreadable, rather than proceeding with guesses, stubs, or partial code generation. Defined in `platform/standards/context-gate.md`. Applies whenever an agent would create, edit, refactor, or scaffold files; perform code review; or generate commands whose correctness depends on context not fully available. Related: [`platform/standards/context-gate.md`](../../../platform/standards/context-gate.md).

- **platform doctrines** — standing platform rules collected in `platform/data/doctrines.md` that apply across all collabs and implementation work. Distinguished from per-collab decisions: doctrines persist until a future moderator explicitly revises them in a new collab record. The current doctrine is the hard-cutover no-legacy rule: when a name is wrong, remove it at source without retaining legacy aliases or backwards-compatibility shims. Related: [`platform/data/doctrines.md`](../../../platform/data/doctrines.md).

- **source ledger** — the disposition record at `platform/data/source-ledger.md` for retired source carriers and embedded metadata blocks. Rows are added only for active retirement work; completed carrier history is represented by the executable checks that now own the invariant. Validated by `./platform/tooling/check-source-ledger.py --check` as part of `./platform/tooling/audit.sh`. Related: [`platform/data/source-ledger.md`](../../../platform/data/source-ledger.md).

- **terminal** — the `terminal` registry field, set by `--terminal <seal|issue>` at init. Controls how the collab closes: `seal` (default) requires a reviewer seal; `issue` closes when the platform engineer exports issue evidence. Cannot be changed after init. Values: `ALLOWED_TERMINALS` in `registry_constants.py`. See [workflow-models.md](workflow-models.md).

- **workflow model** — how a collab closes, chosen by `--terminal` at init. Two options: seal (default) and issue. Cannot be changed after init. See [workflow-models.md](workflow-models.md).

- **issue terminal** — a collab initialized with `--terminal issue`. Closes when `(collab export-issues)` writes evidence; skips `Completion.verification` and does not need a `verificationSeal`. See [workflow-models.md](workflow-models.md).

**Retired terms:**

- **~~global home~~ (retired 2026-05-16)** — Replaced by [user-scope collab state root](#user-scope-collab-state-root). "Global home" refers informally to `$HOME/.collabs/` as a monolithic location. Retired because it conflates location (`$HOME`) with scope (user-level) and hides the directory's purpose (collab state storage). The replacement term encodes scope, domain, and role, and includes the required `<projectId>` subdir that is the actual per-project unit.
