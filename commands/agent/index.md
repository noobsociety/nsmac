# (agent)

Route multi-agent scaffold workflows through one namespace.

## Trigger

**Dispatch:** `(agent <install | patch | upgrade>)` — routing-only command form; not a shell command.
**Search phrases:** agent install, agent patch, agent upgrade, bootstrap multi-agent setup, install multi-agent scaffold, patch repository for multi-agent, upgrade multi-agent scaffold

## Steps

1. Resolve `<install | patch | upgrade>` from the first token after `(agent)`. If missing or invalid, **ABORT** naming the token received and emit the allowed route set: `install`, `patch`, `upgrade`.
2. Load `<route>/index.md` from this namespace directory.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `install` -> [agent/install](install/index.md); `patch` -> [agent/patch](patch/index.md); `upgrade` -> [agent/upgrade](upgrade/index.md).
- **Parameters:** `<install | patch | upgrade>` — required route selector.
- **Examples:** `(agent install)`, `(agent patch)`, `(agent upgrade)`.
- **Boundary:** `(agent install)` copies scaffold templates from `~/.cursor/platform/templates/` into the repo root only. `(agent patch)` edits `REPOSITORY.md` only. `(agent upgrade)` compares installed scaffold files against the current templates and, after user confirmation, writes the accepted set all-or-nothing. Each command does not write to `~/.cursor/` or modify agent settings JSON.
