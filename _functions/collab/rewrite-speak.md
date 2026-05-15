# /collab rewrite speak

Rewrite the calling role's last contribution in-place within the active collab phase.

## Trigger

**Slash:** `/collab rewrite speak`
**Signature:** `/collab rewrite speak`
**Prose dispatch:** `(collab rewrite speak)` — for non-Cursor agents; not terminal-executable in Cursor.
**Search phrases:** collab rewrite speak, rewrite last contribution, redo collab speak

## Steps

**This command rewrites text only. Do not make file edits, run shell commands, or modify any codebase artifact outside `.collabs/`.**

1. Read [_invariants.md](_invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read `.collabs/registry.json` and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. If the registry status is `closed` or `archived`, **ABORT**: record is closed.
4. Resolve the active phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
5. If the active phase is `Completion`, **ABORT**: `/collab rewrite speak` is not permitted in the `Completion` phase; use `/collab rewrite execution` to rewrite execution records.
6. Resolve the speaking participant from the current agent's joined role and the registry `participants` list. If no matching participant exists, **ABORT** and tell the moderator to run `/collab join --role <role>` first.
7. Locate the role's most recent contribution `<details>` block in the active phase through `tools/collab/registry.py rewrite-speak-render`; do not call turn-gating `speak-state` for contribution lookup. If no role-owned block exists, **ABORT**: no prior contribution to rewrite; use `/collab speak` to create the first contribution.
8. The agent prepares updated content for the role based on current collab context; for the moderator role, use only the supplied `<message>` text verbatim as the replacement body. If the caller is the moderator role and no `<message>` text is present, **ABORT**: moderator-role rewrite requires human-authored text.
9. Write the replacement contribution text to a temporary content file, then call `tools/collab/registry.py rewrite-speak-render <target> <role> --content-file <path>`. When the active phase is `Action Plan`, the helper applies the shared shape validator defined in `_invariants.md` Invariant #9 before any transcript mutation; if the replacement body fails the check, the helper aborts before writing — see Invariant #9 for the abort message templates. The helper locates the latest role-owned contribution block in the active phase, identifies the active content region up to (but not including) any existing `<details><summary>Revision history</summary>` block and the closing `</details>` tag, moves the prior active content into the **Revision history shape** in **Notes**, updates the timestamp, writes the replacement content into the active region, and preserves the anchor id plus visible summary label. If the helper cannot locate the latest role-owned block, **ABORT**: treat the missing block as a helper defect and do not create a replacement block by hand.
10. Do not create a new `<details>` block. Do not add a new Table of Contents entry.
11. Stop. Do not execute any action item, make any file edit outside `.collabs/`, or run any shell command.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `rewrite speak`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from `.collabs/registry.json`, using `tools/collab/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Rewrite semantics:** `/collab rewrite speak` rewrites in-place rather than appending. The contribution count for the role in the phase does not change. One-speak phase limits are not re-checked; the intent is to update, not to add a second entry. Rewrite is role-scoped and does not advance phase state; turn-order enforcement adds no safety guarantee for this command.
- **Handoff cleanup window:** Handoff is the last phase where rewrite obligations may be fulfilled; `/collab rewrite speak` aborts in Completion (step 5). Plan contribution cleanup before the Handoff→Completion transition.
- **Revision history shape:** Wrap the prior content in `<details><summary>Revision history</summary>\n\nPrevious revision, <original-timestamp>:\n\n<prior-content>\n\n</details>` at the end of the contribution block, immediately before the closing `</details>` tag of the contribution. If a revision history block already exists, prepend the new prior-revision entry inside it rather than nesting a second wrapper.
- **Moderator boundary:** The moderator role is human-owned; write only the supplied message text verbatim and apply any rule-mandated structure-only formatting pass. Agents must not generate content for the moderator role.
- **Execution boundary:** Never perform any file edit, shell command, or codebase change as a side effect of this command. Only rewrite text within `.collabs/`.
- **Recovery path:** If `rewrite-speak-render` aborts because the role-owned block is missing or malformed, do not hand-edit the transcript. Re-run `/collab speak` when no prior block exists, or repair the malformed block in a separate moderator-approved recovery route before retrying.
- **Post-state resume signal:** After `/collab rewrite speak` completes, re-establish collab context with `tools/collab/registry.py speak-state --resume <target> <role>` before issuing the next command.
- **Reviewer-notice gate:** When the contribution being rewritten predates the most recent reviewer turn in the same phase, `rewrite-speak-render` emits `REVIEWER-NOTICE:` and re-triggers the reviewer gate before accepting the rewrite. Same-turn or rewrite-by-reviewer cases skip this check; the gate re-triggers only when a prior-round reviewer pass would otherwise be silently invalidated. Enforced at helper level, not by route steps.
