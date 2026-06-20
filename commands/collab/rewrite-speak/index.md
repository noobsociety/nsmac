# (collab rewrite speak)
 
## Turn-gating rule

`(collab rewrite speak)` is contribution-scoped, not turn-scoped. A
participant that already has a contribution in the active non-Completion
phase may rewrite that contribution through `rewrite-speak-render` even
when normal `speak-state` would report another expected role.

Do not use speak-state turn gating to decide whether a rewrite is allowed.
Rewrite the calling role's last contribution in-place within the active collab phase.

## Trigger

**Dispatch:** `(collab rewrite speak)` — routing-only command form; not a shell command.
**Search phrases:** collab rewrite speak, rewrite last contribution, redo collab speak

## Steps

**This command rewrites text only. Do not make file edits, run shell commands, or modify any codebase artifact outside the user-scope collab state root.**

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. Resolve the active phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
5. If the active phase is `Completion`, **ABORT**: `(collab rewrite speak)` is not permitted in the `Completion` phase; use `(collab rewrite execution)` to rewrite execution records.
6. Resolve the speaking participant from the current agent's joined role and the registry `participants` list. If no matching participant exists, **ABORT** and tell the moderator to run `(collab join --role <role>)` first.
7. Locate the role's most recent contribution `<details>` block in the active phase through `commands/collab/engine/registry.py rewrite-speak-render`; do not call turn-gating `speak-state` for contribution lookup. If no role-owned block exists, **ABORT**: no prior contribution to rewrite; use `(collab speak)` to create the first contribution.
8. The agent prepares updated content for the role based on current collab context; for the moderator role, use only the supplied `<message>` text verbatim as the replacement body. If the caller is the moderator role and no `<message>` text is present, **ABORT**: moderator-role rewrite requires human-authored text.
9. Write the replacement contribution text to a temporary content file, then call `commands/collab/engine/registry.py rewrite-speak-render <target> <role> --content-file <path>`. If the visible excerpt would exceed 250 words, split the content: keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file. The excerpt cap is not permission to summarize away useful reasoning, evidence, or edge cases; preserve that material in the full body instead of trimming it out. The helper replaces both the active excerpt and the active full body together and moves the prior content (including any prior full body) into revision history — see [contribution-annex.md](../../../commands/collab/reference/contribution-annex.md) **Parser Contract**. When the active phase is `Action Plan`, the helper applies the shared shape validator defined in `invariants.md` Invariant #9 before any transcript mutation; if the replacement body fails the check, the helper aborts before writing — see Invariant #9 for the abort message templates. The helper locates the latest role-owned contribution block in the active phase, identifies the active content region up to (but not including) any existing `<details><summary>Revision history</summary>` block and the closing `</details>` tag, moves the prior active content into the **Revision history shape** in **Notes**, updates the timestamp, writes the replacement content into the active region, and preserves the anchor id plus visible summary label. If the helper cannot locate the latest role-owned block, **ABORT**: treat the missing block as a helper defect and do not create a replacement block by hand.
10. Do not create a new `<details>` block. Do not add a new Table of Contents entry.
11. Stop. Do not execute any action item, make any file edit outside the user-scope collab state root, or run any shell command.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `rewrite speak`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Rewrite semantics:** `(collab rewrite speak)` rewrites in-place rather than appending. The contribution count for the role in the phase does not change. One-speak phase limits are not re-checked; the intent is to update, not to add a second entry. Rewrite is role-scoped and does not advance phase state; turn-order enforcement adds no safety guarantee for this command.
- **Handoff cleanup window:** Handoff is the last phase where rewrite obligations may be fulfilled; `(collab rewrite speak)` aborts in Completion (step 5). Plan contribution cleanup before the Handoff→Completion transition. When a non-success assessment verdict reopens `Handoff` via `(collab reopen handoff)`, the cleanup window re-opens and `(collab rewrite speak)` becomes available again for that phase.
- **`(collab reopen)` contract:** The registered route for phase restoration after a non-success assessment verdict is `(collab reopen <action-plan|handoff>)`. It performs the full reset — status, phase, turn order, completion sub-state, stale seal state, and verdict — before any contributor may re-speak. Use `(collab reopen)` as the restore command, not `(collab set active-phase --force)`, which does not perform the full reset.
- **Handoff registry resync:** When the active phase is `Handoff` and the rewritten contribution contains `**writeScope**` or `**validationCommands**` headings, `rewrite-speak-render` resyncs the registry structured Handoff state (`handoff.roles.<role>.writeScope`, `validationCommands`, and `body`) to match the rewritten content. Without resync, a Handoff rewrite silently leaves registry fields stale, causing `record_execution`'s touched-path gate to reject paths added or removed in the rewrite. The registry-sync implementation details and example block appear in the registry-sync clause below.
- **Revision history shape:** Wrap the prior content in `<details><summary>Revision history</summary>\n\nPrevious revision, <original-timestamp>:\n\n<prior-content>\n\n</details>` at the end of the contribution block, immediately before the closing `</details>` tag of the contribution. If a revision history block already exists, prepend the new prior-revision entry inside it rather than nesting a second wrapper.
- **Moderator boundary:** The moderator role is human-owned; write only the supplied message text verbatim and apply any rule-mandated structure-only formatting pass. Agents must not generate content for the moderator role.
- **Execution boundary:** Never perform any file edit, shell command, or codebase change as a side effect of this command. Only rewrite text within the user-scope collab state root.
- **Recovery path:** If `rewrite-speak-render` aborts because the role-owned block is missing or malformed, do not hand-edit the transcript. Re-run `(collab speak)` when no prior block exists, or repair the malformed block in a separate moderator-approved recovery route before retrying.
- **Post-state resume signal:** After `(collab rewrite speak)` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before issuing the next command.
- **Full-body split:** `rewrite-speak-render` enforces the 250-word excerpt cap. When the replacement excerpt exceeds 250 words, keep --content-file as a capped standalone excerpt and put complete detail in --full-body-file. The cap is not permission to summarize away useful reasoning, evidence, or edge cases; preserve that material in the full body instead of trimming it out. See [`contribution-budget.md`](../../../commands/collab/reference/contribution-budget.md) **Word limit**.
- **Effort override slot:** The replacement content supplied to `rewrite-speak-render` must include the `EFFORT OVERRIDE: <level> — <category>: <signal>` line for any mandatory-declaration turn (see `agent-effort.md`). The helper enforces this at render time; a rewrite that removes the override line from a mandatory-declaration turn will be rejected.
- **Reviewer-notice gate:** When the contribution being rewritten predates the most recent reviewer turn in the same phase, `rewrite-speak-render` emits `REVIEWER-NOTICE:` and re-triggers the reviewer gate before accepting the rewrite. Same-turn or rewrite-by-reviewer cases skip this check; the gate re-triggers only when a prior-round reviewer pass would otherwise be silently invalidated. Enforced at helper level, not by route steps.

### Handoff Registry-Sync Clause

When `(collab rewrite speak)` runs in `Handoff`, the helper parses the replacement body with the same structured Handoff parser used by `(collab speak)`. The helper then replaces `handoff.roles.<role>.writeScope`, `handoff.roles.<role>.validationCommands`, and `handoff.roles.<role>.body` in the registry before committing the transcript rewrite. This keeps the registry write boundary consumed by `(collab run plan)`, `execute-spawn`, and `execution --touched-path` aligned with the visible Handoff text.

Example replacement body:

```markdown
EFFORT OVERRIDE: high — delivery-or-migration-risk: Handoff scope revised after verification found one missing route file

Implementation scope is revised after verification found one missing route file.

**writeScope**
`commands/collab/index.md`
`commands/collab/reopen/index.md`
`commands/collab/engine/registry.py`

**validationCommands**
`[["./platform/tooling/audit.sh"],["./tests/run.sh"]]`
```
