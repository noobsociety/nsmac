# (help)

Render the route playbook for the named command route so agents can look up dispatch syntax, parameters, and steps without exploring file trees.

## Trigger

**Dispatch:** `(help <route>)` — routing-only command form; not a shell command.
**Search phrases:** help route, show route playbook, display command help, route lookup, command reference

## Steps

1. Resolve `<route>` from the token(s) after `(help)`. **ABORT** if `<route>` is missing: `<route>` is required; e.g., `(help collab init)`, `(help collab run plan)`.
2. Derive the candidate path: map `<route>` to a file under `commands/` using the **Route path mapping** rule in **Notes**. If the resolved path does not exist or cannot be read, **ABORT**: route not found: `<route>`; valid routes are listed in `commands/commands.md`.
3. Display the file contents exactly as read. Stop.

## Notes

- **Parameters:** `<route>` — required; the command namespace and optional route name to display; e.g., `collab init`, `collab run plan`, `agent install`, `collab` (namespace-only).
- **Route path mapping:** A qualified multi-token route (e.g., `collab run plan`) maps `<namespace>` to the first token and `<route-path>` to the hyphenated remainder: `commands/<namespace>/<route-path>/index.md`. A single-token route (e.g., `collab`) resolves to the namespace router: `commands/<namespace>/index.md`. Multi-word route selectors always use the hyphenated form on disk — see `platform/standards/command-convention.md`.
- **No help schema:** This route renders existing route playbooks as-is. It does not maintain a separate help-content surface or duplicate content from the route files.

```route-arg
dispatch: (help <route>)
param: name=<route>; required=required; placeholder=<route>; class=type; rule=command namespace and optional route name
```
