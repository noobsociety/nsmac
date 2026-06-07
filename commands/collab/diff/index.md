# /collab diff

Show the diff between the registry-derived content state and the content-only sections of a collaboration transcript. The managed header — everything from the start of the file up to and including `<!-- collab:header-managed -->` — is excluded from the comparison; only the content below that boundary is compared.

## Trigger

**Slash:** `/collab diff`
**Signature:** `/collab diff [<target>]`
**Prose dispatch:** `(collab diff [<target>])` — prose routing hint; not a terminal command.
**Search phrases:** collab diff, transcript diff, content diff, registry transcript comparison

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `commands/collab/engine/registry.py diff <target>`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `diff`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Content boundary:** The `<!-- collab:header-managed -->` comment marks the boundary between the managed header and the content-only body. Everything from the start of the transcript file through `<!-- collab:header-managed -->` is managed by the helper (`render_managed_header_text`) and is excluded from the diff. The comparison starts at the first line after `<!-- collab:header-managed -->`. Do not include the managed header, TOC, generated participant tables, or lifecycle projection fields in the diff output.
- **Comparison model:** The diff compares a normalized projection of registry-derived content (what the registry says the transcript should contain) against the actual content-only sections of the transcript file on disk. The projection function extracts content sections without rebuilding managed fields from scratch; this avoids over-reporting header churn as a diff.
- **No-diff output:** When the registry-derived content and the on-disk content-only sections match, the helper reports `no diff` and exits cleanly.
- **Read-only:** This route does not mutate registry state or transcript text.

```route-arg
dispatch: (collab diff [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
