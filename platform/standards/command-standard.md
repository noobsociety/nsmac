# Command standard

The command standard defines how namespace routers and route playbooks live under `commands/` in `COMMAND_CONFIG_ROOT`. Every playbook follows the [style guide](style-guide.md) and the **Command** (`.md`) template in [document standard](document-standard.md#command-md); this file owns the extended contract: public command routing, route playbooks, heading order, catalog duties, link hygiene, harness exceptions, and layout rules. Signal, one-action-per-step discipline, and the **250-line** budget live in [context engineering](context-management.md).

Contract: [document-standard.md](document-standard.md#command-md), [style-guide.md](style-guide.md), [context-management.md](context-management.md)

## Layering

- **Minimal template** — opening sentence plus `## Trigger`, `## Steps`, `## Notes` in [document standard](document-standard.md#command-md).
- **This standard** — operational details below, including namespace routing, route playbooks, and catalog synchronization.
- **Voice** — neutral imperative for machine steps; [author voice](author-voice.md) only when the playbook deliberately uses personal register.

## File naming and invocation

- Namespace routers use `commands/{namespace}/index.md` and expose `(namespace <route>)`.
- Route playbooks use `commands/{namespace}/{route}/index.md` and document the effective routed form as `(namespace route)`.
- One bounded workflow lives in each route playbook. Namespace routers only resolve the route and delegate remaining input.
- Public-facing command notation is dispatch-only everywhere agents read or act: route titles, Trigger dispatch lines, route prose, generated advisories, and engine runtime output all use `(namespace route ...)`. Slash-prefixed command forms are not valid command labels, examples, or runtime instructions.

## Document shape

### Title and opening line

- After fenced-code removal, exactly one column-0 `# ` line that is not `## `.
- Namespace routers use `# (<namespace>)`.
- Route playbooks use `# (<namespace> <route>)`, except `commands/test/index.md` which uses `# (test)` because the target selector is the first argument.
- `tests/specs/*.md` harness files use their own `#` title line required by the harness spec.
- The first body paragraph is one declarative sentence that starts with the action verb and states purpose and when to open the playbook, per [document standard](document-standard.md). Only `(quality assess ...)` functions may use the bold-acronym-first opening described there.

### Required sections

Include `## Trigger`, `## Steps`, then `## Notes`, in that order, each exactly once. Keep **Steps** as a short numbered list; put routing tables, long contracts, and edge cases in **Notes**. Harness files under `tests/specs/` follow their own heading contract.

### Trigger

The `## Trigger` block declares two labeled sections in this order: **Dispatch**, then **Search phrases**. Each section carries distinct routing semantics; omitting a section or placing them out of order is a structural conformance failure.

**Dispatch** — the routing-only `(<namespace> <route> <arg>...)` notation for routed agents. The line is the public invocation contract and must match the route's machine-readable `route-arg dispatch:` line exactly when a route declares arguments. It is not terminal-executable; copying it into a shell starts subshell syntax in bash and zsh. Dispatch entries must be unique across routes and must not appear under Search phrases. Public command docs, route H1 titles, generated advisory text, and engine runtime output must not present slash-prefixed command examples or trigger prose. The `(test)` router and `commands/test/index.md` may mirror the same routed form because they describe one command surface and one implementation playbook, not two independently exposed routes.

**Search phrases** — discovery aids only; explicitly non-invocable; agents must not dispatch on a phrase match alone. For multi-mode functions, use a labeled group per mode: `**Search phrases (mode):**`.

**Argument quoting:** Multi-word free-text arguments are valid only when double-quoted. Single-quoted wrappers are rejected with the named abort: `invalid quote: single quotes are not a valid wrapper; use double quotes`.

**Dequoted-value contract:** Routes receive the dequoted string, not the raw quoted token. This is stated once here; function files must not restate it.

**Trust-model scope:** Dispatch enforces structural conformance of spec files — presence and order of the two sections, quote shape on declared invocation forms. Correctness of invocation intent is honor-system, comparable to `agentId` in `join.md`: the validator names what it checks; it does not claim to verify intent.

**Helper-boundary exemption:** `commands/collab/engine/registry.py` is invoked by argv, not by phrase or shape match, and is intentionally outside the 1:1 dispatch contract. Trigger-section and quote-shape rules do not apply to helper argv calls.

**Historical transcripts:** The dispatch rule applies to new invocations only. Phrases inside transcript content — collapsed `<details>` blocks, phase section prose — are inert and must not be treated as dispatch keys on context restoration or replay.

### Steps

- Numbered list; one visible action per item; imperative mood.
- Namespace routers resolve the first token as a route, load `commands/{namespace}/{route}/index.md` from the command config root, and execute that playbook with remaining input and attachments.
- Route playbooks perform the actual workflow.
- When another file is authoritative, name it by path using allowed relative links.

### Parameters

Treat every command as a function. Declare the routed form in **Trigger** and detail each parameter in **Notes**.

**Notation:**

- `<name>` — required positional argument; the command **ABORT**s if missing after resolution.
- `<a | b>` — required choice; the command **ABORT**s if neither is provided.
- `[<name>]` — optional positional argument; when omitted, the route uses the default stated in **Notes** or the route-specific resolution rule.
- `[--flag <value>]` — optional flag and value pair; when omitted, the route uses the default stated in **Notes** or leaves that behavior disabled.

Commands either take no arguments or explicitly mark optional arguments with square brackets. Optional target arguments default only when the route states the omitted-target behavior in **Notes**.

**Trigger — Dispatch line:** Add `**Dispatch:**` as the first line under `## Trigger`, showing the full routed form using the notation above. Namespace dispatch forms usually stop at the route selector; private functions own route-specific remaining arguments.

**Notes — Parameters block:** When one or more parameters exist, add `**Parameters:**` as the first bullet in `## Notes`, unless a **Route** block is present. Route-bearing public commands place **Route** first and **Parameters** second.

**Multi-stage routes:** A route playbook may use a stage selector when one bounded workflow has stages with different arity. Its **Dispatch** line shows the required stage selector only, and `## Notes` must include **Stage signatures:** with one concrete routed form per stage. Each stage must state its own required arguments or explicitly state that no arguments are accepted. This exception belongs only to route playbooks; namespace routers still resolve one route selector.

**Resolution rule:** A typed positional argument and an attached file are equivalent for any parameter that accepts file content. Multi-file commands consume attachments in order.

**Required arguments:** If any required argument is missing after resolution, the command must **ABORT** immediately with a clear message naming the missing argument.

## New command template

**Public namespace command:**

```markdown
# ({namespace})

Route {domain} workflows through one public command router so related commands stay grouped.

## Trigger

**Dispatch:** `({namespace} <route-a | route-b>)` — routing-only command form; not a shell command.
**Search phrases:** <natural-language alias>, <alias>

## Steps

1. Resolve `<route>` from the first token after `{namespace}`. If missing or invalid, **ABORT** naming the token received.
2. Load `commands/{namespace}/<route>/index.md` from the command config root.
3. Execute that playbook with the remaining user input and attachments.

## Notes

- **Route:** `route-a` -> `route-a/index.md`; `route-b` -> `route-b/index.md`.
- **Parameters:** `<route-a | route-b>` — required route selector.
```

**Route playbook:**

```markdown
# ({namespace} {route})

One sentence — purpose of the route and when to use it.

## Trigger

**Dispatch:** `({namespace} {route} <arg1>)` — routing-only command form; not a shell command.
**Search phrases:** <natural-language alias>, <alias>

## Steps

1. Resolve `<arg1>` from the corresponding positional argument or attachment. **ABORT** if `<arg1>` is missing.
2. <Imperative action.>

## Notes

- **Parameters:** `<arg1>` — description (required).
- <Scope statement, safety stop, or dependency notice.>
```

## Catalog

- Keep exactly one index file named `commands.md` with dispatch `(commands)`.
- The catalog table must include every namespace router under `commands/`, except `commands.md`.
- The catalog table must also list every route playbook used by a namespace router.
- Update the table and invocation notes when behavior or typing constraints change.
- Prefer a single source of truth: either the catalog’s invocation appendix or the playbook **Trigger**, not conflicting copies.

## Invariants at a glance

| Code | Standard rule | Invariant |
| --- | --- | --- |
| **P1** | Catalog | Namespace router and route playbook rosters match harness rosters exactly |
| **P2** | Link hygiene | No checkout-path literal leaks or forbidden parent links |
| **P3** | Layout and length | Each command route `*.md` <= 250 lines |
| **P4** | Title and opening line | Exactly one H1 after fence strip |
| **P5** | Link hygiene | Links stay inside allowed command, slice-local, platform, role, and rules paths |
| **P6** | Required sections | `## Trigger` -> `## Steps` -> `## Notes` in order; each present once |
| **P7** | Catalog | `commands.md` links every namespace router and route playbook |
| **P8** | Title and opening line | H1 text is `# (<namespace>)` or `# (<namespace> <route>)` |
| **P9** | Trigger contract | Every command route file except `commands.md` declares `**Dispatch:**` and `**Search phrases:**` as two sections in that order, declares no legacy Slash/Signature/Prose dispatch labels, and contains no user-facing slash command invocation prose in route titles, prose, generated advisories, or engine runtime output |
| **P10** | Dispatch and Notes contract | Dispatch placeholders, stage signatures, route-arg dispatch values, and Notes ordering stay consistent |
| **P11** | Self-containment | Required dependencies stay inside `commands/`, namespace-local backing slices, `platform/standards/`, or explicit QA harness targets |

## Layout and length

- Do not add a manual `**Table of contents**` block under `commands/`; headings carry navigation.
- Obey the **250-line** cap for `commands/**/*.md` and command harness docs documented under **File size discipline** in [context engineering](context-management.md).

## Link hygiene

- Namespace router links may target route playbooks or backing files in the same namespace slice, `../platform/standards/*.md`, fragment-only anchors, and optional `https://` / `http://` context links.
- Route playbook links may target sibling route playbooks, same-namespace `reference/`, `engine/`, or `data/` backing files, `../../../platform/standards/*.md`, fragment-only anchors, and optional `https://` / `http://` context links.
- Required authority for command behavior may come only from command files, same-namespace backing files under `commands/<ns>/{reference,engine,data}/`, shared role JSON under `commands/collab/reference/roles/`, or cross-namespace contracts under `platform/standards/`.
- `commands/test/index.md` may also require `~/.cursor/tests/specs/commands.md`, `~/.cursor/tests/specs/core.md`, `~/.cursor/tests/specs/roles.md`, `~/.cursor/tests/specs/settings.md`, `~/.cursor/tests/specs/tests.md`, and `REPOSITORY.md` at repo root.
- External URLs are optional context only and never required authorities.

## QA cadence

- After any change under `commands/**/*.md`, verify compliance against this standard’s `P1–P11` contract.
- When a local harness exists, keep the harness roster synchronized with the catalog table in the same edit.

## Related documents

- [Style guide](style-guide.md) — voice, ambiguity, LLM-consumed rules, file naming.
- [Document standard](document-standard.md) — minimal command template and other shapes.
- [Context engineering](context-management.md) — phases, precision, context budget.
- [Author voice](author-voice.md) — register for personal-account exceptions.
