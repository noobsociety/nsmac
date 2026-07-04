# (collab tag)

Create or preview the local git tag for a collaboration record.

## Trigger

**Dispatch:** `(collab tag [<target>] [--tag <name>] [--confirm] [--push])` — routing-only command form; not a shell command.
**Search phrases:** collab tag, create collab tag, preview collab tag

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Call `commands/collab/engine/registry.py tag [<target>] [--tag <name>] [--confirm] [--push]`. Omit `--confirm` for the default dry-run. Include `--push` only when the caller explicitly wants `git push origin <tag>` after local tag creation.
4. Display the helper output. If it emits `NEXT:`, relay that line exactly.
5. Stop after the helper reports the dry-run plan or the confirmed tag result.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `tag`; when absent, resolved per **Registry targeting** in **Notes**. `--tag <name>` overrides the default `collab/<slug>` tag name. `--confirm` creates the local annotated tag. `--push` is valid only as an explicit outward-action opt-in after local tag creation.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Default behavior:** The default is a dry-run that prints target, work repo, `HEAD`, tag name, and push state. It leaves the repository unchanged.
- **Confirmation gate:** `--confirm` is required before the helper creates a tag. `--push` is a second explicit opt-in for pushing that tag.
- **Git-state guardrails:** The helper rejects a dirty work tree before creating or previewing the tag so the release tag is anchored to an inspectable `HEAD`.
- **Role boundary:** The route is role-agnostic because it leaves collab phase, participant, and transcript state unchanged. Direct helper invocations may pass `--caller-role`, but the tag helper does not use it for authorization; git-state and confirmation gates are the enforcement surface.
- **Post-state resume signal:** The route does not change collab registry phase. Run `commands/collab/engine/registry.py speak-state --resume <target> <role>` before any later collab phase contribution.

```route-arg
dispatch: (collab tag [<target>] [--tag <name>] [--confirm] [--push])
param: name=target; required=optional; placeholder=<target>; class=type; rule=collab slug, id, or numeric #N; default=derived:activeCollabId
param: name=--tag; required=optional; placeholder=<name>; class=type; rule=git tag name; default=derived:collab/<slug>
param: name=--confirm; required=optional; placeholder=--confirm; class=literal; values=present; default=literal:false
param: name=--push; required=optional; placeholder=--push; class=literal; values=present; default=literal:false
```
