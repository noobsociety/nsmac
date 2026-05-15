# /collab seal verification

Seal the `Completion.verification` sub-state after a reviewer pass, recording the seal object and triggering close or a cap-exit action.

## Trigger

**Slash:** `/collab seal verification`
**Signature:** `/collab seal verification [--cap-exit <action>]`
**Prose dispatch:** `(collab seal verification [--cap-exit <action>])` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** collab seal, verification seal, reviewer seal, close verification loop, seal-with-cap

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: seal-verification-record-unreadable -->
2. Read `.collabs/registry.json` and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
<!-- abort: seal-verification-record-closed -->
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
<!-- abort: seal-verification-phase-not-completion -->
4. If the registry `activePhase` is not `Completion`, **ABORT**: `/collab seal verification` is valid only in the `Completion` phase.
5. Call `tools/collab/registry.py seal-state <target>` to read the live verification state. Capture `registryRevision`, `verificationSubState`, `verificationRounds`, and `verificationCap` from the output.
<!-- abort: seal-verification-substate-not-verification -->
6. If the reported `verificationSubState` is not `verification`, **ABORT**: `Completion.verification` sub-state is not active; current sub-state: `<verificationSubState>`.
<!-- abort: seal-verification-no-reviewer -->
7. If `reviewerRole` is absent from the registry `participants` list, **ABORT**: reviewer role is not a registered participant; run `/collab join --role <reviewerRole>` first.
<!-- abort: seal-verification-zero-rounds -->
8. If `verificationRounds` is zero, **ABORT**: zero verification rounds; at least one reviewer-executor paired event is required before sealing.
<!-- abort: seal-verification-wrong-role -->
9. Resolve the sealing participant from the current agent's joined role. If the joining role does not match `reviewerRole`, **ABORT**: seal must be authored by the reviewer role; current role: `<role>`; expected: `<reviewerRole>`.
10. If `--cap-exit <action>` is present: validate that `<action>` is one of `reopen-action-plan`, `reopen-handoff`, or `archive`.
<!-- abort: seal-verification-invalid-cap-exit -->
    If invalid, **ABORT**: invalid cap-exit value `<action>`; must be one of: reopen-action-plan, reopen-handoff, archive.
<!-- abort: seal-verification-cap-exceeded -->
11. If `--cap-exit` is absent and `verificationRounds` is at or above `verificationCap`, **ABORT**: round cap reached; reissue with `--cap-exit reopen-action-plan`, `--cap-exit reopen-handoff`, or `--cap-exit archive`.
12. Write the seal by calling `tools/collab/registry.py seal-render <target> <role> --observed-revision <registryRevision> [--cap-exit <action>]`. The helper writes `verificationSeal = { observedRevision, executionEntries, validationScopes, touchedPaths, sealedAt, sealedBy }` atomically to the registry and appends the seal record to the transcript `## Completion` section. If the helper exits non-zero, **ABORT**: seal write failed; name the helper error.
13. Display the `NEXT:` guidance returned by `seal-render`. If a cap-exit action was declared, execute the named registered command after the seal is written. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `seal verification`; when absent, resolved per **Registry targeting** in **Notes**. `--cap-exit <action>` — one of `reopen-action-plan`, `reopen-handoff`, or `archive`; required when the round cap is reached, optional when the reviewer chooses to end the loop before the cap.
- **Registry targeting:** Resolve the target collab from `.collabs/registry.json`, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT** (agent-honor-system): registry target unavailable; name the registry field or token.
- **Reviewer-only:** Only the `reviewerRole` participant may author the seal. Non-reviewer roles must not issue this command.
- **Zero-round rule:** A seal over zero `verificationRounds` is a hard ABORT with no advisory or warning path. At least one complete reviewer-executor paired event must be recorded in `Completion.verification` before the seal is accepted.
- **Round definition:** A round is a paired event unit — one reviewer verification event plus any executor patch events within the same `Completion.verification` cycle. Rounds are registry-countable; the helper increments the count, not transcript parsing.
- **Cap exits:** When the round cap fires, the reviewer must choose one registered action: `reopen-action-plan` (transitions the collab to `Action Plan` phase), `reopen-handoff` (transitions to `Handoff` phase), or `archive` (closes with an accepted-risk summary). The cap-exit action is recorded on `verificationSeal`; no further rounds are accepted after a cap exit is recorded.
- **Seal staleness:** The `verificationSeal` is invalidated when any of the following occur: an execution record is rewritten via `/collab rewrite execution`; a transcript repair touches execution evidence; a patch outside the declared `writeScope` is applied. Each trigger is helper-enforced with a paired shell test asserting invalidation. A stale seal blocks close. See [`_registry.md`](_registry.md) for the `verificationSeal` field schema.
- **Seal object:** `verificationSeal = { observedRevision: integer, executionEntries: object[], validationScopes: string[], touchedPaths: string[], sealedAt: ISO-8601, sealedBy: string }`. Written atomically by `seal-render`; no hand-editing.
- **Stale-write guard:** `seal-render` requires `--observed-revision <registryRevision>` from the immediately preceding `seal-state` call. If the live registry revision differs, the helper aborts and emits `RESUME: tools/collab/registry.py seal-state --resume <target> <role>`.
- **Auto-close after seal:** For reviewer-backed collabs, `seal-render` triggers close when all assigned `execution.<role>` entries are `completed` and a current non-stale `verificationSeal` exists. Auto-close from `/collab run plan` alone is removed for reviewer-backed collabs; the seal is required.
- **Post-state resume signal:** After `/collab seal verification` completes, re-establish context with `tools/collab/registry.py seal-state --resume <target> <role>` after any `/compact`, agent swap, or subagent return before the next command.
- **writeScope reopen advisory:** When the reviewer surfaces out-of-scope work during verification, the legal exit is `/collab reopen handoff` (with `--cap-exit reopen-handoff`). The reviewer must not widen the scope informally; the registered command creates the audit trail. Registry field `handoff.roles.<role>.writeScope` is the reopen boundary source.
- **Effort matrix:** This route's `pa` turn is `xhigh` and is a mandatory-declaration turn. See [`_agent-effort.md`](_agent-effort.md) (`Completion.verification` row).

```cursor-arg
dispatch: (collab seal verification [--cap-exit <action>])
param: name=--cap-exit; required=optional; placeholder=<action>; class=literal; values=reopen-action-plan | reopen-handoff | archive
```
