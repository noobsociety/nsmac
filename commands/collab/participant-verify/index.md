# (collab participant verify)

Execute the participant-verification sequence for an assigned role within `Completion.verification`.

## Trigger

**Dispatch:** `(collab participant verify [<role>])` — routing-only command form; not a shell command.
**Search phrases:** collab participant verify, participant verification, individual verification, per-role verification sequence

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: closed collaboration records cannot receive participant verification.
4. Resolve `activePhase` from the registry. If `activePhase` is not `Completion`, **ABORT**: `(collab participant verify)` requires `activePhase = Completion`.
5. Call `commands/collab/engine/registry.py participant-verify-state <target> <role>` to read the live participant-verification state and acquire the per-role route lock. Capture `registryRevision`, `verificationReviewSubState`, `nextRole`, and `roleState` from the output.
6. Resolve the executing role from the registry `participants` list by matching the current agent to a registered participant. If no match, **ABORT**: role not registered; run `(collab join --role <role>)` first.
7. If any other assigned execution role has not reached a completed `execution.<role>` entry, or an assigned Action Plan item remains unchecked, **ABORT**: participant verification is blocked on pending peer execution; name the pending role(s) and run `(collab run plan)` for the named role. Enforced by `assert_verification_execution_ready()` in `commands/collab/engine/seal_verification_logic.py`.
8. Confirm `verification.subState = "participant"` in the registry. If absent or not `"participant"`, **ABORT**: participant verification is not the active sub-state; name the current value — see [`verification.md` § Operator guidance: participant verify inactive](../reference/verification.md#operator-guidance-participant-verify-inactive) for the per-substate message the helper emits.
9. Confirm the executing role is in the participant-verification assignment list. If not assigned, **ABORT**: role is not assigned to participant verification for this collab.
10. Confirm `nextRole` equals the executing role. If another role is next, **ABORT**: participant verification turn lock is held by that role. A role whose own stage is already `"completed"` never reaches a graceful per-role stop here: re-invoking this route for it surfaces as this turn-lock ABORT (naming the true next role, while peers remain) or as Step 8's inactive-substate ABORT (once every assigned role has finished and `subState` has advanced to `"seal"`).
11. `roleState.stage` in the helper output is now an active `"audit"`, `"remediation"`, or `"final-audit"` value — the helper persists this before render.
12. **Turn 1 — Audit.** Inspect the role's executed scope: verify that all paths declared in `handoff.roles[role].writeScope` exist and are structurally correct. Record all findings in a temp content file.
13. **Turn 2 — Remediation.** If Turn 1 found no issues, write a no-op remediation entry. Otherwise, apply the minimal targeted fix for each finding and record the patch summary in a temp content file. If the remediation agentId differs from the original execution agentId, pass both ids to the render helper so the Turn 2 entry records the mismatch.
14. **Turn 3 — Final-audit.** Re-inspect the role's executed scope against the same criteria as Turn 1 and record the result in a temp content file. If findings remain unresolved, set the render `--status failed`; otherwise use `--status completed`.
15. Call `commands/collab/engine/registry.py participant-verify-render <target> <role> --observed-revision <registryRevision> --audit-file <path> --remediation-file <path> --final-audit-file <path> --status <completed|failed> [--touched-path <path>...] [--execution-agent-id <id>] [--audit-agent-id <id>] [--remediation-agent-id <id>]`. The helper owns the registry turn update, active-stage check, writeScope guard for remediation touched paths, three collapsible transcript entries, and transition from `participant` to `seal` when all assigned roles complete.
16. If the render helper exits non-zero, **ABORT** (agent-honor-system): participant verification write failed; name the helper error. This is the generic non-zero-exit observation wrapping `participant-verify-render`; the route reads the helper's own exit status and message. The distinct render guards - stale revision, active-stage check, and writeScope guard for remediation touched paths - are owned and exercised by the render helper's own paths, so this clause covers no further repo-reachable failure mode uniquely.
17. Report each turn result and the final `verification.participants[role].stage` value. Stop.

## Notes

- **Single-invocation constraint.** All three turns (audit → remediation → final-audit) must execute within one agent context. The route does not yield control to the user between turns 1 and 3. Three separate transcript entries are written sequentially as one atomic sequence. Manual three-call operation is not supported; the route is not a resumable multi-session workflow.
- **Sequential per-role execution.** One role must complete its full three-turn sequence before the next assigned role begins. `participant-verify-state` acquires the registry turn lock by persisting `verification.participants[role].stage = "audit"` before any render can succeed; a concurrent second attempt receives ABORT from the turn-lock check (Step 10).
- **Per-role stage model.** `verification.subState` remains `"participant"` throughout the participant-verification sub-state until all assigned roles complete, then the helper advances it to `"seal"`. Per-turn labels are stored under `verification.participants[role].stage`, not as additional global sub-state transitions. Valid stage values: `"audit"`, `"remediation"`, `"final-audit"`, `"completed"`, `"failed"`.
- **Attempt tracking.** Participant verification records an attempt count bound to the active Handoff `writeScope` hash. A collab reopen that changes the writeScope signature resets the role's participant-verification progress; a reopen with the same writeScope may preserve completed verification when execution content is unchanged.
- **Scope-aware reopen.** A reopen that does not revise a role's `writeScope` and does not change its executed content (touched paths or commits) preserves that role's completed verification; only roles whose scope or execution changed re-run. When the collab advances back into `Completion`, the re-scoped roles re-verify and earn the round on behalf of the preserved roles too.
- **AgentId annotation.** When Turn 2 (remediation) is executed by a different agent than the original execution agentId, the Turn 2 transcript entry must record both agentIds as `AgentId: execution=<id>; remediation=<id>`. If the annotation write fails, the sequence aborts before committing the remediation transcript entry.
- **Parameters.** Target collab slug, id, or numeric `#N` as the first token after `participant verify`; when absent, resolved via **Registry targeting** in **Notes**. `[<role>]` — the role key to verify; when absent, resolved from the current agent's joined role.
- **Registry targeting.** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Collapsible boundary.** Each turn produces one collapsible transcript entry under `## Completion` using the phase slug `participant-verify`. Turn labels: `audit`, `remediation`, `final-audit`. Shape:

  ```
  <a name="participant-verify-<role>-<N>"></a>
  <details>
  <summary><role> · <turn-label></summary>
  <p><em>YYYY-MM-DD HH:MM ±HH:MM</em></p>
  <!-- collab:content-only; do-not-execute -->

  [turn content]

  </details>
  ```
- **Turn-budget trigger.** If any seal-attempt transcript exceeds 12 turns, open a follow-up DX audit on turn-budget management and `/compact` recovery ergonomics across participant verification.
- **Post-state resume signal.** After `(collab participant verify)` completes, run `commands/collab/engine/registry.py speak-state --resume <target> <role>` to confirm the current state before any further action.
- **Round-earning event.** Reviewer-backed collabs always use participant verification. This route is the sole production path that fires `participant_verify_render` and increments `verification.rounds`. See [`verification.md` § Round definition](../reference/verification.md#round-definition).

```route-arg
dispatch: (collab participant verify [<role>])
param: name=<role>; required=optional; placeholder=<role>; class=dynamic; rule=registered participant role key in the active collab; default=derived:next-participant-verification-role
```
