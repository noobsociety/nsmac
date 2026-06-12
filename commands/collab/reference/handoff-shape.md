# Structured Handoff deliverable shape

This document specifies the structured Handoff schema for contributions appended by `(collab speak)` in the `Handoff` phase. Structured Handoff state is registry-owned; the transcript `## Handoff` section is a helper-rendered mirror.

**Architectural grounding:**
- **Invariant #2 (registry as source of truth; transcript as human ledger):** Registry is the authoritative source for command state, including Handoff deliverable data. The transcript `## Handoff` section mirrors selected registry fields; it is generated from registry state and must not be hand-edited.
- **Invariant #6 (subagent write-scope disjointness):** `writeScope` closes the enforcement gap Invariant #6 names — parent agents must not translate Handoff prose into scope. `execute-spawn` consumes `writeScope` directly once structured state exists.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** handoff shape, handoff deliverable, writeScope, validationCommands, structured handoff

## Steps

1. Read this document when authoring a Handoff contribution, implementing Handoff helper support, or evaluating a returned Completion patch.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

**Field set**

A Handoff contribution declares two fields:

| Field | Type | Description |
|---|---|---|
| `writeScope` | array of glob strings | Allowed-path globs for Completion execution; consumed by `execute-spawn --scope` and `execution --touched-path`. |
| `validationCommands` | array of argv arrays | Bounded commands to run after Completion; each entry is an argv array, not a shell string. |

**writeScope**

Each entry is a glob string matching one or more repository paths. Entries must be as narrow as the intended Completion work; over-broad globs are rejected. `run-plan` passes declared `writeScope` to `execute-spawn`; parent agents must not translate Handoff prose into scope. When structured Handoff state exists for a role, the execution recorder also rejects any `--touched-path` outside that role's declared `writeScope`.

**validationCommands format and trust boundary**

Each entry is an argv array: `["./platform/tooling/audit.sh"]`, `["./tests/run.sh"]`, or `["./some-test.sh", "--flag"]`. Complex validation logic lives in repo-source scripts; `validationCommands` invokes those scripts. Registry content carries bounded invocations only; the scripts carry the logic and are subject to normal code review.

Rejection message format: `ABORT: validationCommands contains disallowed pattern: <value>`. The exact rejected value is named. Rejection triggers: shell metacharacters, shell-string form (instead of argv array), unsafe or absolute paths, empty command arrays, and overlong entries.

**Mirror-render idempotency**

The transcript `## Handoff` section is generated from registry state. Repeated renders of the same registry state must produce byte-identical output. Hand-editing the Handoff section is prohibited; the helper overwrites it on next render.

**Failure recovery**

When `execute-spawn` rejects a returned Completion patch or the execution recorder rejects a touched path outside declared `writeScope`, do not widen scope ad hoc. Two recovery paths:

1. **Re-Handoff:** the assigned role issues a revised Handoff via `(collab speak)` in a new or restored Handoff phase.
2. **`(collab rewrite execution)`:** when the patch is otherwise valid and scope widening is the only issue, use `(collab rewrite execution)` to revise the execution record.

**Reopen and narrowed scope**

Reopen saves current coverage before clearing execution state. If your scope narrows on a reopen, you don't need to re-add prior paths to `writeScope`; the saved snapshot already covers them. `writeScope` is about write permissions, not what counts as covered at seal — seal coverage comes from the snapshot. On registries that predate this feature, re-declare all paths or the seal will fail with CHARTERED-DELIVERABLE-MISSING.

**Grandfather policy**

Existing closed collabs are not migrated. `writeScope` and `validationCommands` are required only for Handoff contributions appended after this schema is implemented.

**See also**

- [`invariants.md`](invariants.md) — Invariant #2 (registry/mirror model) and Invariant #6 (write-scope disjointness)
- [`commands/collab/speak/index.md`](../speak/index.md) — Handoff phase speak rules and one-speak constraint
- [`run-plan.md`](../run-plan/index.md) — Handoff dependency parsing and `execute-spawn` scope consumption
