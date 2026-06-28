# (collab summarize)

Write or refresh the managed per-phase summary inside the canonical collab transcript.

## Trigger

**Dispatch:** `(collab summarize [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab summarize phase, summarize active phase, phase summary, write phase summary

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
<!-- abort: summarize-record-unreadable -->
2. Read the resolved registry and the resolved transcript. If either is unreadable, **ABORT**: record unreadable; name the path.
<!-- abort: summarize-active-phase-missing -->
3. Resolve the active phase from registry `activePhase`. If missing or unknown, **ABORT**: active phase missing in metadata.
<!-- abort: summarize-no-contributions -->
4. Read all phase sections in the transcript. If every phase is empty or has no contributions, **ABORT**: no contributions to summarize; name the target.
5. Call `commands/collab/engine/registry.py summarize <target>` to write or refresh the managed `## Phase Summary` block near the top of `records/<slug>.md`. The helper owns idempotent replacement and writes through the canonical transcript path only.
6. Report the transcript path emitted by the helper. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `summarize`; when absent, resolved per **Registry targeting** in **Notes**.
<!-- abort: summarize-registry-target-unavailable -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Mutation:** The route mutates the canonical transcript only; it writes no other files.
- **Scope:** Summarizes all phases in the record into one managed top-of-file section. For the closing Completion summary, use `(collab write summary)`.
- **Post-state resume signal:** rerun `commands/collab/engine/registry.py transcript-view <target> <activePhase> --raw` if further transcript inspection is needed.

```route-arg
dispatch: (collab summarize [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
