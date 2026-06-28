# (collab log)

Display the registry changelog for a collaboration record — a sequenced list of explicit registry events sourced from the append-only revision store. The changelog is not the transcript revision history: transcript contribution rewrites (`(collab rewrite speak)`, implemented via `prepend_revision_history` in `registry.py`) record per-contribution edit history inside each transcript block and are a distinct surface.

## Trigger

**Dispatch:** `(collab log [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab log, registry changelog, collab event history, revision log

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `commands/collab/engine/registry.py log <target>`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `log`; when absent, resolved per **Registry targeting** in **Notes**.
<!-- abort: log-registry-target -->
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Data source:** Reads from `<state-root>/revisions/<collabId>/` — the append-only revision store introduced by collab #52 (`collab-state-observability`). The store must exist; if the `revisions/` directory is absent or the collab has no entries, the helper reports `no log entries` and exits cleanly. Retroactive behavior for pre-existing collabs (those initialized before the revision store existed) is documented in the revision writer spec.
- **Event sequence:** Each log entry carries an `eventIndex` value — a counter that increments only on explicit log events. Header rewrites, transcript rendering, and state repair do not increment `eventIndex` unless they deliberately emit a registry event. The `eventIndex` is distinct from the write-guard `revision` counter; see [schema-evolution.md](../../../commands/collab/reference/schema-evolution.md) for the counter lifecycle.
- **Output shape:** One entry per line in descending `eventIndex` order (newest first). Each line: `#<eventIndex>  <ISO-8601 timestamp>  <event-type>  <summary>`. Example:

  ```
  #12  2026-06-03T14:20:00+02:00  speak       handoff tw
  #11  2026-06-03T14:17:00+02:00  speak       action-plan tw
  #10  2026-06-03T14:08:00+02:00  speak       conclusion tw
  ```

- **Naming disambiguation:** "Registry changelog" is the correct framing for this command's output. Do not conflate it with the `<details><summary>Revision history</summary>` blocks in transcript contributions, which record per-contribution rewrites and are written by `prepend_revision_history` (`registry.py:4179`). These are two distinct history surfaces: one for registry state events, one for transcript content edits.
- **Read-only:** The route does not mutate registry state or transcript text.
- **Precondition:** `(collab log)` requires the append-only revision writer to be present. If the writer is absent, log output is empty for all collabs regardless of activity. The writer is a hard precondition for this route's usefulness; its implementation and `eventIndex` counter are a single deliverable.

```route-arg
dispatch: (collab log [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
