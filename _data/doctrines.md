# Platform Doctrines

Standing platform rules that apply across all collabs and implementation work. These are not one-off collab decisions; they persist until a future moderator explicitly revises them in a new collab record.

## Hard-cutover no-legacy rule

**Rule:** When a name is wrong, remove it at source. Do not retain legacy aliases, deprecation windows, or backwards-compatibility shims.

**Corollary:** A renaming patch must update all callers, tests, docs, and generated references atomically. Retaining the old name alongside the new name in any tracked file is a policy violation.

**Exception scope:** A future moderator may explicitly scope an exception for a specific migration by documenting it in a collab record. That exception applies only to the explicitly named artifact and does not weaken this rule for other work.

**Origin:** mod-4, collab #34 (2026-05-22). Promoted from a per-collab decision to a standing doctrine per moderator instruction.
