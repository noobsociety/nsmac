# (collab seal verification)

Commit the integrity seal on a completed reviewer-backed execution pass, or record the reviewer assessment after the seal exists.

## Trigger

**Dispatch:** `(collab seal verification [--outcome <outcome>] [--restore-target <target>] [--restore-reason <reason>] [--evidence <json>] [--failure-category <category>])` - routing-only command form; not a shell command. No outcome flag writes the seal; an outcome flag records the assessment verdict.
**Search phrases:** collab seal, verification seal, reviewer seal, seal-write, record-verdict, assessment verdict

## Steps

**Seal-write** (no `--outcome`):

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. If `activePhase` is not `Completion`, **ABORT**: `(collab seal verification)` is valid only in the `Completion` phase.
5. Call `commands/collab/engine/registry.py seal-state <target> <role>` and capture `registryRevision`, `verificationSubState`, and `verificationRounds`.
6. If `verificationSubState` is not `verification`, **ABORT**: seal-write requires `Completion.verification` to be active. If the sub-state is `assessment`, a seal already exists; record the verdict instead.
7. If the reviewer role is absent from `participants`, **ABORT**: reviewer role is not a registered participant; run `(collab join --role <reviewerRole>)` first.
8. If `verificationRounds` is zero, **ABORT**: zero verification rounds; at least one participant-verification pass must complete before sealing.
9. Resolve the sealing participant from the current agent's joined role. If the role does not match `reviewerRole`, **ABORT**: seal must be authored by the reviewer role.
10. Confirm every `execution.<role>.touchedPaths` path is committed in `HEAD`. Working-tree-only paths, staged-only paths, deleted-only-in-working-tree paths, or touched paths with unstaged content cannot be sealed.
11. Call `commands/collab/engine/registry.py seal-write <target> <role> --observed-revision <registryRevision>`. The helper writes `verificationSeal`, appends a Completion history line, transitions `verification.subState` to `assessment`, writes the seal-verdict companion, and persists the registry/transcript atomically.
12. Display the helper's `NEXT:` guidance. Stop.

**Record-verdict** (`--outcome <outcome>`):

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the helper fresh (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. If `activePhase` is not `Completion`, **ABORT**: `(collab seal verification)` is valid only in the `Completion` phase.
5. Call `commands/collab/engine/registry.py seal-state <target> <role>` and capture `registryRevision`, `verificationSubState`, and `verificationRounds`.
6. If `verificationSubState` is not `assessment`, **ABORT**: record-verdict requires an existing seal in assessment state.
7. If `verificationRounds` is zero, **ABORT**: zero verification rounds; a verdict cannot assess an unearned seal.
8. Resolve the verdict author from the current agent's joined role. If the role does not match `reviewerRole`, **ABORT**: verdict must be authored by the reviewer role.
9. If `--outcome success` is present, ask whether any durable rationale in the current transcript (Audit-block content, reviewer findings, seal-trust caveats, or qualifications) belongs in committed source. If yes, promote it now into the relevant route doc, reference doc, or invariant file before recording the success verdict. If promotion is out of scope, file a concrete backlog row naming the slug, file, and exact location before recording the success verdict. If no source-worthy rationale is found, state that explicitly and continue.
10. Call `commands/collab/engine/registry.py record-verdict <target> <role> --observed-revision <registryRevision> --outcome <outcome> [--restore-target <target>] [--restore-reason <reason>] [--evidence <json>] [--failure-category <category>]`. The helper records the assessment verdict and auto-closes on `outcome == success`.
11. Display the helper's `NEXT:` guidance. Stop.

## Notes

- **Seal-write vs. record-verdict:** Seal-write records implementation integrity. Record-verdict records the reviewer assessment. They are separate lifecycle operations and do not compose in one invocation.
- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `seal verification`; when absent, resolved per **Registry targeting**. `--outcome <outcome>` is required for record-verdict mode and must be one of `success`, `incomplete`, or `failed`. `--restore-target`, `--restore-reason`, `--evidence`, and `--failure-category` supply structured reviewer findings for non-success verdicts.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent, per [route-invariants.md](../../../platform/standards/route-invariants.md).
- **Reviewer-only:** Only the `reviewerRole` participant may author a seal or verdict.
- **Git-tracking gate:** `seal-write` inspects each execution `touchedPath` against git's committed `HEAD` state, index, and unstaged diff. Committed paths and committed deletions pass. Working-tree-only paths, staged paths, and touched paths with unstaged content fail with `SEAL-GIT-STATE: implementation not in git`.
- **Content-integrity gate:** At seal-write time and on every `success` verdict, helpers recompute the scope digest from `HEAD`. If it differs from `verificationSeal.contentDigest`, the seal becomes stale with `staleReason: "content-drift"` and a success verdict fails with `SEAL-CONTENT-DRIFT`.
- **Zero-round rule:** A seal over zero `verificationRounds` is a hard abort. The round is recorded when the last assigned participant verification completes; `participant_verify_render` increments the count atomically at the all-participants-completed transition.
- **Participant verification gate:** Reviewer-backed collabs always use participant verification before the reviewer seal. If any assigned `verification.participants[role].stage` is not `"completed"`, `seal-write` rejects and names the next participant role.
- **Seal object:** `verificationSeal = { observedRevision, executionEntries, validationScopes, touchedPaths, contentDigest, pathDigests, sealedAt, sealedBy, executionSignature, fullBodySignature, stale }`. Written atomically by `seal-write`; stale-seal triggers may later mark it stale.
- **Stale-write guard:** `seal-write` and `record-verdict` require `--observed-revision <registryRevision>` from the immediately preceding `seal-state` call.
- **Auto-close after seal:** Reviewer-backed collabs close only after all execution entries are complete, a current non-stale seal exists, and a success verdict is recorded.
- **Promotion mechanism:** The promotion check in the `--outcome success` path protects durable rationale on the success seal path. It is not a per-collab `charteredDeliverables` requirement; it is a final qualitative check for rationale that should live in committed source before the collab closes.
- **Reviewer findings block:** On `incomplete` or `failed`, `record-verdict` appends an immutable Reviewer findings block to the transcript audit log and prompts the restore route. Reopen clears the structured `verdict` object but does not remove the findings block.
- <a id="restore-route-recovery"></a>**restore-route-recovery:** After a non-success verdict, run `(collab show verdict)`, then `(collab reopen action-plan)` or `(collab reopen handoff)` according to `restoreTarget`. Revise the reopened phase content, run `(collab run plan)`, rerun participant verification, run `(collab seal verification)`, and record a new verdict.
- **Post-state resume signal:** After either mode completes, re-establish context with `commands/collab/engine/registry.py seal-state --resume <target> <role>` after any `/compact`, agent swap, or subagent return.
- **Effort matrix:** This route's reviewer turn is `xhigh` and is a mandatory-declaration turn. See [agent-effort.md](../../../commands/collab/reference/agent-effort.md).

```route-arg
dispatch: (collab seal verification [--outcome <outcome>] [--restore-target <target>] [--restore-reason <reason>] [--evidence <json>] [--failure-category <category>])
param: name=--outcome; required=optional; placeholder=<outcome>; class=literal; values=success | incomplete | failed; default=literal:absent
param: name=--restore-target; required=optional; placeholder=<target>; class=dynamic; rule=registered phase name; one of action-plan or handoff; default=literal:absent
param: name=--restore-reason; required=optional; placeholder=<reason>; class=dynamic; rule=causal justification; required when outcome is incomplete or failed; default=literal:absent
param: name=--evidence; required=optional; placeholder=<json>; class=dynamic; rule=JSON object of read-only anchors (transcript ids, revision, committed paths, entry ids); default=literal:absent
param: name=--failure-category; required=optional; placeholder=<category>; class=dynamic; rule=causal label; optional; default=literal:absent
```
