# /collab show policy

Document the gate policy that decides when a collaboration needs a reviewer judgment pass, and list available roles.

## Trigger

**Slash:** `/collab show policy`
**Signature:** `/collab show policy`
**Prose dispatch:** `(collab show policy)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** collab gate policy, reviewer, gate-blocked state, available roles

## Steps

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Read this policy when a collab needs judgment without depending on a specific participant being present.
2. Treat the trigger set as role-agnostic conditions that can fire in any collab.
3. Resolve the reviewer from registry `reviewerRole` when set; otherwise apply the **Reviewer fallback** in **Notes**.
4. If a trigger fires and no safe assignee exists, pause the collab as gate-blocked instead of advancing.
5. Do not mutate registry state from this documentation-only route.
6. To list available roles, call `tools/collab/registry.py roles` from the repository root. This reads every file under `cursor/_roles/` and outputs one participant-row per role.

## Notes

- **Parameters:** no arguments are accepted.
- **Documentation-only status:** This route documents policy and lists roles. It does not mutate registry state. No machine-readable registry field exists for gate assignment in this version. The future field name is `reviewer`.
- **Gate policy:** A gate policy separates durable trigger conditions from the role assigned to close the gate.
- **Gate triggers:** Any one condition fires the gate: all non-reviewer, non-moderator participants complete one full exchange without convergence; those participants converge but change Audit framing; the direction creates notable cost, migration, or maintenance risk not present in Audit; the moderator explicitly requests a judgment pass.
- **Reviewer:** Set the reviewer at collab initialization or roster setup using `/collab set reviewer <role>`. Do not reassign mid-collab.
- **Reviewer fallback:** When no `reviewerRole` is set, assign implementation-risk triggers to the participant with the closest implementation concerns, coherence or documentation-source triggers to the participant with the closest documentation concerns, and moderator-judgment triggers to the moderator only as a last resort before escalation.
- **Assignment timing:** Set reviewer once at initialization or initial roster setup. Do not reassign mid-collab.
- **Gate-blocked state:** Gate-blocked means a trigger fired but no current participant can safely own the gate. Gate-blocked is a non-error pause that prevents phase advancement until a safe reviewer joins or the moderator explicitly records an accepted-risk override.
- **Phase presence:** When reviewer is set via `reviewerRole`, the lifecycle enforces: reviewer speaks once, last, in convergent phases (`Audit`, `Conclusion`); reviewer may speak in `Discussion` when the optional-phases list includes it; reviewer stays silent in `Action Plan`, `Handoff`, and `Completion` unless a re-Audit signal fires. In `Completion.verification`, the reviewer issues `/collab seal verification` to record the seal object; this is the reviewer's terminal obligation for reviewer-backed collabs. Execution (`Completion.execution`) precedes sealing (`Completion.verification`); close is blocked until a current non-stale `verificationSeal` exists.
- **Verification sub-state semantics:** See [`_verification.md`](_verification.md) for the full sub-state model, round definition, seal object schema, stale-seal triggers, cap-exit options, and reviewer obligation.
- **writeScope reopen advisory:** When the reviewer discovers out-of-scope work during `Completion.verification`, the only registered exit is `/collab seal verification --cap-exit reopen-handoff`. See [`_verification.md`](_verification.md) for the full advisory and cap-exit option set.
- **Role catalog:** `tools/collab/registry.py roles` is the authoritative source for available roles. No role key is hard-coded in this policy.

## Provenance

`Audit` phase citations supplied by the moderator are live-session references:

- Prefer repo-relative paths checked into the repository.
- When an external document is required, cite the source during the live session and summarize the durable facts needed for the audit record.
- Transient local paths (e.g., `~/Downloads/`) are not durable references. They are valid as working context during a live session but must not be retained as citations in the audit record, because they will be unresolvable from any other machine or after the file is moved.

## Drift

The following risks do not produce a single observable failure. They accumulate as gradual divergence and will not announce themselves. "No incident" is not the same as "no problem."

When an Action Plan item resolves a Drift deferral, the same completion path must update this section before recording execution as complete: move the row to **Resolved structural items** with source/test provenance, or remove it when the trigger is no longer applicable and no audit value would be preserved.

**Slow-rot risks (no single failure event):**

- **Spec/helper divergence:** `speak.md` and other route specs describe helper call shapes. When the helper evolves, the spec can silently contradict it. The gap only surfaces when a new contributor relies on the spec and gets an unexpected result.
- **Spec/helper divergence at verification boundary:** `seal-verification.md` describes the `seal-render`, `seal-state`, and verification round helper shapes. If `tools/collab/registry.py` evolves those subcommands without updating the route spec, contributors receive unexpected results or silent wrong-state writes at the exact point where seal integrity is most critical.
- **Seal staleness on execution rewrites:** `verificationSeal` binds to an `observedRevision` and specific `executionEntries`. A rewrite via `/collab rewrite execution` after sealing changes the execution evidence the seal was written against. If the helper's staleness call in the rewrite path fails silently, the seal appears valid but covers different evidence than it recorded. Each staleness trigger must have a paired shell test asserting invalidation.
- **Reviewer-prose drift vs seal object:** A reviewer may write "looks good" in a Discussion or Conclusion contribution and later issue a seal that records different `touchedPaths` or `validationScopes` than the prose implied. No route breaks; the audit trail is internally inconsistent. The seal is the machine-readable record; reviewer prose is explanatory context only.
- **Reviewer-prose staleness:** The reviewer block in transcript headers is hand-written. A pending reviewer that joins late, or a reviewer block that is never updated, bakes inaccurate state into the audit trail. No route breaks; the record is simply wrong.
- **Moderator-input transience:** Audit inputs cited as local paths become unresolvable when the file moves or the machine changes. The transcript remains parseable but its evidence base is gone. See **Provenance** above.
- **Honor-system / helper drift:** A route stays marked `agent-honor-system` while the underlying helper begins enforcing the same abort path. The P9 coverage gate (`tools/cursor/coverage-gate.sh`) detects missing tests for helper-enforced paths but does not detect routes whose `agent-honor-system` marker is no longer accurate — the inverse drift remains invisible until a manual audit.

**Resolved structural items (provenance retained):**

These items were previously deferred here and later implemented or superseded. They stay visible as audit provenance, not as backlog.

| Item | Resolution provenance |
|---|---|
| Join/speak registry + transcript transaction | Resolved by `tools/collab/registry.py` `commit_registry_and_transcript`, which writes registry and transcript together with rollback on known write failures; covered by `tests/tools/collab/registry.py/registry.py__validates_registry_flows.test.sh` for `speak-render` and `join-participants` persistence. |
| Participant-table render helper | Resolved by `tools/collab/registry.py render-participants` and `join-participants`; covered by `tests/tools/collab/registry.py/registry.py__validates_registry_flows.test.sh` assertions that stale participant rows are replaced from registry state. |
| Tombstone-style contribution retract | Resolved by `tools/collab/registry.py retract-speak`; covered by `tests/tools/collab/registry.py/registry.py__enforces_speak_contracts.test.sh` assertions that the tombstone is written, original content is retained, and retract is rejected after Completion. |

**Deferred structural items (trigger-based backlog):**

These items were surfaced in `collab-command-assessment-feedback` (2026-05-01) and explicitly deferred. They should be re-opened when the named trigger fires — not before.

| Item | Concrete-failure trigger |
|---|---|
| Helper CLI versioning (documented contract for subcommand input/output shape) | A subcommand rename or field removal breaks a route spec in production |
| Action Plan → GitHub issue export (`/collab export-issues` or equivalent) | A collab's Action Plan is large enough that manual issue creation becomes the bottleneck |
| Capability-class enforcement for mutating collab routes | A trusted actor channel exists for at least two supported harnesses, or an integration test can distinguish a joined caller from a non-joined caller for a mutating collab route |
