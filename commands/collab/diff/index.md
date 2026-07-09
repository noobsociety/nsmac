# (collab diff)

Compare the current state of a collaboration record against its last recorded registry snapshot — scaffold-stripped — and surface drift across three axes: registry/transcript metadata, scaffold-stripped transcript content, and `verificationSeal.pathDigests` versus current `HEAD`. The output is advisory; it does not modify registry state or transcript content.

## Trigger

**Dispatch:** `(collab diff [<target>])` — routing-only command form; not a shell command.
**Search phrases:** collab diff, content drift, registry transcript diff, stale seal, seal drift, transcript content mismatch

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Call `commands/collab/engine/registry.py diff [<target>]`.
3. Display the helper output exactly. Stop.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `diff`; when absent, resolved per **Registry targeting** in **Notes**.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **What diff ignores (scaffold and ledger categories):** The helper strips or normalizes the following before comparing transcript content. This enumeration must exactly match `diff.ignored_scaffold_category_names()`; `test_diff_scaffold_categories` extracts these bullet titles and asserts doc<->helper set equality. Each predicate the helper composes must map to at least one named category, so a new stripped line-type cannot stay unnamed. The guard catches "a category with no predicate" and "a predicate row with no category"; a new strip step added inside `scaffold_stripped_text` that bypasses the category map would not be detected — fully closing that gap requires behavioral corpus enumeration of what the predicate chain actually drops.
  - **Contribution timestamp wrappers** — `<p><em>…</em></p>` lines rendered per contribution block.
  - **Content-only guards** — `<!-- collab:content-only; do-not-execute -->` lines.
  - **Effort-override banners** — `<!-- collab:effort-override b64:…​ -->` base64 comment lines.
  - **Full-contribution collapsible blocks** — `<details>` blocks whose first inner line is `<summary>Full contribution</summary>`; stripped by `strip_managed_full_body_lines` in `digests.py`.
  - **Managed header block** — the `<!-- collab:header-managed -->` through `<!-- collab:header-end -->` section (status table, participants table, prohibitions, reviewer note, table of contents, separator).
  - **Revision-history collapsible blocks** — managed `<details><summary>Revision history</summary>` blocks added by contribution rewrites.
  - **Action Plan checkbox state** — `[ ]` versus `[x]` checklist state changes; item text remains content.
- **False authority:** diff output is advisory; registry state remains authoritative.
- **Advisory-output contract:** `(collab diff)` reads and compares; it emits display output only. No registry write, no transcript mutation, no phase change. Running it during any phase or sub-state is safe.
- **Three output axes:** The helper distinguishes:
  1. **Seal drift** — `verificationSeal.pathDigests` recorded blob/mode versus current `HEAD` for each touched path; path-level rows with recorded blob, current blob, mode, and missing/deleted status (F3).
  2. **Content mismatch** — scaffold-stripped transcript contribution text differs from the per-contribution baseline recorded in `<transcript-stem>-contributions.json` (written by the speak path). When no store exists yet, every current contribution surfaces as "added" (F1).
  3. **Metadata mismatch** — registry field values differ from what the transcript header mirrors (F2).
- **Read-only:** The route does not mutate registry state or transcript text.

## Examples

### F3 scenario — stale seal after a post-seal commit

A `verificationSeal` was recorded at revision 18 for `collab-render-seal-facade-boundary`. A subsequent commit updated a touched path. The seal was silently invalidated; without `(collab diff)`, the reviewer's only recovery was raw git plumbing (`git cat-file`, `rev-parse`) against the registry's recorded `pathDigests`. `(collab diff)` closes this gap.

Running `(collab diff collab-render-seal-facade-boundary)` after the post-seal commit:

```
collab diff: collab-render-seal-facade-boundary
seal drift (1 paths):
  commands/collab/engine/transcript_render.py
    recorded blob: a3f8c1d…  mode: 100644
    current  blob: 7b2e09f…  mode: 100644
    status: changed
content mismatch (0 contributions):
  (none)
metadata mismatch (0 fields):
  (none)
```

The recorded blob matches the digest in `verificationSeal.pathDigests`; the current blob reflects the post-seal commit. The reviewer sees exactly what drifted before re-running the seal, instead of reconstructing it from raw git plumbing.

**Deleted-path variant:** If a touched path is deleted after the seal:

```
seal drift (1 paths):
  commands/collab/engine/transcript_render.py
    recorded blob: a3f8c1d…  mode: 100644
    current  blob: (deleted)  mode: 000000
    status: deleted
```

```route-arg
dispatch: (collab diff [<target>])
param: name=<target>; required=optional; placeholder=<target>; class=dynamic; rule=collab slug, id, or #N; defaults to active collab; default=derived:active-collab
```
