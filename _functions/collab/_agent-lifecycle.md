# Agent lifecycle timing

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** collab lifecycle timing, collab compact timing, collab subagent timing

## Steps

1. Read this document when deciding when to run lifecycle commands during a collab session.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

This document specifies when to run lifecycle commands during a collab session. It supplements [`_agent-effort.md`](_agent-effort.md) (effort levels) and [`_agent-model.md`](_agent-model.md) (join-time model and harness).

## `/compact`

Run after each **Discussion** `(collab speak)` contribution, before issuing the next collab command. The pattern is:

```
(collab speak) → /compact → wait for turn → (collab speak)
```

Also run before preparing a **Handoff** subagent — compact the parent session before spawning.

Do not run mid-turn. The transcript and registry persist on disk; compaction shrinks local context without losing collab state.

## `/effort`

Run `/effort` (harness slash command, not a collab route) before every speak turn. Check the `EFFORT:` advisory emitted by the helper (`tools/collab/registry.py effort-state <target> <role>`) and set the harness effort level to match before writing the contribution.

Effort changes per phase per role as defined in `_agent-effort.md` and `_agent-model.md`. The join-time model does not change; only effort adjusts between phases.

## `/collab join`

`/collab join` is metadata-only admission work. It does not produce a phase contribution and runs at `low` for any role. The per-phase effort matrix governs speak turns only.

## `Completion.verification`

`Completion.verification` has two ordered sub-phases:

1. **`verification.seal`** — Reviewer calls `/collab seal verification`; mechanical execution-truth check. Run at the current effort level for `Completion.verification` (`xhigh` for the reviewer role).
2. **`verification.assessment`** — Reviewer evaluates goal achievement and records a verdict. Opens after a successful seal; also re-enters when the seal becomes stale or a cap-exit is recorded. Assessment is budget-exempt when a cap-exit trigger opened it.

## Subagents

Subagents belong in the **Completion** phase only, after Handoff has declared disjoint write scopes and validation commands. Spawning is helper-driven (`execute-spawn`) under `/collab run plan`. Subagents never author a collab turn and must not mutate registry or transcript state independently.

## `/clear`

Run only at the **close → init** boundary — after a collab closes and before starting a new one. Not safe mid-collab; it resets session state.

## `/exit`

A harness-level session command. It does not affect collab state; the transcript and registry persist on disk after exit. Use when leaving the session entirely, not as a collab lifecycle step.
