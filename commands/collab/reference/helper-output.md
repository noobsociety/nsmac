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

### `rewrite-speak-render`

Pre-write checks (before mutating): validates the role-owned contribution block exists, runs the Action Plan shape check when the active phase is `Action Plan`, and evaluates the reviewer-notice gate.

Post-write (after successful rewrite):

1. `REVIEWER-NOTICE: <message>` — when the contribution being rewritten predates the most recent reviewer turn in the same phase
2. `NEXT: <imperative routing guidance>`
3. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
4. `EFFICIENCY:` — only when the action crosses a lifecycle boundary
5. Entry id of the rewritten contribution

Exit 0 on success. Exit 1 when the role-owned contribution block is missing or malformed, the Action Plan shape check fails, or the reviewer gate blocks the rewrite.

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

Writes one atomic three-turn participant-verification sequence. When the last assigned participant completes verification, increments `verification.rounds` by 1. Successful exit emits:

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

### `export-issues`

Post-write advisories in order:

1. `NEXT: <state guidance>`
2. `EFFORT: <phase> · <role> · <level> · <scale phrase>`
3. `EFFICIENCY:` (only when the export closes the record)
4. `<status>` — registry status after the write
5. Terminal close notice JSON when the export closes the record: `{"notice": "clear", "status": "closed", "message": "..."}`

Exit 0 on success. Exit 1 when the collab is closed, the active phase is not `Completion`, the terminal is not `issue`, the caller is not the platform-engineer role, assigned execution remains pending, or the evidence file is unreadable or malformed.

## Abort families

Named abort classes that close spec-to-helper gaps not covered by the per-command required-lines tables above. Each entry names the logical module, the triggering condition, and the exact exit-1 message or protocol constraint.

### Module: `speak-render` / `rewrite-speak-render`

**Full-body envelope rejection**

Fires when the excerpt (`--content-file`) contains a hand-authored `<details>` or `</details>` control line, or when the full-body content (`--full-body-file`) contains a `<details>` or `</details>` control line. The helper owns the full-body envelope; callers must not nest additional control lines.

Exit-1 messages (exact):

- Excerpt: `excerpt must not contain hand-authored <details> blocks; use --full-body-file for Full contribution; line <N>`
- Full body: `full body must not contain hand-authored <details> control lines; the helper owns the Full contribution envelope; line <N>`

**Action Plan shape validation**

Fires when `activePhase == "Action Plan"` and the submitted content has a non-exempt line that does not match the canonical shape, or has no assignment lines after exempt content is stripped. Pre-pass strips HTML comments, blank lines, Markdown headings, and the `EFFORT OVERRIDE:` first line. Abort messages mirror `invariants.md` Invariant #9 and are the shared validator's sole exit path for both `speak-render` and `rewrite-speak-render`.

Exit-1 messages (exact):

- `ABORT: line N does not match Action Plan shape '- [ ] **<role>:** ...' (Invariant #9, invariants.md). Offending line: '<line>'. Example: '- [ ] **tw:** Update the route doc.'`
- `ABORT: Action Plan body contains no assignment lines after exempt content is removed (Invariant #9, invariants.md). Example: '- [ ] **tw:** Update the route doc.'`

### Module: `seal-state`

**Phase and status guards**

Exit-1 messages (exact):

- `record is closed`
- `/collab seal verification is valid only in the Completion phase`

### Module: `seal-render`

**Paired-execution-signature double-increment guard**

`seal-render` tracks a `pairedExecutionSignature` alongside the verification round counter. When a seal attempt occurs without any change to execution state since the previous seal, the guard suppresses the round increment, leaving `rounds` unchanged. If `rounds` remains zero after the guard fires (no execution-state change has ever been paired with a seal), the helper aborts:

Exit-1 message (exact): `zero verification rounds; at least one reviewer-executor paired event is required before sealing`

**`seal-verification-archive-protocol-violation`** *(agent-honor-system)*

`--cap-exit archive` is reserved for scenarios where unresolved findings remain at the cap. Using it when participant verification passed cleanly (no findings) is a protocol violation. The helper does not abort — this constraint is agent-honor-system and route-prose-enforced. Violation triggers the rollback condition in `invariants.md` Invariant #10 (detection remains active).

**Stale revision guard**

Exit-1 message (exact, two lines):

```
stale registry revision: observed <N>, live <M>
RESUME: commands/collab/engine/registry.py seal-state --resume <id> <role>
```

**Role and reviewer guards**

Exit-1 messages (exact):

- `record is closed`
- `/collab seal verification is valid only in the Completion phase`
- `verification seal requires an active reviewer role`
- `reviewer role is not a registered participant; run /collab join --role <reviewer> first`
- `seal must be authored by the reviewer role; current role: <role>; expected: <reviewer>`

**Sub-state guards**

Exit-1 messages (exact):

- `Completion.verification sub-state is not active; current sub-state: <state>`
- `participant verification is active; next role: <pending_role>`
- `verification assessment is active; seal block is immutable; provide --outcome to record a verdict`
- `verification assessment is not active; current verification.subState: <state>`
- `verification assessment cannot mutate seal cap-exit; omit --cap-exit when writing a verdict`

**Execution completeness guard**

Exit-1 message (exact): `verification seal requires all execution entries to be completed`

**Execution content-completeness guard**

Before sealing, `seal-render` verifies that every declared `touchedPath` in
each execution entry resolves to committed content at `HEAD` — either a
committed blob or a committed-deletion tombstone. Staged and unstaged changes
are rejected because they are not part of `HEAD`.

Exit-1 message prefix (exact): `SEAL-CONTENT-INCOMPLETE:`

**Content-drift guard**

On the `success` verdict path, `seal-render` recomputes the scope digest from
`HEAD` and compares it against `verificationSeal.contentDigest`. A mismatch
means the sealed content is no longer what is in the branch.

Exit-1 message prefix (exact): `SEAL-CONTENT-DRIFT:`

**Execution agent-conflation guard**

Before sealing, `seal-render` rejects a verification round where two role
execution entries share the same concrete `agentId`.

Exit-1 message prefix (exact): `PARTICIPANT-VERIFY-AGENT-CONFLATION:`

**Round cap guard**

Exit-1 message (exact): `round cap reached; reissue with --cap-exit reopen-action-plan, --cap-exit reopen-handoff, --cap-exit follow-up-collab, or --cap-exit archive`

**Cap-exit argument guards**

Exit-1 messages (exact):

- `invalid cap-exit value <value>; must be one of: reopen-action-plan, reopen-handoff, follow-up-collab, archive`
- `follow-up-collab cap-exit cannot include assessment outcome fields`
- `follow-up-collab cap-exit requires --restore-reason, --evidence, and --failure-category`
- `cap-exit metadata is only valid with --cap-exit follow-up-collab`

**Assessment verdict guards**

Exit-1 messages (exact):

- `verdict outcome is required when writing assessment fields`
- `assessment verdict requires verificationSeal`
- `success verdict requires current non-stale verificationSeal; stale: <reason>`

### Module: `handoff-shape`

**writeScope and validationCommands disallowed pattern**

All `writeScope` and `validationCommands` shape violations share one exit-1 template produced by `handoff_abort`:

Exit-1 message template (exact): `ABORT: <field> contains disallowed pattern: <value>`

`<field>` is `writeScope` or `validationCommands`; `<value>` is the rejected value rendered as a string or JSON.

**writeScope triggers:**

- Non-string or blank entry
- Entry length > 200 characters
- Absolute path
- Bare `*` or `**`; path starting with `../`, containing `/../`, or ending with `/..`
- Normalized path resolves to empty, `.`, or `..`
- Path component is `''`, `.`, or `..`
- First path component is `*` or `**`
- `writeScope` value is not a list or is empty
- More than 32 entries
- Duplicate entries after normalization
- Missing `writeScope` section: `ABORT: writeScope contains disallowed pattern: missing`

**validationCommands triggers:**

- Non-string or blank argument
- Argument length > 200 characters
- Shell metacharacter in any argument
- Command path does not start with `./`
- Absolute command path
- Traversal sequences `../`, `/../`, `/..` in any argument
- Trivial command path `.` or `./`
- Empty command identifier after `./`
- `validationCommands` value is not a list or is empty
- More than 16 command entries
- More than 16 arguments per command entry
- JSON parse failure for a command or argument entry
- Missing `validationCommands` section: `ABORT: validationCommands contains disallowed pattern: missing`

**Handoff state schema validation**

Fires after parsing when the assembled state object does not conform to the schema:

Exit-1 messages (exact):

- `handoff: handoff state must be an object`
- `handoff: handoff state contains disallowed version field`
- `handoff: handoff body must be a string when present`

### Module: `participant-verify-state`

**Phase and status guards**

Exit-1 messages (exact):

- `record is closed`
- `/collab participant verify requires activePhase = Completion`
- `role must already be a participant: <role>`

**Sub-state, assignment, and turn-lock guards**

Exit-1 messages (exact):

- `participant verification is not the active sub-state; current value: <state>`
- `role is not assigned to participant verification: <role>`
- `participant verification turn lock is held by role <pending_role>`
- `participant verification attempt cap reached for <role>: <attempts>/<cap>`

### Module: `participant-verify-render`

Applies all `participant-verify-state` guards plus the following additional checks.

**Status argument validation**

Exit-1 message (exact): `participant verification status must be one of: completed, failed`

**Stale revision guard**

Exit-1 message (exact, two lines):

```
stale registry revision: observed <N>, live <M>
RESUME: commands/collab/engine/registry.py participant-verify-state --resume <id> <role>
```

**Turn-lock active guard**

Fires when `participant-verify-state` has not been called to acquire the active-stage lock for this role.

Exit-1 message (exact): `participant verification turn lock is not active; run participant-verify-state first for role <role>`

**Touched-path scope guard**

Exit-1 message (exact): `execution touched path outside declared writeScope: <path>`

**Transcript availability guard**

Exit-1 message (exact): `transcript missing: <path>`

### Module: `reopen`

**Phase token validation**

Exit-1 message (exact): `reopen phase must be one of: action-plan, handoff`

**Status and verdict guards**

Exit-1 messages (exact):

- `record is archived`
- `/collab reopen is valid only after a non-success Completion verdict`
- `/collab reopen requires a non-success Completion verdict`
- `/collab reopen phase mismatch: verdict restoreTarget is <target>; expected <expected_token>`

**Transcript availability guard**

Exit-1 message (exact): `transcript missing: <path>`

### Module: `show-verdict`

**Verdict availability guard**

Exit-1 message (exact): `verdict unavailable for target`

### Module: `init` (argument validation)

**Flag parsing guards**

Exit-1 messages (exact):

- `duplicate flag: --agent-id`
- `agent-id is required`
- `duplicate flag: --reviewer`
- `--reviewer requires a role key`
- `duplicate flag: --preview`
- `duplicate flag: --no-participant-verification`
- `unknown flag: <flag>`
- `<name> is required`

**Registry collision guards**

Exit-1 messages (exact):

- `record already exists: <path>`
- `registry collision: <id>`
- `registry collision: <slug>`
- `registry collision: sequence <N>`

### Module: `contribution-budget`

**Spec integrity guards**

Fire when `contribution-budget.md` is missing or malformed; abort `speak-render` and `rewrite-speak-render` before word count is evaluated.

Exit-1 messages (exact):

- `contribution budget spec missing: <path>`
- `contribution budget spec missing word limit: <path>`
- `contribution budget spec missing exempt class: <class_name>`

`<class_name>` is the alphabetically first missing required key among: `action-plan-checklist`, `conclusion-ratification`, `contribution-full-body`, `effort-override-line`, `moderator-verbatim`.

**Word count enforcement**

Fires when the countable excerpt exceeds the configured word limit.

Exit-1 message (exact): `contribution excerpt is <count> words; limit is <limit>; keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file`

### Module: command-default (registry and target resolution)

Shared abort conditions across all commands that read from the registry.

**Registry availability**

Exit-1 messages (exact):

- `registry missing: <path>`
- `registry invalid JSON: <path>: <detail>`

**Target resolution**

Exit-1 messages (exact):

- `registry target not found: <target>`
- `registry activeCollabId is empty`

## Defect definition

A command has a helper-output defect when any of the following is true:

- A required line is absent from successful output
- Advisory lines appear out of the fixed order
- Exit code does not match the semantic table above
- A pre-write advisory line appears after a post-write advisory line
- A suppressed line appears on a failed-gate output

## Module-to-subcommand map

Maps each documented `## Abort families` module family to its implementing subcommand(s) and key function(s). Most functions reside in `registry.py`; rows that resolve to a sibling helper note the containing module in the Key function(s) column. Use this table to audit spec-to-code alignment without running the helper: check that the abort messages listed in each module section match the exit-1 strings in the named functions.

| Module | Subcommand(s) | Key function(s) |
|---|---|---|
| `speak-render` / `rewrite-speak-render` | `speak-render`, `rewrite-speak-render` | `render_speak()`, `render_re_speak()` |
| `seal-state` | `seal-state` | `seal_state()` |
| `seal-render` | `seal-render` | `render_seal()` |
| `handoff-shape` | `speak-render`, `rewrite-speak-render` | `parse_handoff_content()`, `validate_handoff_write_scope()`, `validate_handoff_validation_commands()`, `validate_handoff_state()` |
| `participant-verify-state` | `participant-verify-state` | `participant_verify_state()` |
| `participant-verify-render` | `participant-verify-render` | `participant_verify_render()` |
| `reopen` | `reopen` | `reopen_collab()` |
| `show-verdict` | `show-verdict` | `show_verdict()` |
| `init` | `init` | `init_collab()`, `parse_init_tokens()` |
| `contribution-budget` | `speak-render`, `rewrite-speak-render` | `enforce_contribution_budget()`, `read_budget_spec()` |
| `command-default` | all commands | `load_registry()`, `resolve_config_root()` |
| `participant-role-files` | all registry-loading commands | `validate_registry()`, `validate_participant_role_files()` |
| `planned-route-gates` | `validate` | `validate_planned_route_prerequisites()` in `commands/collab/engine/planned_routes.py` |

**How to diff:** For each module row, open the named key function(s) in `registry.py` or the named helper module and compare its `die()` / `sys.exit(1)` call strings against the exit-1 messages listed in the corresponding `## Abort families` module section above. Any string present in one but absent in the other is a spec-drift candidate.
