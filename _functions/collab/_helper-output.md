# Helper output

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab helper output, advisory line ordering, helper exit codes

## Steps

1. Read this document when auditing or changing collab helper output contracts.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Defines the required output lines per collab helper command, advisory line ordering, and exit-code semantics. Authoritative for platform-engineer role audits under item #5.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success or eligible; output is valid and the caller may proceed |
| 1 | Blocked, invalid input, or precondition failed; output names the reason |

Any command that exits non-zero must print a human-readable error message. Silent non-zero exits are a defect.

## Advisory line ordering

Advisory lines follow every successful mutating action. Order is fixed; consumers parse by prefix label, not line index.

| Position | Prefix | Required by |
|---|---|---|
| 1 | `NEXT:` | All mutating commands |
| 2 | `EFFORT:` | All mutating commands |
| 3 | `EFFICIENCY:` | Commands that cross a lifecycle boundary |
| 4 | `IDENTITY:` | `join` only |

`EFFICIENCY:` is suppressed when no lifecycle boundary is crossed in the action. `IDENTITY:` records the `agentId` captured at join time.

Advisory lines are suppressed on failed eligibility checks, duplicate contributions, or any gate failure. The output on failure shows only the blocker.

## Pre-write advisory lines (`speak-render`)

`speak-render` emits two pre-write advisory lines before appending content:

```
BOUNDARY: transcript write only; no shell commands or source edits outside the user-scope collab state root
SUCCINCTLY: stay within role concerns; do not pad or summarize other roles
```

These are not part of the post-write advisory sequence. They appear before any write and before any post-write advisory line.

## Required lines per command

### `join-participants`

Successful exit emits in order:

1. `NEXT: Run /collab show policy before first speak.`
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `IDENTITY: <agentId>`

### `speak-render`

Pre-write (before appending):

1. `BOUNDARY: transcript write only; no shell commands or source edits outside the user-scope collab state root`
2. `SUCCINCTLY: stay within role concerns; do not pad or summarize other roles`
3. `RETRACT: use /collab retract speak to tombstone the latest active-phase contribution`

Post-write (after successful append):

1. `NEXT: <imperative routing guidance>`
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `EFFICIENCY:` (only when action crosses a lifecycle boundary)
4. `appended`
5. `PHASE: <state>` by default, or `{"phaseState": "<state>"}` when `--json` is supplied

### `speak-lifecycle-live`

Emits lifecycle JSON: `{"phaseState": "<value>"}` where `<value>` is a phase name or `unchanged`.

### `speak-state`

Emits JSON object with fields: `activePhase`, `allowedRoles`, `expectedRole`, `contributors`, `lastContributor`, `readyToWrite`, `uncheckedAssignedItemsByRole`.

Exit 0 when the queried role is in `allowedRoles`. Exit 1 otherwise.

### `effort-state`

Emits: `EFFORT: <phase> · <role> · <level> · <scale phrase>`

Exit 0 always.

### `execute-spawn`

Exit 0 when the declared scope does not conflict with sibling scopes. Exit 1 with conflict message naming the overlapping paths.

### `participant-verify-state`

Emits JSON object with fields: `target`, `activePhase`, `registryRevision`, `completionSubState`, `verificationReviewSubState`, `assignedRoles`, `nextRole`, `role`, `roleAgentId`, `roleState`, `readyToVerify`, `freshRegistryRead`. When the role is next, the helper persists `verification.participants[role].stage = "audit"` before emitting the JSON so the following `participant-verify-render` call has a registry-visible active lock. When `--resume` is supplied, also emits `resume`.

Exit 0 on valid input. Exit 1 when the collab is closed, the phase is not `Completion`, participant verification is not the active sub-state, or the role is not assigned.

### `participant-verify-render`

Writes one atomic three-turn participant-verification sequence. Successful exit emits:

1. `participant verification <completed|failed> for <role>`
2. `NEXT: Run /collab participant verify for role <role>.` when another participant remains, otherwise `NEXT: Run /collab seal verification for role <reviewer>.`

Exit 0 on success. Exit 1 when the observed revision is stale, no active participant-verification lock exists for the role, another participant role is next, the attempt cap is reached, or touched paths fall outside the role's declared `writeScope`.

### `seal-state`

Emits JSON object with fields: `target`, `activePhase`, `registryRevision`, `reviewerRole`, `reviewerState`, `verificationSubState`, `completionSubState`, `verificationReviewSubState`, `verificationRounds`, `verificationCap`, `executionEntries`, `validationScopes`, `touchedPaths`, `participantVerification`, `participantVerificationRoles`, `participantVerificationParticipants`, `nextParticipantVerificationRole`, `sealStale`, `verdict`, `freshRegistryRead`. When a `<role>` argument is provided, also emits `roleAgentId`, `readyToSeal`, and `readyToAssess`. When `--resume` is supplied, also emits `resume`.

Exit 0 on valid input. Exit 1 when the collab is closed, the phase is not `Completion`, or the target is unresolvable.

### `seal-render`

Two modes share the subcommand: bare seal (no verdict flags) and assessment verdict (with `--outcome` and optional verdict fields). The modes are mutually exclusive; `--cap-exit` and verdict flags cannot be combined.

**Bare seal path** (no verdict flags; `verificationReviewSubState` must be `seal`):

Post-write advisories in order:

1. `NEXT: Run /collab seal verification for role <role> with --outcome <success|incomplete|failed>.`
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `EFFICIENCY:` (only when action crosses a lifecycle boundary)
4. `<status>` — registry status after the write
5. Phase-transition notice JSON when a cap-exit transitions the phase; assessment-transition notice `{"notice": "assessment", "transition": "Completion.verification.seal->Completion.verification.assessment", "message": "Verification seal recorded; reviewer assessment required."}` when no cap-exit is applied

When `--cap-exit` is provided, the `NEXT:` line reflects the new state after the transition rather than prompting for an assessment verdict. For `--cap-exit follow-up-collab`, it requires `--restore-reason`, `--evidence`, and `--failure-category`, records them on `verificationSeal.followUp`, and emits `NEXT: Open a follow-up collab {"evidence":...,"failureCategory":...,"restoreReason":...}.`

**Assessment verdict path** (with `--outcome`; `verificationReviewSubState` must be `assessment`):

Post-write advisories in order:

1. `NEXT: Moderator should run /collab reopen <phase-token> <target>.` — on `success`, reflects the closed state via `next_line_for_state`; on `incomplete` or `failed`, directs the moderator to run `/collab reopen <phase-token>` where `<phase-token>` is `action-plan` or `handoff` derived from `restoreTarget`.
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `EFFICIENCY:` (only when action crosses a lifecycle boundary)
4. `<status>` — `closed` on `success`; otherwise unchanged
5. Assessment notice JSON: `{"notice": "assessment", "outcome": "<outcome>", "restoreTarget": "<target>", "message": "Assessment verdict recorded; restore target is <target>."}`

### `execution`

Post-write advisories in order:

1. `NEXT: <next role or state guidance>`
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `EFFICIENCY:` (only when action crosses a lifecycle boundary)
4. `<status>` — registry status after the write
5. Terminal notice JSON when auto-close triggers: `{"notice": "clear", "status": "closed", "message": "..."}`

Exit 0 on success. Exit 1 when the collab is closed, the role is not a participant, unchecked assigned Action Plan items remain (for `completed` status), or touched paths fall outside the role's declared `writeScope`.

## Defect definition

A command has a helper-output defect when any of the following is true:

- A required line is absent from successful output
- Advisory lines appear out of the fixed order
- Exit code does not match the semantic table above
- A pre-write advisory line appears after a post-write advisory line
- A suppressed line appears on a failed-gate output
