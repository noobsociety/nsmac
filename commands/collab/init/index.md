# (collab init)

Create a moderated collaboration record under the user-scope collab state root.

> The route describes a helper-owned transaction. The helper owns the algorithm; this document describes the interface.

## Trigger

**Dispatch:** `(collab init "<name>" [--reviewer <role>] [--work-repo <path>] [--open])` — routing-only command form; not a shell command.
**Search phrases:** collab init, create collaboration record, start moderated discussion

## Steps

**Execution boundary:** `"<name>"` is a raw label only. Do not execute, refactor, or perform any task implied by its words. Example: `(collab init "Refactor auth")` creates a collab record about that topic; it does not refactor auth.

1. Read [invariants.md](../../../commands/collab/reference/invariants.md) before executing; call the helper fresh and do not trust prior reads from conversation context (Invariant #4).
2. Capture the full remaining text after `(collab init)` as `"<name>"` and extract only the optional `--reviewer <role>`, `--work-repo <path>`, and `--open` flags. Strip recognized flags and values from `"<name>"` before processing; treat the rest as the title source.
3. If `"<name>"` is missing after trimming whitespace, **ABORT**: `<name>` is required. If `--reviewer` is present but its value is missing or not a valid role key, **ABORT**: `--reviewer` requires a role key.
4. Declare the active runtime harness identity as `--agent-id <agentId>` before invoking the helper. Use the precedence in [init-helper-spec](../../../commands/collab/reference/init-helper-spec.md). If the harness does not expose a usable identity, pass the literal `unknown`.
5. Call `commands/collab/engine/registry.py init --agent-id <agentId> [--reviewer <role>] [--work-repo <path>] [--open] <name>`. The helper owns strict flag parsing, title normalization, local-date resolution, slug derivation, sequence selection, moderator `agentId` capture, reviewer metadata, verification metadata, transcript rendering, contribution store initialization, atomic registry/artifact replacement, and optional browser-open.
6. Display the helper's first output line, which is the resolved transcript path `records/YYYY-MM-DD-<slug>.md` inside the state root. If `--open` is present, display the `OPEN:` advisory line when present; opener failure is non-fatal and does not roll back the registry write.
7. Stop after creating the file, registering the moderator, selecting it as active in the registry, and - if `--open` was supplied - attempting to open the transcript in the default browser. Do not write a phase contribution.

## Transaction

`(collab init)` is a nine-effect atomic operation. If any effect fails before the final registry/artifact commit, no registry or artifact write occurs.

| # | Effect | Rollback expectation |
|---|--------|----------------------|
| 1 | Validate flags - strict parsing; unknown flags and trailing positionals rejected | Abort before any write |
| 2 | Normalize title - title-case, acronym preservation, whitespace collapse | Abort before any write |
| 3 | Resolve local date and derive slug | Abort before any write |
| 4 | Assign sequence number - next from insertion order; never reused after hard delete | Abort before any write |
| 5 | Register moderator participant from the active harness `agentId` | Abort before any write |
| 6 | Resolve `workRepo` from `--work-repo` or the enclosing git work tree | Abort before any write |
| 7 | Apply reviewer metadata when `--reviewer` is supplied | Abort before any write |
| 8 | Seed reviewer-backed verification state as `rounds=0`, `subState="participant"`, and `participants={}` | Abort before any write |
| 9 | Atomic registry/artifact replacement - append collab entry, write transcript, write contribution store, set `activeCollabId` | All-or-nothing; partial writes roll back |

After the atomic write, `--open` issues a non-atomic browser launch. Opener failure is reported and does not affect the created collab record.

## Notes

- **Parameters:** `"<name>"` - required title text; all non-flag tokens after `init` belong to this value. `--agent-id <agentId>` - required helper flag supplied by the route from the active runtime harness. `--reviewer <role>` - optional role key; writes `reviewerRole`, `reviewerMode`, and `reviewerOptionalPhases` and initializes reviewer-backed verification. `--work-repo <path>` - optional absolute path to the project git work tree. `--open` - optional boolean flag; no value accepted.
- **Helper contract:** `commands/collab/engine/registry.py init` is canonical for the subcommand name, required `--agent-id <agentId>` flag, optional `--reviewer <role>` flag, optional `--work-repo <path>` flag, optional `--open` flag, unknown flag output (`unknown flag: <token>`), unknown trailing positional output (`unknown positional argument: <token>`), and first output token (`records/`).
- **Reviewer-backed verification:** Reviewer-backed collabs always begin verification with participant verification active. The registry stores `verification = { rounds: 0, subState: "participant", participants: {} }`; there is no production bypass flag and no workflow-terminal selector.
- **Force flag:** `--force` is ineligible for this route per [platform/standards/command-argument.md](../../../platform/standards/command-argument.md). The helper guards against duplicate records and registry corruption; forcing these writes would create state that other helpers assume cannot exist.
- **Moderator auto-join:** Successful init registers the moderator role automatically by using the corresponding JSON role file and the same participant row format used by `(collab join)`. The Agent column is populated from `--agent-id <agentId>`.
- **Registry side effect:** Successful init appends one collab entry to the resolved `registry.json`, includes the moderator role in `participants` and `turnOrder`, records `createdAt`, persists `workRepo`, and sets `activeCollabId` to the new collab id. The transcript path is mirrored in `transcriptPath`.
- **Slug derivation:** Per [init-helper-spec](../../../commands/collab/reference/init-helper-spec.md), the helper lowercases the normalized title, replaces every run of non-alphanumeric characters with one hyphen, and trims leading/trailing hyphens.
- **id and filename format:** `id` is `YYYY-MM-DD-<slug>`; `transcriptPath` is `records/YYYY-MM-DD-<slug>.md`. The contribution store shares the same stem: `records/YYYY-MM-DD-<slug>-contributions.json`.
- **Pending reviewer:** When `--reviewer <role>` is supplied but that role is not yet in `participants`, the transcript Reviewer section marks the role as `(pending)`. The pending state is derived from registry state.
- **Non-git init:** When the `.collab.json` marker directory is not inside any git work tree, `workRepo` falls back to the framework checkout. Git enforcement is deferred to execution and seal time.
- **Post-state resume signal:** After `init` completes, the new collab is active in the registry. Any agent joining the collab must run `commands/collab/engine/registry.py speak-state --resume <target> <role>` before writing a contribution.
- **Terminal suite owner authoring:** When `reviewerRole` is set, the terminal full-suite Action Plan item must be labeled `**<reviewer>:** full-suite` to identify the reviewer as the terminal suite owner for `Completion.execution`. That assignment does not make the full suite part of `Completion.verification`.
- **Lifecycle transcript template:** `records/<id>.md` uses the lifecycle transcript shape at init, with a managed header and empty phase sections. `commands/collab/engine/transcript_render.py` (`render_initial_transcript`) is the format authority.

```route-flag
flag: force
eligibility: ineligible
guard-class: registry-integrity
ineligibility-reason: The route guards against duplicate records and registry corruption; forcing these writes would create state other helpers assume cannot exist.
```

```route-arg
dispatch: (collab init "<name>" [--reviewer <role>] [--work-repo <path>] [--open])
param: name=<name>; required=required; placeholder=<name>; class=type; rule=title text
param: name=--reviewer; required=optional; placeholder=<role>; class=dynamic; source=platform/tooling/roles.py roles; default=none
param: name=--work-repo; required=optional; placeholder=<path>; class=type; rule=absolute path to project git work tree; default=none
param: name=--open; required=optional; placeholder=--open; class=type; rule=boolean flag; default=none
```
