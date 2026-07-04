# (collab release)

Preview or execute the explicit collaboration release plan. Here `release` as
the `(collab release)` command verb is distinct from the conventional-commit
`release` scope, such as `chore(release): merge dev to main`. This v1 route
wires local tag creation and optional tag push only; release PR, direct merge,
GitHub release, and changelog automation are declared but not wired until v2.

## Trigger

**Dispatch:** `(collab release [<target>] [--tag <name>] [--confirm] [--push] [--direct-merge] [--github-release] [--auto-fire])` — routing-only command form; not a shell command.
**Search phrases:** collab release, release collab, preview release plan

## Steps

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Resolve the target collab with **Registry targeting** in **Notes**.
2. Read the resolved registry and the resolved transcript path. If either is unreadable, **ABORT**: record unreadable; name the path.
3. Call `commands/collab/engine/registry.py release [<target>] [--tag <name>] [--confirm] [--push] [--direct-merge] [--github-release] [--auto-fire]`. Omit `--confirm` for the default dry-run.
4. Display the helper output. If it emits `NEXT:` or `GATED:`, relay that line exactly.
5. Stop after the helper reports the dry-run plan, confirmation gate, or explicit auto-fire result.

## Notes

- **Parameters:** target collab slug, id, or numeric `#N` as the first token after `release`; when absent, resolved per **Registry targeting** in **Notes**. `--tag <name>` overrides the default `collab/<slug>` tag name. `--confirm` acknowledges release execution. `--push`, `--direct-merge`, `--github-release`, and `--auto-fire` are independent opt-ins.
- **Registry targeting:** Resolve the target collab from the first token after the route, falling back to `activeCollabId` when absent. The resolution algorithm and abort contract are owned by **Target resolution** in [`platform/standards/route-invariants.md`](../../../platform/standards/route-invariants.md); this route does not restate them.
- **Default behavior:** The default is a dry-run plan. It prints the target, work repo, `HEAD`, tag, and release options, then stops.
- **Wired v1 behavior:** With both `--confirm` and `--auto-fire`, the helper may create the annotated local tag and, when `--push` is also present, push that tag to `origin`.
- **Declared v2 behavior:** The default "open release PR and stop" flow, `--direct-merge`, and `--github-release` are intentionally not wired in v1. When requested, helper output must label them `declared, not wired (v2)` rather than `enabled`.
- **Confirmation gates:** `--confirm` is required before release execution is considered. `--auto-fire` is separately required before the helper performs the wired tag/push action; this preserves dry-run behavior for ordinary calls.
- **Changelog boundary:** This v1 route reports changelog as deferred because `doc/write-changelog` is not present in this repository. Rebuilding changelog generation belongs to a separate collab.
- **Close boundary:** `(collab close)` and host `post-close` notifications are not release orchestration surfaces. Release work starts only from this explicit route.
- **Git-state guardrails:** The helper rejects a dirty work tree before release planning or execution so the plan is anchored to an inspectable `HEAD`.
- **Role boundary:** The route is role-agnostic because it leaves collab phase, participant, and transcript state unchanged. Direct helper invocations may pass `--caller-role`, but the release helper does not use it for authorization; git-state and confirmation gates are the enforcement surface.
- **Post-state resume signal:** The route does not change collab registry phase. Run `commands/collab/engine/registry.py speak-state --resume <target> <role>` before any later collab phase contribution.

```route-arg
dispatch: (collab release [<target>] [--tag <name>] [--confirm] [--push] [--direct-merge] [--github-release] [--auto-fire])
param: name=target; required=optional; placeholder=<target>; class=type; rule=collab slug, id, or numeric #N; default=derived:activeCollabId
param: name=--tag; required=optional; placeholder=<name>; class=type; rule=git tag name; default=derived:collab/<slug>
param: name=--confirm; required=optional; placeholder=--confirm; class=literal; values=present; default=literal:false
param: name=--push; required=optional; placeholder=--push; class=literal; values=present; default=literal:false
param: name=--direct-merge; required=optional; placeholder=--direct-merge; class=literal; values=present; default=literal:false
param: name=--github-release; required=optional; placeholder=--github-release; class=literal; values=present; default=literal:false
param: name=--auto-fire; required=optional; placeholder=--auto-fire; class=literal; values=present; default=literal:false
```
