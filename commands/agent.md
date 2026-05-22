# /agent

Route multi-agent scaffold workflows through one public slash command.

## Trigger

**Slash:** `/agent`
**Signature:** `/agent <install | patch | upgrade>`
**Prose dispatch:** `(agent install ...)`, `(agent patch ...)`, `(agent upgrade ...)` — prose routing hint; not a terminal command.
**Search phrases:** agent install, agent patch, agent upgrade, bootstrap multi-agent setup, install multi-agent scaffold, patch repository for multi-agent, upgrade multi-agent scaffold

## Steps

1. Resolve `<install | patch | upgrade>` from the first token after `/agent`. If missing or invalid, **ABORT** naming the token received and emit the allowed route set: `install`, `patch`, `upgrade`.
2. Load `../_functions/agent/<route>.md` from the command config root.
3. Execute that route with the remaining user input and attachments.

## Notes

- **Route:** `install` -> [_functions/agent/install](../_functions/agent/install.md); `patch` -> [_functions/agent/patch](../_functions/agent/patch.md); `upgrade` -> [_functions/agent/upgrade](../_functions/agent/upgrade.md).
- **Parameters:** `<install | patch | upgrade>` — required route selector.
- **Examples:** `/agent install`, `/agent patch`, `/agent upgrade`.
- **Boundary:** `/agent install` copies scaffold templates from `~/.cursor/_templates/` into the repo root only. `/agent patch` edits `REPOSITORY.md` only. `/agent upgrade` compares installed scaffold files against the current templates and, after user confirmation, writes the accepted set all-or-nothing. Each command does not write to `~/.cursor/` or modify agent settings JSON.
