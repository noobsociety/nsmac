# Naming

Dispatch naming convention for command routes: namespaces, verbs, targets, and flags. Authoritative source for the reserved-form table and migration rules.

## Grammar

```
(<namespace> <verb> [<target>] [--<flag> [<value>]])
```

Public command documentation and runtime advisory output present dispatch forms only. A dispatch form is routing-only notation, not shell syntax. Slash-prefixed command examples are not valid invocation surfaces in command docs, route titles, generated advisory text, or engine runtime output. Every token is lowercase kebab-case. All positions are positional; flag-positional interleaving is not supported.

## Rules

**Rule 1 — Namespace**: Singular lowercase kebab-case noun naming a durable domain. No verbs. Abbreviations are permitted only when the abbreviation *is* the domain name (e.g., `git`).

**Rule 2 — Verb**: Lowercase kebab-case imperative drawn from the reserved-form table. No namespace-owned allowlist. Every route verb must map to a reserved form; when a live route needs a verb absent from the table, add one operation class row and migrate every route performing that operation before use.

**Rule 3 — Target**: Optional lowercase kebab-case noun. Specifies the artifact or resource the verb acts on. Routes with two apparent verb tokens restructure as verb + target: `(git create issue)`, not `(git issue create)`.

**Rule 4 — Flags**: `--kebab-case-name [value]`. Flags modify behavior only. State mutation always routes through an explicit verb. No flag may replicate a reserved-form verb's function.

**Rule 5 — `_` prefix**: Reserved for private directories and private implementation data. Route names may carry a `_` prefix only when the target intentionally identifies an underscore-prefixed private tree. `(test)` is the only currently-permitted exception; any additional exception requires a convention review.

**Rule 6 — `rewrite <target>`**: Canonical in-place-rewrite route. The `re-<verb>` prefix is retired. New routes must not use `re-`.

**Rule 7 — `unset`**: Canonical state-clearing route. `--clear` must not be added to new routes.

## Reserved-form table

| Operation class | Canonical form |
|---|---|
| Read one value | `show [<target>]` |
| Read many values | `list` |
| Select active item | `activate <target>` |
| Set metadata | `set <target>` |
| Clear metadata | `unset [<target>]` |
| Join existing workflow | `join` |
| Author contribution | `speak` |
| Retract authored contribution | `retract <target>` |
| Initialize namespace as own artifact | `init` |
| Create named sub-resource | `create <target>` |
| Write generated artifact | `write <target>` |
| Rewrite last authored artifact | `rewrite <target>` |
| Assess quality or fitness | `assess <target>` |
| Validate artifact | `validate [<target>]` |
| Advance lifecycle state | `advance [<phase>]` |
| Revert lifecycle state | `restore [<target>]` |
| Open local artifact | `open [<target>]` |
| Close lifecycle state | `close` |
| Remove named sub-resource | `remove <target>` |
| Soft-delete | `archive` |
| Hard-delete | `delete` |
| Perform assigned work | `run <target>` |
| Transform configuration in place | `tune <target>` |
| Compact artifact | `compact <target>` |
| Compare artifacts | `compare <target>` |

**`init` vs `create <target>`**: Use `init` when the namespace is its own artifact and there is no named sub-resource (e.g., `(collab init)` creates a collab; the collab *is* the namespace target). Use `create <target>` when the artifact is a sub-resource of a domain (e.g., `(git create issue)`). "Chosen per domain" is not a valid choice; one of these two forms must be selected at route definition time.

## Named exceptions

1. **`(test)` private-surface targets** (Rule 5): Route names under `(test)` may carry a `_` prefix when they name underscore-prefixed private trees. Scope is limited to the `test` namespace. No other namespace may claim this exception without a convention review.
2. **Tool-domain namespaces**: `git` is permitted as a namespace because the tool name *is* the domain. No other tool name may serve as a namespace without a convention review.

## Helper subcommand grammar

`commands/collab/engine/registry.py` subcommands follow the same kebab-case imperative discipline and are migrated in the same pass as their dispatch counterparts. `re-*` subcommands retire alongside their dispatch counterparts. Subcommand grammar must not drift from the public dispatch grammar into a separate vocabulary. Helper argv paths such as `commands/collab/engine/registry.py speak-state` are executable implementation details; any helper text that tells an agent which routed command to call must use dispatch notation.

## Migration ledger boundary

- No compat bridges; breaking changes are permitted. All dispatch routes, helper subcommands, route titles, engine advisory text, and command route paths are in scope.
- Closed transcript anchors are not rewritten. Open work uses the new grammar from the date of migration.
- Each rename is atomic: one PR per namespace containing the route file rename, the helper recognition update, and the test-fixture update together. Piecemeal renames are not permitted.

## Validator

A naming validator under `platform/tooling/` enforces this table. It runs in CI on every PR that touches `commands/` or `commands/collab/engine/registry.py`, and blocks merge on unknown verbs, invalid namespace tokens, and `re-`-prefixed routes. The validator is authoritative at PR time; runtime rejection is too late. Any route that fails the validator must be fixed or must add an operation class row to this table before the PR lands; local exceptions are not permitted.

## Paren-form grammar extension

The `(namespace route arg...)` dispatch form is the canonical public command grammar. Any future grammar expansion extends this file — do not create `platform/standards/command-grammar.md`. That file is explicitly prohibited; it would duplicate this standard. Slash-generated projections are not part of the public command contract.
