# Agent lifecycle timing

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab lifecycle timing, collab compact timing, collab subagent timing

## Steps

1. Read this document when deciding when to run lifecycle commands during a collab session.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The document specifies when to run lifecycle commands during a collab session. The document supplements [`agent-effort.md`](agent-effort.md) (effort levels) and [`agent-model.md`](agent-model.md) (join-time model and harness).

## `/compact`

Run after each **Discussion** `(collab speak)` contribution, before issuing the next collab command. The pattern is:

```
(collab speak) → /compact → wait for turn → (collab speak)
```

Also run before preparing a **Handoff** subagent — compact the parent session before spawning.

Do not run mid-turn. The transcript and registry persist on disk; compaction shrinks local context without losing collab state.

## `/effort`

Run `/effort` (harness slash command, not a collab route) before every speak turn. Check the `EFFORT:` advisory emitted by the helper (`commands/collab/engine/registry.py effort-state <target> <role>`) and set the harness effort level to match before writing the contribution.

Effort changes per phase per role as defined in `agent-effort.md` and `agent-model.md`. The join-time model does not change; only effort adjusts between phases.

## `(collab join)`

`(collab join)` is metadata-only admission work. `(collab join)` does not produce a phase contribution and runs at `low` for any role. The per-phase effort matrix governs speak turns only.

## `Completion.verification`

`Completion.verification` has two ordered sub-phases:

1. **`verification.seal`** — Reviewer calls `(collab seal verification)`; mechanical execution-truth check. Run at the current effort level for `Completion.verification` (`xhigh` for the reviewer role).
2. **`verification.assessment`** — Reviewer evaluates goal achievement and records a verdict. Opens after a successful seal and re-enters when the seal becomes stale.

## Subagents

Subagents belong in the **Completion** phase only, after Handoff has declared disjoint write scopes and validation commands. Spawning is helper-driven (`execute-spawn`) under `(collab run plan)`. Subagents never author a collab turn and must not mutate registry or transcript state independently.

## `/clear`

Run only at the **close → init** boundary — after a collab closes and before starting a new one. Not safe mid-collab; it resets session state.

## `/exit`

A harness-level session command. The command does not affect collab state; the transcript and registry persist on disk after exit. Use when leaving the session entirely, not as a collab lifecycle step.

## Token visibility

Token consumption during collab participation is visible through harness commands only — the registry has no telemetry channel to model-counted or agent-counted totals.

**Codex:** Run `/status` to get a snapshot of current context usage. Record the value at collab join and again after each collab command. The per-command delta and collab-total delta are user-measured percentages relative to the context window.

**Claude Code:** Run `/usage`. Same snapshot-and-diff approach: record at join, after each command, compare.

**Snapshot-and-diff recipe:**

1. Run `/status` (Codex) or `/usage` (Claude Code) immediately after `(collab join)`.
2. After each `(collab speak)` or other collab command, take another snapshot.
3. Report `command delta = snapshot_after − snapshot_before` and `collab delta = snapshot_current − snapshot_at_join` as user-measured context percentages.

These values are harness-scoped and user-measured. They are not collab-authoritative: the registry does not record them, and agents cannot derive them without user action.

**Automatic per-command `TOKENS:` emission is out of scope for this repo.** No process authored here sits in the per-command execution loop with access to token counts. Any automatic path terminates in code this repo does not own (harness internals) or in agent self-report (a fabrication risk). Automatic token emission is a harness concern per Invariant #7. If a future harness wrapper supplies telemetry, the advisory shape must include `denominator=context-window` and `source=harness|unavailable` provenance; a bare percentage implying live precision is rejected.
