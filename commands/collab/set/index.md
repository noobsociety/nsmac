# /collab set

Update collab metadata fields that do not already belong to a dedicated mutation route.

## Trigger

**Slash:** `/collab set`
**Signature:** `/collab set <field> <value>`; or `/collab set reviewer <role>` / `/collab set reviewer --clear` / `/collab set reviewer-optional-phases <phase>...`
**Prose dispatch:** `(collab set ...)` — prose routing hint; not a terminal command.
**Search phrases:** collab set, set collaboration metadata, update collab metadata

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Resolve `<field>` from the next positional token after `set`. If missing, **ABORT**: `<field>` is required.
3. Resolve `<value>` from all remaining input after `<field>`, excluding an optional leading `--force` flag. If missing after trimming whitespace, **ABORT**: `<value>` is required.
4. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
5. Validate field ownership against **Field ownership** in **Notes**. If `<field>` is not settable in the current mode, **ABORT**: field not settable; name the field and owning route.
6. Apply the field update in the registry:
   - `title` updates the registry title and transcript H1.
   - `description` updates the registry description and the transcript opening description.
   - `turn-order` parses space-separated role keys, validates uniqueness and membership in registry `participants`, validates that no key equals `reviewerRole`, then updates registry `turnOrder` and the Turn order cell in the transcript state table.
   - `reviewer <role>` validates that `<role>` is in registry `participants`, that `<role>` does not equal `moderatorRole`, and that `<role>` is not in registry `turnOrder`; then sets registry `reviewerRole` to `<role>` with default `reviewerMode` (`last-in-convergent-phases`) and default `reviewerOptionalPhases` (`["Discussion"]`), and mirrors the value in the Reviewer cell of the transcript status table via `commands/collab/engine/registry.py render-status`.
   - `reviewer --clear` removes `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases` from the registry entry, then calls `commands/collab/engine/registry.py render-status <target>` to update the transcript status table.
   - `reviewer-optional-phases <phase>...` validates every phase name against the phase sequence, rejects duplicates, persists registry `reviewerOptionalPhases`, and re-renders the managed header/status surfaces. Changing this field after a phase has advanced does not retroactively admit the reviewer into the earlier phase.
   - `work-repo <path>` sets registry `workRepo` to the resolved canonical absolute path of the project git tree; it is the primary recovery path for a misbound or unbound collab. Validates that `<path>` is a git work tree. Once set, touched-path verification and git-state checks during seal resolve against this path instead of the default repository root. Must be an absolute path to an existing git work tree; an unresolvable or non-git path aborts.
   - `active-phase` is recovery-only: require `--force`, validate against the phase sequence, then update registry `activePhase` and the Active phase cell in the transcript state table.
7. Stop after updating registry and transcript. Do not append a contribution.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `set`; when absent, resolved per **Registry targeting** in **Notes**. `<field>` — required metadata field name. `<value>` — required replacement value (omit for `reviewer --clear`). `--force` — optional recovery-only override for fields that are normally owned elsewhere.
- **Registry targeting:** Resolve the target collab from the resolved registry, using `commands/collab/engine/registry.py` as the shared helper. When the first token after the route is present, treat it as a collab slug, id, or stable numeric position. Otherwise use `activeCollabId`. If the registry is unreadable or invalid, the token does not match any entry, or `activeCollabId` is empty, **ABORT**: registry target unavailable; name the registry field or token.
- **Field ownership:** `title` -> `set`; `description` -> `set`; `turn-order` -> `set`; `reviewer`, `reviewerOptionalPhases` -> `set`; `work-repo` -> `set`; `status` -> `open` / `close`; `participants` -> `join` / `kick`; `active-phase` -> `next` / `prev` (or `set --force` for recovery only).
- **Ownership boundary:** Every mutable field has exactly one normal mutation path. `/collab set` must refuse fields owned by another route unless `--force` is used for recovery-only metadata repair.
- **Post-state resume signal:** After `/collab set` completes, re-establish collab context with `commands/collab/engine/registry.py speak-state --resume <target> <role>` before issuing the next collab command.
- **Sync contract compliance:** `title`, `description`, `turn-order`, and `active-phase` transcript-side updates (H1, opening text, Turn order cell, Active phase cell) are prose-rendered; `commands/collab/engine/registry.py set` writes registry only. This is declared under the sync contract in [`platform/standards/route-invariant.md`](../../../platform/standards/route-invariant.md).

```route-arg
dispatch: (collab set <field> <value>)
param: name=<field>; required=required; placeholder=<field>; class=literal; values=title | description | turn-order | reviewer | reviewer-optional-phases | active-phase | work-repo
param: name=<value>; required=required; placeholder=<value>; class=type; rule=field-specific replacement value
param: name=<role>; required=required; placeholder=<role>; class=dynamic; source=commands/collab/engine/registry.py roles
param: name=--clear; required=optional; placeholder=--clear; class=literal; values=present; default=literal:false
```

```route-flag
flag: force
eligibility: eligible
guard-class: recovery-only
```
