# Completion.verification — Verification semantics reference

Standalone reference for `Completion.verification` sub-state semantics. Loaded by `show-policy.md`, `seal-verification.md`, and any contributor needing a non-route description of the reviewer verification loop.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab verification semantics, Completion.verification, verification round, seal object, stale seal, cap exit

## Sub-states

`Completion` splits into two ordered sub-states for reviewer-backed collabs:

| Sub-state | Description |
|-----------|-------------|
| `Completion.execution` | `/collab run plan` execution for all assigned roles, resulting in `execution.<role>` registry entries. |
| `Completion.verification` | Reviewer passes over executed scope and calls `/collab seal verification` to issue the seal. |

Execution precedes sealing. Close is blocked until a current non-stale `verificationSeal` exists.

## Round definition

A verification round is a paired-event unit: one reviewer event plus any executor patch events within the same `Completion.verification` cycle. Rounds are registry-countable; `tools/collab/registry.py` increments the count on each paired event. The count is not derived from transcript parsing.

**Zero-round rule:** A seal over zero verification rounds is a hard ABORT. At least one complete reviewer-executor paired event must be recorded before the seal is accepted. There is no advisory or warning path for the zero-round case.

## Seal object

`verificationSeal` is written atomically to the registry by `seal-render`:

```
verificationSeal = {
  observedRevision: integer,
  executionEntries: object[],
  validationScopes: string[],
  touchedPaths:    string[],
  sealedAt:        ISO-8601,
  sealedBy:        string
}
```

The `observedRevision` binds the seal to the registry state at seal time. Any subsequent change to the fields covered by the seal triggers staleness.

## Stale-seal triggers

Each trigger is helper-enforced with a paired shell test asserting invalidation:

| Trigger | Mechanism |
|---------|-----------|
| Execution rewrite via `/collab rewrite execution` | `rewrite-execution` helper path invalidates seal |
| Transcript repair touching Completion execution evidence | Repair helper path invalidates seal |
| Out-of-scope patch applied outside declared `writeScope` | `execute-spawn` rejection or explicit helper hook |

A stale seal blocks close. The seal must be re-issued after any stale trigger fires.

## Cap and cap-exit options

A round cap is set at collab initialization (default: 3). When the cap fires, the reviewer must choose one registered cap-exit action recorded on the seal; no further rounds are accepted after a cap exit is recorded.

| Cap-exit action | Effect |
|-----------------|--------|
| `reopen-action-plan` | Transitions the collab to `Action Plan` phase |
| `reopen-handoff` | Transitions the collab to `Handoff` phase |
| `archive` | Closes with an accepted-risk summary |

The cap-exit action is passed to `seal-render` as `--cap-exit <action>`. The reviewer may also declare a cap exit before the cap fires when they choose to end the loop early.

## writeScope reopen advisory

When the reviewer discovers during `Completion.verification` that required fixes are outside the executed `writeScope`, the only registered exit is `/collab seal verification --cap-exit reopen-handoff`. This transition reopens `Handoff` for a revised scope declaration; informal scope widening is not permitted.

The boundary source is `handoff.roles.<role>.writeScope` in the registry.

## Reviewer obligation

Only the `reviewerRole` participant may author the seal. Non-reviewer roles must not issue `/collab seal verification`. The reviewer's terminal obligation for reviewer-backed collabs is issuing the seal; the reviewer does not run the full test suite as part of verification.

## Auto-close

For reviewer-backed collabs, auto-close from `/collab run plan` alone is removed. Close fires only when all assigned `execution.<role>` entries are `completed` AND a current non-stale `verificationSeal` exists. Both conditions must hold simultaneously.

## Related routes

- [`seal-verification.md`](seal-verification.md) — invocable route spec for `/collab seal verification`
- [`_registry.md`](_registry.md) — `verificationSeal` field schema and `completion.subState` field ownership
- [`show-policy.md`](show-policy.md) — gate policy and phase-presence overview
- [`_agent-effort.md`](_agent-effort.md) — effort matrix row for `Completion.verification`
