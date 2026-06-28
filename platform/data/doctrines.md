# Platform doctrines

Standing platform rules that apply across all collabs and implementation work. These are not one-off collab decisions; they persist until a future moderator explicitly revises them in a new collab record.

## Present-state source rule

**Rule:** Tracked source expresses present state only. Git history owns past outcomes; external work queues own possible future work. Do not carry versioning plans, changelog accounting, roadmap promises, old snapshots, or quota plans in source.

**Corollary:** Functional gates may report live measurements, but tracked source must not encode prior run snapshots or future quotas. Remove outcome residue instead of reconciling it.

**Exception scope:** The sole sanctioned past-record carrier in tracked source is the `dp` (Deterministic Projector) backed tombstone — [`dp.json`](../../commands/collab/reference/roles/dp.json) and its carve-outs in [`role-standard.md`](../standards/role-standard.md) and [`invariants.md`](../../commands/collab/reference/invariants.md). The tombstone is load-bearing because closed collab record a13dba4c references `dp` in its participant roster, and the tombstone persists only until no registry record references `dp`. No other past- or future-outcome residue is exempt.

## Hard-cutover no-legacy rule

**Rule:** When a name is wrong, remove it at source. Do not retain legacy aliases, deprecation windows, or backwards-compatibility shims.

**Corollary:** A renaming patch must update all callers, tests, docs, and generated references atomically. Retaining the old name alongside the new name in any tracked file is a policy violation.

**Exception scope:** A future moderator may explicitly scope an exception for a specific migration by documenting it in a collab record. That exception applies only to the explicitly named artifact and does not weaken this rule for other work.

**Origin:** mod-4, collab #34 (2026-05-22). The rule was promoted from a per-collab decision to a standing doctrine per moderator instruction.
