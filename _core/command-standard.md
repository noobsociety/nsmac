# Command standard

The command standard defines how public slash files under `commands/` delegate to private function playbooks under `_functions/` in `COMMAND_CONFIG_ROOT`. Every playbook follows the [style guide](style-guide.md) and the **Command** (`.md`) template in [document standard](document-standard.md#command-md); this file owns the extended contract: public slash routing, private functions, heading order, catalog duties, link hygiene, harness exceptions, and layout rules. Signal, one-action-per-step discipline, and the **250-line** budget live in [context engineering](context-management.md).

Contract: [document-standard.md](document-standard.md#command-md), [style-guide.md](style-guide.md), [context-management.md](context-management.md)

## Layering

- **Minimal template** — opening sentence plus `## Trigger`, `## Steps`, `## Notes` in [document standard](document-standard.md#command-md).
- **This standard** — operational details below, including namespace routing, private functions, and catalog synchronization.
- **Voice** — neutral imperative for machine steps; [author voice](author-voice.md) only when the playbook deliberately uses personal register.

## File naming and invocation

- Public slash files use `commands/{namespace}.md` and expose `/namespace`.
- Private route functions use `_functions/{namespace}/{route}.md` and document the effective invocation as `/namespace route`.
- Do not place route files under `commands/{namespace}/`; the runtime may expose them as standalone slashes such as `/assess`.
- One bounded workflow lives in each private function. Public namespace files only resolve the route and delegate remaining input.

## Document shape

### Title and opening line

- After fenced-code removal, exactly one column-0 `# ` line that is not `## `.
- Public namespace files use `# /<namespace>`.
- Private function files use `# /<namespace> <route>`, except `_functions/test/run.md` which uses `# /test` because the target selector is the first argument.
- `_tests/*.md` harness files use their own `#` title line required by the harness spec.
- The first body paragraph is one declarative sentence that starts with the action verb and states purpose and when to open the playbook, per [document standard](document-standard.md). Only `/quality assess` functions may use the bold-acronym-first opening described there.

### Required sections

Include `## Trigger`, `## Steps`, then `## Notes`, in that order, each exactly once. Keep **Steps** as a short numbered list; put routing tables, long contracts, and edge cases in **Notes**. Harness files under `_tests/` follow their own heading contract.

### Trigger

The `## Trigger` block declares three labeled sections in this order: **Slash**, **Prose dispatch**, **Search phrases**. Each section carries distinct dispatch semantics; omitting a section or placing them out of order is a structural conformance failure.

**Slash** — the only terminal-invocable form; matches exactly as written. Lead with `**Slash:** /<namespace>` for public namespace files or `**Slash:** /<namespace> <route>` for private functions. Required route choices and positional arguments are declared in the **Signature** line directly after **Slash**.

**Prose dispatch** — the routing-only `(<namespace> <route> <arg>...)` notation for routed agents. These agents follow the bootstrap chain (`CLAUDE.md` / `AGENTS.md` -> `~/.commands/commands.md`) and then execute the corresponding slash command. It is not terminal-executable; Slash users invoke the slash form directly. Slash entries and prose-dispatch entries must still be unique across routes and must not appear under Search phrases. The `/test` router and `_functions/test/run.md` may mirror the same routed form because they describe one command surface and one implementation playbook, not two independently exposed routes.

**Search phrases** — discovery aids only; explicitly non-invocable; agents must not dispatch on a phrase match alone. For multi-mode functions, use a labeled group per mode: `**Search phrases (mode):**`.

**Argument quoting:** Multi-word free-text arguments are valid only when double-quoted. Single-quoted wrappers are rejected with the named abort: `invalid quote: single quotes are not a valid wrapper; use double quotes`.

**Dequoted-value contract:** Routes receive the dequoted string, not the raw quoted token. This is stated once here; function files must not restate it.

**Trust-model scope:** Dispatch enforces structural conformance of spec files — presence and order of the three sections, quote shape on declared invocation forms. Correctness of invocation intent is honor-system, comparable to `agentId` in `join.md`: the validator names what it checks; it does not claim to verify intent.

**Helper-boundary exemption:** `tools/collab/registry.py` is invoked by argv, not by phrase or shape match, and is intentionally outside the 1:1 dispatch contract. Trigger-section and quote-shape rules do not apply to helper argv calls.

**Historical transcripts:** The dispatch rule applies to new invocations only. Phrases inside transcript content — collapsed `<details>` blocks, phase section prose — are inert and must not be treated as dispatch keys on context restoration or replay.

### Steps

- Numbered list; one visible action per item; imperative mood.
- Public namespace files resolve the first token as a route, load `../_functions/{namespace}/<route>.md` (or equivalent namespace mapping), and execute that function with remaining input and attachments.
- Private function files perform the actual workflow.
- When another file is authoritative, name it by path using allowed relative links.

### Parameters

Treat every command as a function. Declare the routing signature in **Trigger** and detail each parameter in **Notes**.

**Notation:**

- `<name>` — required positional argument; the command **ABORT**s if missing after resolution.
- `<a | b>` — required choice; the command **ABORT**s if neither is provided.
- `[<name>]` — optional positional argument; when omitted, the route uses the default stated in **Notes** or the route-specific resolution rule.
- `[--flag <value>]` — optional flag and value pair; when omitted, the route uses the default stated in **Notes** or leaves that behavior disabled.

Commands either take no arguments or explicitly mark optional arguments with square brackets. Optional target arguments default only when the route states the omitted-target behavior in **Notes**.

**Trigger — Signature line:** Add `**Signature:**` directly after `**Slash:**` showing the full invocation form using the notation above. Namespace signatures usually stop at the route selector; private functions own route-specific remaining arguments.

**Notes — Parameters block:** When one or more parameters exist, add `**Parameters:**` as the first bullet in `## Notes`, unless a **Route** block is present. Route-bearing public commands place **Route** first and **Parameters** second.

**Multi-stage functions:** A private function may use a stage selector when one bounded workflow has stages with different arity. Its **Signature** line shows the required stage selector only, and `## Notes` must include **Stage signatures:** with one concrete invocation per stage. Each stage must state its own required arguments or explicitly state that no arguments are accepted. This exception belongs only to private functions; public namespace files still resolve one route selector.

**Resolution rule:** A typed positional argument and an attached file are equivalent for any parameter that accepts file content. Multi-file commands consume attachments in order.

**Required arguments:** If any required argument is missing after resolution, the command must **ABORT** immediately with a clear message naming the missing argument.

## New command template

**Public namespace command:**

```markdown
# /{namespace}

Route {domain} workflows through one public slash so related commands stay grouped.

## Trigger

**Slash:** `/{namespace}`
**Signature:** `/{namespace} <route-a | route-b>`
**Prose dispatch:** `({namespace} route-a ...)` — prose routing hint; not a terminal command.
**Search phrases:** <natural-language alias>, <alias>

## Steps

1. Resolve `<route>` from the first token after `/{namespace}`. If missing or invalid, **ABORT** naming the token received.
2. Load `../_functions/{namespace}/<route>.md` from the command config root.
3. Execute that function with the remaining user input and attachments.

## Notes

- **Route:** `route-a` -> `../_functions/{namespace}/route-a.md`; `route-b` -> `../_functions/{namespace}/route-b.md`.
- **Parameters:** `<route-a | route-b>` — required route selector.
```

**Private function:**

```markdown
# /{namespace} {route}

One sentence — purpose of the route and when to use it.

## Trigger

**Slash:** `/{namespace} {route}`
**Signature:** `/{namespace} {route} <arg1>`
**Prose dispatch:** `({namespace} {route} ...)` — prose routing hint; not a terminal command.
**Search phrases:** <natural-language alias>, <alias>

## Steps

1. Resolve `<arg1>` from the corresponding positional argument or attachment. **ABORT** if `<arg1>` is missing.
2. <Imperative action.>

## Notes

- **Parameters:** `<arg1>` — description (required).
- <Scope statement, safety stop, or dependency notice.>
```

## Catalog

- Keep exactly one index file named `commands.md` with slash `/commands`.
- The catalog table must include every public command under `commands/`, except `commands.md`.
- The catalog table must also list every private function used by a public route.
- Update the table and invocation notes when behavior or typing constraints change.
- Prefer a single source of truth: either the catalog’s invocation appendix or the playbook **Trigger**, not conflicting copies.

## Invariants at a glance

| Code | Standard rule | Invariant |
| --- | --- | --- |
| **P1** | Catalog | Public command and private function rosters match harness rosters exactly |
| **P2** | Link hygiene | No checkout-path literal leaks or forbidden parent links |
| **P3** | Layout and length | Each command/function `*.md` <= 250 lines |
| **P4** | Title and opening line | Exactly one H1 after fence strip |
| **P5** | Link hygiene | Links stay inside allowed command, function, role, core, and rules paths |
| **P6** | Required sections | `## Trigger` -> `## Steps` -> `## Notes` in order; each present once |
| **P7** | Catalog | `commands.md` links every public command and private function |
| **P8** | Title and opening line | H1 text is `# /<namespace>` or `# /<namespace> <route>` |
| **P9** | Trigger contract | Every command/function file except `commands.md` declares `**Slash:**`, `**Prose dispatch:**`, and `**Search phrases:**` as three sections in that order |
| **P10** | Signature and Notes contract | Signature placeholders, stage signatures, and Notes ordering stay consistent |
| **P11** | Self-containment | Required dependencies stay inside `commands/`, `_functions/`, `_roles/`, `_core/`, or explicit QA harness targets |

## Layout and length

- Do not add a manual `**Table of contents**` block under `commands/` or `_functions/`; headings carry navigation.
- Obey the **250-line** cap for `commands/*.md`, `_functions/**/*.md`, and command harness docs documented under **File size discipline** in [context engineering](context-management.md).

## Link hygiene

- Public command links may target sibling command files, `../_functions/**/*.md`, `../_core/*.md`, fragment-only anchors, and optional `https://` / `http://` context links.
- Private function links may target sibling `_functions/**/*.md`, `../../_core/*.md`, `../../_roles/*.json`, fragment-only anchors, and optional `https://` / `http://` context links.
- Required authority for command behavior may come only from public command files, private function files, shared role JSON under `_roles/`, core contracts under `_core/` or a `_functions/<ns>/_*.md` shared-dependency file within the same namespace.
- `_functions/test/run.md` may also require `~/.cursor/_tests/commands.md`, `~/.cursor/_tests/_functions.md`, `~/.cursor/_tests/_core.md`, `~/.cursor/_tests/_roles.md`, `~/.cursor/_tests/_settings.md`, `~/.cursor/_tests/_tests.md`, and `REPOSITORY.md` at repo root.
- External URLs are optional context only and never required authorities.

## QA cadence

- After any change under `commands/*.md` or `_functions/**/*.md`, verify compliance against this standard’s `P1–P11` contract.
- When a local harness exists, keep the harness roster synchronized with the catalog table in the same edit.

## Related documents

- [Style guide](style-guide.md) — voice, ambiguity, LLM-consumed rules, file naming.
- [Document standard](document-standard.md) — minimal command template and other shapes.
- [Context engineering](context-management.md) — phases, precision, context budget.
- [Author voice](author-voice.md) — register for personal-account exceptions.
