# /collab seal verification

Seal the `Completion.verification` sub-state after a reviewer pass, recording the seal object and triggering close or a cap-exit action.

## Trigger

**Slash:** `/collab seal verification`
**Signature:** `/collab seal verification [--cap-exit <action>] [--outcome <outcome>] [--restore-target <target>] [--restore-reason <reason>] [--evidence <json>] [--failure-category <category>]`
**Prose dispatch:** `(collab seal verification [--cap-exit <action>])` — prose routing hint; not a terminal command.
**Search phrases:** collab seal, verification seal, reviewer seal, close verification loop, seal-with-cap, assessment verdict, verdict flags, --outcome, --restore-target, failureCategory

## Steps

1. Read [invariants.md](../../../core/collab/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: seal-verification-record-unreadable -->
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
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
10. If `--cap-exit <action>` is present: validate that `<action>` is one of `reopen-action-plan`, `reopen-handoff`, `follow-up-collab`, or `archive`.
<!-- abort: seal-verification-invalid-cap-exit -->
    If invalid, **ABORT**: invalid cap-exit value `<action>`; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive.
<!-- abort: seal-verification-cap-exceeded -->
11. If `--cap-exit` is absent and `verificationRounds` is at or above `verificationCap`, **ABORT**: round cap reached; reviewer has not issued a seal event in this round; reissue with `--cap-exit reopen-action-plan`, `--cap-exit reopen-handoff`, `--cap-exit follow-up-collab`, or `--cap-exit archive`.
<!-- abort: seal-verification-uncommitted-paths -->
12. Collect every path listed in `execution.<role>.touchedPaths` across all execution entries. For each path, verify it is staged or committed in git — not working-tree-only. A path present only in the working tree means the implementation has not reached git and cannot be sealed. **ABORT** (agent-honor-system): implementation not in git; list each path that is unstaged and uncommitted.
13. Write the seal by calling `tools/collab/registry.py seal-render <target> <role> --observed-revision <registryRevision> [--cap-exit <action>] [--restore-reason <reason> --evidence <json> --failure-category <category>]`. The helper writes `verificationSeal = { observedRevision, executionEntries, validationScopes, touchedPaths, sealedAt, sealedBy }` atomically to the registry and appends the seal record to the transcript `## Completion` section. If the helper exits non-zero, **ABORT**: seal write failed; name the helper error.
14. Display the `NEXT:` guidance returned by `seal-render`. If a cap-exit action was declared, execute the named registered command after the seal is written. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `seal verification`; when absent, resolved per **Registry targeting** in **Notes**. `--cap-exit <action>` — one of `reopen-action-plan`, `reopen-handoff`, `follow-up-collab`, or `archive`; required when the round cap is reached, optional when the reviewer chooses to end the loop before the cap. With `--cap-exit follow-up-collab`, `--restore-reason <reason>`, `--evidence <json>`, and `--failure-category <category>` are required and are recorded on `verificationSeal.followUp`.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT** (agent-honor-system): registry target unavailable; name the registry field or token.
- **Reviewer-only:** Only the `reviewerRole` participant may author the seal. Non-reviewer roles must not issue this command.
- **Git-tracking gate (agent-honor-system):** Step 12 is agent-enforced; the helper does not currently check git state. Use `git diff --cached --name-only` and `git log --oneline -1 -- <path>` to determine whether a path is staged or committed. A path that appears only in `git diff --name-only` (working tree, unstaged) fails the gate. Sealing over uncommitted work records paths in `verificationSeal.touchedPaths` that do not exist in git history, making the seal unreproducible.
- **Zero-round rule:** A seal over zero `verificationRounds` is a hard ABORT with no advisory or warning path. At least one complete reviewer-executor paired event must be recorded in `Completion.verification` before the seal is accepted.
- **Round definition:** A round is a paired event unit. The round is recorded when the last participant verification completes. `participant_verify_render` increments the count atomically at the all-participants-completed transition; `pairedExecutionSignature` guards against double-increment on single-client retry. `seal_render` checks that `verificationRounds > 0` as defense-in-depth only; it does not increment the count. `seal_state` reads the committed value without incrementing.
- **Participant verification gate:** If participant verification is enabled and any assigned `verification.participants[role].stage` value is not `"completed"`, `seal-render` rejects the seal and names the next participant role. This gate is independent of `verification.subState` so a stale or manually drifted `"seal"` sub-state cannot bypass incomplete participant verification.
- **Cap exits:** When the round cap fires, the reviewer must choose one registered action: `reopen-action-plan` (transitions the collab to `Action Plan` phase), `reopen-handoff` (transitions to `Handoff` phase), `follow-up-collab` (keeps the record in assessment and emits structured `NEXT:` guidance to open a follow-up collab with `restoreReason`, evidence anchors, and `failureCategory`), or `archive` (closes with an accepted-risk summary for unresolved findings). The cap-exit action is recorded on `verificationSeal`; `follow-up-collab` also records `verificationSeal.followUp`; no further rounds are accepted after a cap exit is recorded. `--cap-exit archive` is reserved for scenarios where unresolved findings remain at the cap; using it when participant verification passed cleanly (no findings) is a protocol violation and triggers the rollback condition in `invariants.md`.
- **Seal staleness:** The `verificationSeal` is invalidated when any of the following occur: an execution record is rewritten via `/collab rewrite execution`; a transcript repair touches execution evidence; a patch outside the declared `writeScope` is applied. Each trigger is helper-enforced with a paired shell test asserting invalidation. A stale seal blocks close. See [`registry.md`](../../../core/collab/registry.md) for the `verificationSeal` field schema.
- **Seal object:** `verificationSeal = { observedRevision: integer, executionEntries: object[], validationScopes: string[], touchedPaths: string[], sealedAt: ISO-8601, sealedBy: string, followUp?: { restoreReason: string, evidence: object, failureCategory: string } }`. Written atomically by `seal-render`; no hand-editing.
- **Stale-write guard:** `seal-render` requires `--observed-revision <registryRevision>` from the immediately preceding `seal-state` call. If the live registry revision differs, the helper aborts and emits `RESUME: tools/collab/registry.py seal-state --resume <target> <role>`.
- **Auto-close after seal:** For reviewer-backed collabs, `seal-render` triggers close when all assigned `execution.<role>` entries are `completed` and a current non-stale `verificationSeal` exists. Auto-close from `/collab run plan` alone is removed for reviewer-backed collabs; the seal is required.
- **Post-seal assessment:** After a successful seal, `Completion.verification` transitions to `verification.assessment`. The reviewer evaluates whether discussion goals were met and emits a `verdict: { outcome, restoreTarget?, restoreReason?, evidence?, failureCategory? }`. The reviewer must determine `outcome` autonomously from execution evidence; soliciting the outcome from the moderator or user is not permitted. Assessment also re-opens when the seal becomes stale or a cap-exit is recorded. On `outcome == success`, the helper may close and summarize. On `incomplete` or `failed`, the assessment write atomically appends the **Reviewer findings block** (see below) to the audit log and prompts the next responsible role and exact command without auto-executing; the moderator confirms the restore route. Assessment must emit even when no actionable cause is identifiable (`nullResult: true` with a one-line justification); silent non-emission is not permitted.
- <a name="reviewer-findings-block"></a>**Reviewer findings block:** On a non-success outcome (`incomplete` or `failed`), the assessment helper appends an immutable `Reviewer findings` block to the audit log atomically with the verdict write. Reopen clears the structured `verdict` object in registry state but does not rewrite the audit log; the block survives. For `success` outcome, no block is emitted. Block shape:

  ```
  <a name="reviewer-findings-N"></a>
  <details>
  <summary>pa · reopen brief (<outcome>, <failureCategory>)</summary>

  restoreReason: <one-line>
  restoreTarget: <action-plan | handoff>
  failureCategory: <category>
  evidence:
    registryRevision: <int>
    committedPaths: [...]
    executionEntryIds: [...]
    transcriptIds: [...]
  NEXT: Run /collab reopen <restoreTarget> — <summary>.

  </details>
  ```

  **Derived fields:** `NEXT:` and the command packet (reopen command, role prompt, reason summary) are derived from `restoreTarget` and the verdict object fields at write time; the reviewer does not author them. The `NEXT:` line in the block is the in-transcript, human-readable counterpart to the machine-advisory `NEXT:` line emitted by the helper after the write; both are derived from the same verdict fields but serve different consumers and must not be collapsed.

  **Anchor rule:** anchor id is `reviewer-findings-N` where `N` is the count of prior findings blocks in this transcript plus one. The block appears immediately after the verdict marker line and before the next phase header.

  **Drift detection:** `grep -nP '^restoreReason:' ~/.collabs/*/records/*.md` enumerates emitted blocks. A non-success verdict that emits no block, or a reopen that removes a block, is a regression. See `invariants.md` Invariant #12 for the routing-vs-rationale classification that motivates this design.

- <a name="restore-route-recovery"></a>**Restore-route recovery:** After an `incomplete` or `failed` verdict, run `/collab show verdict` to inspect `restoreTarget`, `restoreReason`, evidence, and the next command. If `restoreTarget` is `Action Plan`, run `/collab reopen action-plan`; if it is `Handoff`, run `/collab reopen handoff`. Revise the reopened phase content, rerun assigned execution with `/collab run plan`, then reseal with `/collab seal verification`. After any `/compact`, agent swap, or subagent return during this path, re-establish context with `tools/collab/registry.py seal-state --resume <target> <role>` before continuing.
- **Post-state resume signal:** After `/collab seal verification` completes, re-establish context with `tools/collab/registry.py seal-state --resume <target> <role>` after any `/compact`, agent swap, or subagent return before the next command.
- **writeScope reopen advisory:** When the reviewer surfaces out-of-scope work during verification, the legal exit is `/collab seal verification --cap-exit reopen-handoff`. The `seal-render` helper applies the cap-exit and transitions the collab to `Handoff` phase directly; no separate reopen command is needed for this path. The reviewer must not widen the scope informally; the cap-exit creates the audit trail. Registry field `handoff.roles.<role>.writeScope` is the reopen boundary source.
- **Effort matrix:** This route's reviewer turn is `xhigh` and is a mandatory-declaration turn. See [`agent-effort.md`](../../../core/collab/agent-effort.md) (`Completion.verification` row).

```route-arg
dispatch: (collab seal verification [--cap-exit <action>] [--outcome <outcome>] [--restore-target <target>] [--restore-reason <reason>] [--evidence <json>] [--failure-category <category>])
param: name=--cap-exit; required=optional; placeholder=<action>; class=literal; values=reopen-action-plan | reopen-handoff | follow-up-collab | archive; default=literal:absent
param: name=--outcome; required=optional; placeholder=<outcome>; class=literal; values=success | incomplete | failed; default=literal:absent
param: name=--restore-target; required=optional; placeholder=<target>; class=dynamic; rule=registered phase name; one of action-plan or handoff; default=literal:absent
param: name=--restore-reason; required=optional; placeholder=<reason>; class=dynamic; rule=causal justification; required when outcome is incomplete or failed; default=literal:absent
param: name=--evidence; required=optional; placeholder=<json>; class=dynamic; rule=JSON object of read-only anchors (transcript ids, revision, committed paths, entry ids); default=literal:absent
param: name=--failure-category; required=optional; placeholder=<category>; class=dynamic; rule=causal label; optional; default=literal:absent
```
