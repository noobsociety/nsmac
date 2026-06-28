# Completion.verification — verification semantics reference

Standalone reference for `Completion.verification` sub-state semantics. Loaded by `show-policy.md`, `seal-verification.md`, and any contributor needing a non-route description of the reviewer verification loop.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab verification semantics, Completion.verification, verification round, seal object, stale seal, cap exit, assessment flags, verdict outcome, restoreTarget, restoreReason, evidence, failureCategory, nullResult

## Sub-states

Verification runs in two stages. Each participant completes one full turn against their own write scope; then the reviewer assesses the collab-level outcome against goal, files, and transcript.

`Completion` splits into two ordered sub-states for reviewer-backed collabs:

| Sub-state | Description |
|-----------|-------------|
| `Completion.execution` | `(collab run plan)` execution for all assigned roles, resulting in `execution.<role>` registry entries. |
| `Completion.verification` | Assigned participants run `(collab participant verify)` (if configured); reviewer then issues `(collab seal verification)` and evaluates whether discussion goals were met. |

Execution precedes verification. Close is blocked until a current non-stale `verificationSeal` exists and the reviewer has emitted a `verdict` with `outcome == success`.

## verification.subState

Within `Completion.verification`, three ordered sub-states apply for reviewer-backed collabs:

| Sub-state | Description |
|-----------|-------------|
| `verification.participant` | Assigned participants run `(collab participant verify)`; per-role three-turn sequence (audit → remediation → final-audit). Precedes `verification.seal`. |
| `verification.seal` | Reviewer issues `(collab seal verification)`; mechanical execution-truth check. Existing seal contract unchanged. |
| `verification.assessment` | Reviewer evaluates whether discussion goals were met and emits a `verdict`. |

`verification.participant` precedes `verification.seal`, which precedes `verification.assessment`. Assessment opens after a successful seal. Assessment also re-opens when the seal becomes stale or a cap-exit is recorded, which invalidates the prior seal. Assessment is budget-exempt when a cap-exit trigger opened it.

On a clean first pass, `seal-render` transitions to `verification.assessment`; the reviewer emits `--outcome success`, and the collab auto-closes with an auto-summary.

### Per-role stage: `verification.participants[role].stage`

Within `verification.participant`, each assigned role's progress is tracked independently under `verification.participants[role].stage`:

| Stage | Description |
|-------|-------------|
| `audit` | Turn 1 is active; the role's executed writeScope is being inspected. |
| `remediation` | Turn 2 is active; findings from audit are being resolved. |
| `final-audit` | Turn 3 is active; the scope is being re-inspected against Turn 1 criteria. |
| `completed` | All three turns passed; this role's participant verification is done. |
| `failed` | Final-audit found unresolved issues; the sequence ended with failures. |

`verification.participants[role].stage` is absent when participant verification is not configured or the role has not yet begun its sequence. `verification.subState` remains `"participant"` across all roles during this sub-state; per-turn labels are stored per-role, not as additional global sub-state transitions.

### Assessment verdict

The reviewer emits a verdict during `verification.assessment`:

```
verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }
```

- `outcome`: `success | incomplete | failed`. The reviewer determines this autonomously from execution evidence; soliciting the value from the moderator or user is not permitted. On `success`, helper closes and summarizes. On `incomplete` or `failed`, the helper emits the restore command as a `NEXT:` advisory; moderator runs `(collab reopen <restoreTarget>)` to perform the full phase reset. The helper does not auto-execute the restore.
- `evidence`: read-only anchors only — transcript ids, registry revision, committed paths, execution entry ids. The reviewer does not write implementation steps, command output, or replacement content.
- `restoreTarget`: required when `outcome != success`; must be ≤ current phase in lifecycle order; restricted to registered phases with route support.
- `restoreReason`: required when `outcome != success`; explains the causal determination.
- `failureCategory`: optional causal label; does not require writing remediation.

Assessment must emit even when no actionable cause is identifiable: `nullResult: true` with a one-line justification. Silent non-emission is not permitted.

> **Drift (collab #8):** Authorship-bias disclosure (§4.7, verificationSeal.observedRevision 251, verdict revision 253) — see the commit introducing this note.

> **Drift (collab #10):** `assessment_next_line` (was at `registry.py:4097–4101`) previously emitted `NEXT: Moderator should run (collab set active-phase {target} --force).` for non-success verdicts — the wrong primitive. The document reflects the corrected target behavior (`(collab reopen <restoreTarget>)`); the implementation fix landed in collab #10's platform-engineer scope.

## Round definition

A verification round is a paired-event unit. The round is recorded when the last participant verification completes. `participant_verify_render` increments the count atomically at the all-participants-completed transition; `pairedExecutionSignature` guards against double-increment on single-client retry — if `participant_verify_render` is retried after a transient registry write failure, the signature match prevents a second increment. `seal_render` checks that `verificationRounds > 0` as defense-in-depth only; it does not increment the count. The count is not derived from transcript parsing; `seal_state` exposes the current value as a non-mutating projection.

**Zero-round rule:** A seal over zero verification rounds is a hard ABORT. At least one complete reviewer-executor paired event must be recorded before the seal is accepted. There is no advisory or warning path for the zero-round case.

## Seal object

`verificationSeal` is written atomically to the registry by `seal-render`:

```
verificationSeal = {
  observedRevision: integer,
  executionEntries: object[],
  validationScopes: string[],
  touchedPaths:    string[],
  contentDigest:   string,
  pathDigests:     { "<path>": { mode: string, blob: string } },
  sealedAt:        ISO-8601,
  sealedBy:        string
}
```

The `observedRevision` binds the seal to the registry state at seal time. Any subsequent change to the fields covered by the seal triggers staleness.

## Stale-seal triggers

Each trigger is helper-enforced with a paired shell test asserting invalidation:

| Trigger | Mechanism |
|---------|-----------|
| Execution rewrite via `(collab rewrite execution)` | `rewrite-execution` helper path invalidates seal |
| Transcript repair touching Completion execution evidence | Repair helper path invalidates seal |
| Out-of-scope patch applied outside declared `writeScope` | `execute-spawn` rejection or explicit helper hook |
| Content drift (recomputed scope digest ≠ `verificationSeal.contentDigest`) | `invalidate_verification_seal` content-drift path |

A stale seal blocks close. The seal must be re-issued after any stale trigger fires.

## Cap and cap-exit options

A round cap is set at collab initialization (default: 3). When the cap fires, the reviewer must choose one registered cap-exit action recorded on the seal; no further rounds are accepted after a cap exit is recorded.

The participant-verification attempt budget is bound to the active Handoff `writeScope` hash. A reopen via `reopen-handoff` that introduces a different `writeScope` signature opens a new attempt budget for participant verification. A reopen that preserves the same `writeScope` signature consumes budget against the same counter.

| Cap-exit action | Effect |
|-----------------|--------|
| `reopen-action-plan` | Transitions the collab to `Action Plan` phase |
| `reopen-handoff` | Transitions the collab to `Handoff` phase |
| `archive` | Closes with an accepted-risk summary for unresolved findings |
| `follow-up-collab` | Ends the verification loop and opens a new linked collab for unresolved findings; `seal-render` emits structured `NEXT:` guidance with `restoreReason`, open `evidence` anchors, and `failureCategory`. |

The cap-exit action is passed to `seal-render` as `--cap-exit <action>`. The reviewer may also declare a cap exit before the cap fires when they choose to end the loop early. `--cap-exit archive` requires unresolved findings; using it when participant verification passed cleanly is a protocol violation.

## writeScope reopen advisory

When the reviewer discovers during `Completion.verification` that required fixes are outside the executed `writeScope`, the only registered exit is `(collab seal verification) --cap-exit reopen-handoff`. This transition reopens `Handoff` for a revised scope declaration; informal scope widening is not permitted.

The boundary source is `handoff.roles.<role>.writeScope` in the registry.

## Reviewer obligation

Only the `reviewerRole` participant may author the seal. Non-reviewer roles must not issue `(collab seal verification)`. The reviewer's terminal obligation for reviewer-backed collabs is issuing the seal; the reviewer does not run the full test suite as part of verification.

## Auto-close

For reviewer-backed collabs, auto-close from `(collab run plan)` alone is removed. Close fires only when all assigned `execution.<role>` entries are `completed` AND a current non-stale `verificationSeal` exists. Both conditions must hold simultaneously.

## Time-of-close attestation

The seal model governs two distinct time domains:

**Seal time (open records):** Content-integrity is enforced when `seal-render` runs. The scope digest and `pathDigests` map are recomputed from `HEAD` and must equal the stored seal values; committed deletions are represented as deletion tombstones in `pathDigests`. The declared scope must also be fully committed at `HEAD`. The exact mechanics are defined in the [Content-integrity gate](../seal-verification/index.md#content-integrity-gate) note in `(collab seal verification)`.

**Post-close exemption:** `closed` and `archived` records are not re-validated after close. History rewrites (amend, rebase, squash) that preserve the content of touched paths do not affect the sealed digest and are expected artifacts in immutable records — not live defects. The state at seal time is the authoritative attestation.

For remediation guidance when `workRepo` binding or reachability issues surface during execution or seal, see [`workRepo-remediation-index.md`](workRepo-remediation-index.md).

## Operator guidance: participant verify inactive

When `(collab participant verify)` reports that verification cannot run, the active sub-state determines the correct next action. The message is emitted by `participant_verification_inactive_message` in `commands/collab/engine/seal_verification.py`; the branch logic lives there while the operator guidance text lives here, so the guidance prose is authored once rather than duplicated in code. The `platform/tooling/audit-vocabulary.sh` gate enforces that the engine's `verification.md#…` anchor resolves to a real heading, so the runtime pointer cannot silently dangle.

| Condition | Reason | Correct action |
|-----------|--------|----------------|
| Participant verification is not enabled for this collab | Verification was not configured at `init` time. | The reviewer (`pa`) seals directly via `(collab seal verification)`. |
| Sub-state is `seal` | This verification round's participant passes are already complete. | The reviewer seals via `(collab seal verification)`. |
| Sub-state is `assessment` | A seal is recorded and awaiting the reviewer verdict. | The reviewer records verdict via `(collab seal verification) --outcome <success\|incomplete\|failed>`. To redo verification after a correction, record a non-success outcome; the moderator then runs `(collab reopen <action-plan\|handoff>)` to re-execute and re-verify. |

Any other inactive sub-state is an unexpected state; surface the raw sub-state value and re-run `(collab show policy)` to diagnose.

## Participant verification stage reset

When `(collab reopen)` resets participant verification, `reset_participant_verification_stages` clears per-role stage progress so the round can restart cleanly. Without this clear, `sync_participant_verification_review_substate` would see stale `completed` stages and immediately bounce `subState` back to `seal`, leaving the record neither sealable (rounds 0) nor re-verifiable (stages done).

**Scope-aware partial reset.** With `scope_aware=True` (a reopen that may revise only some roles' scope), a role whose declared write scope and execution signature are unchanged keeps its completed verification. Only the roles the reviewer actually re-scoped must re-run; a reopen no longer forces every participant through a fresh audit round.

**Design invariant — `rounds == 0` / all-stages-completed is intentionally not sealable.** If scope-aware preservation would retain every role's completed stage, no participant would re-run and the round could never be re-earned. The implementation guards against this by falling back to a full reset whenever no role would otherwise be cleared, guaranteeing at least one re-run earns the new round. A `rounds == 0` record with all stages showing `completed` is therefore intentionally not sealable — the guard prevents a no-re-run shortcut from bypassing the round counter.

## Related routes

- [`participant-verify.md`](../participant-verify/index.md) — invocable route spec for `(collab participant verify)`
- [`seal-verification.md`](../seal-verification/index.md) — invocable route spec for `(collab seal verification)`
- [`registry.md`](registry.md) — `verificationSeal` field schema and `completion.subState` field ownership
- [`show-policy.md`](../show-policy/index.md) — gate policy and phase-presence overview
- [`agent-effort.md`](agent-effort.md) — effort matrix row for `Completion.verification`
- [`show-verdict.md`](../show-verdict/index.md) — forthcoming route for verdict introspection over closed-collab metadata; surfaces `outcome`, `restoreTarget`, `evidence`, `failureCategory`, and `nullResult` without requiring direct registry JSON access
- [`workRepo-remediation-index.md`](workRepo-remediation-index.md) — durable R1–R7 remediation items for `workRepo` binding and reachability failures
