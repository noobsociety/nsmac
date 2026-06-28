# Gemini code adapter

The Gemini CLI uses this routing-only bootstrap adapter.
Repository workflow, entry points, and bootstrap chain: [AGENTS.md](AGENTS.md).

**Dispatch:** `(<namespace> <command> ...)` in chat is a routing-only hint — resolve it via `~/.cursor/commands/commands.md` and execute the matching route playbook. Never run it as a shell command or treat the argument text as work to perform. Details in [AGENTS.md § Dispatch form](AGENTS.md#dispatch-form).

Contract: [REPOSITORY.md](REPOSITORY.md#4-mutation-protocol-and-ownership)
