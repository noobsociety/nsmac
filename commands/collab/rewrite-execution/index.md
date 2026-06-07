# /collab rewrite execution

Rewrite the calling role's last execution record in-place within the Completion section.

## Trigger

**Slash:** `/collab rewrite execution`
**Signature:** `/collab rewrite execution`
**Prose dispatch:** `(collab rewrite execution)` — prose routing hint; not a terminal command.
**Search phrases:** collab rewrite execution, retry collaboration execution, redo last execute

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: closed collaboration records cannot be re-executed.
4. Resolve the active phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
5. If the active phase is not `Completion`, **ABORT**: `/collab rewrite execution` is valid only when registry `activePhase` is `Completion`.
6. Resolve the executing role from the registry participants list. Match the current agent to a registered participant. If no match, **ABORT**: role not registered; run `/collab join --role <role>` first.
7. Read `## Completion` and locate the role's last execution-history entry. If the last entry is already marked `completed`, **ABORT**: last execution already succeeded; nothing to retry.
8. If no execution-history entry exists for this role, **ABORT**: no prior execution record to rewrite; use `/collab run plan` to begin execution.
9. Append the next numbered item to the execution history as `<n>. **<role>:** in progress YYYY-MM-DD HH:MM — re-execution started.` only when retry work begins before validation can complete in the same visible record; otherwise keep the retry marker internal and collapse visible history on success.
10. Re-run the action-plan implementation: re-read `## Action Plan`, collect all unchecked role-scoped checklist items, and implement them.
11. Run scoped validation for the executing role. Minimum scoped validation is `./platform/tooling/audit.sh`; add targeted tests for touched behavior when available. Do not run `./tests/run.sh` for ordinary role-scoped re-execution. If the retried item is the terminal full-suite Action Plan item, run the full sequence instead: `./platform/tooling/audit.sh` + `./tests/run.sh`.
12. On validation success: locate all execution-history lines belonging to the prior failed attempt — the `in progress` line, if present, and its subsequent `failed` line. Replace them with a single new success line: `<n>. **<role>:** completed YYYY-MM-DD HH:MM — validation passed; <scope>; <N> paths.` Move the removed lines into a collapsed history block using the **Revision history shape** in **Notes**, placed immediately after the new success line. Remove the "in progress" line written in step 9 as well; it belongs in the history block. Do not leave any failure or stale in-progress line visible.
13. On validation failure: append `<n>. **<role>:** failed YYYY-MM-DD HH:MM — validation failed: <failed command>; <scope>; <N> paths.` after the in-progress line written in step 9; leave all prior entries unchanged.
14. Check every completed role-scoped checklist item in `## Action Plan` as `[x]`.
15. Mirror execution state in the registry `execution` object, including validation result, validation scope, and touched paths. The helper rejects touched paths outside the role's structured Handoff `writeScope`.
16. After recording execution, call `commands/collab/engine/registry.py participant-verify-state <target> <role>` to check whether participant verification is immediately due for the executing role. If the output shows `readyToVerify: true` and `nextRole` equals the executing role, run `/collab participant verify` for the executing role before advancing. If participant verification is blocked by pending peer execution or unchecked assigned Action Plan items, report that blocker and do not force seal or close.
17. After participant-verification handling, evaluate the **Auto-close on completion** rule in `/collab run plan` **Notes**. If every non-moderator assigned role has a completed execution entry and no participant-verification blocker remains, close the record.
18. Report all changed files and validation results. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `rewrite execution`; when absent, resolved per **Registry targeting** in **Notes**.
<!-- abort: rewrite-execution-registry-target -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Rewrite semantics:** `/collab rewrite execution` rewrites the last execution record in-place rather than appending a parallel success alongside a visible failure. The Completion section shows only the final execution state; prior failure is preserved in a collapsed history block, not deleted.
- **Revision history shape:** Wrap the prior failed attempt (its `in progress` line when present and `failed` line, in original order) in `<details><summary>Revision history</summary>\n\nPrevious attempt, <attempt-timestamp>:\n\n<in-progress-line-if-present>\n<failed-line>\n\n</details>` placed immediately after the new success line in the execution history. If a revision history block already exists at that position (from an earlier retry), prepend the new attempt block inside the existing wrapper rather than nesting a second wrapper.
- **Completion-only guard:** `/collab rewrite execution` must refuse all phases other than `Completion`.
- **Execution boundary:** This route implements only action-plan items assigned to the current role. Its only lifecycle side effect beyond implementation is the auto-close trigger when all assigned execution is complete.
- **Touched-path enforcement:** When structured Handoff state exists for the executing role, the execution recorder rejects any touched path outside `handoff.roles.<role>.writeScope` with `"execution touched path outside declared writeScope: <path>"`. Recovery: reopen Handoff and revise scope, or remove/revert the out-of-scope change before rewriting execution.
- **Known manual surface:** Unlike `speak-render`, `rewrite-speak-render`, and `rewrite-summary`, execution-history rewrite rendering is not yet centralized in `commands/collab/engine/registry.py`; keep the manual revision-history edits constrained to the Completion execution-history lines described above until that helper surface lands.
