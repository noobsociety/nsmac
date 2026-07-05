# Platform doctrines

Standing platform rules that apply across all collabs and implementation work. These are not one-off collab decisions; they remain in force until a moderator explicitly revises them in a new collab record.

## Present-state source rule

**Rule:** Tracked source expresses present state only. Git history owns past outcomes; external work queues own possible future work. Do not carry versioning plans, changelog accounting, roadmap promises, old snapshots, or quota plans in source.

**Corollary:** Functional gates may report live measurements, but tracked source must not encode prior run snapshots or future quotas. Remove outcome residue instead of reconciling it.

**Exception scope:** Tracked source has no sanctioned past-record carrier. Closed collab records live in the user-scope collab state root, not in tracked source. No past- or future-outcome residue is exempt.

**Enforcement scope.** Mechanical gates certify a bounded set, not blanket present-tense purity. `platform/tooling/audit-present-state.py` flags the residue categories named in the Corollary; `platform/tooling/audit-deleted-path-references.py` and `platform/tooling/audit-retired-systems.py` reject removed paths and retired-system artifacts by identity and extension. No gate adjudicates prose voice — separating exempt historical narration (a closed collab or retired mechanism recalled as past fact) from a genuine present-state violation is a reviewer reading, governed by the closed-collab provenance carve-out in `platform/standards/doctrine.md`. A green audit certifies the enumerated shapes and the artifact identities, not that every sentence reads present-tense.

## Hard-cutover no-legacy rule

**Rule:** When a name is wrong, remove it at source. Do not retain legacy aliases, deprecation windows, or backwards-compatibility shims.

**Corollary:** A renaming patch must update all callers, tests, docs, and generated references atomically. Retaining the old name alongside the new name in any tracked file is a policy violation.

**Exception scope:** A moderator may explicitly scope an exception for a specific migration by documenting it in a collab record. That exception applies only to the explicitly named artifact and does not weaken this rule for other work.

**Origin:** mod-4, collab #34 (2026-05-22). The rule was promoted from a per-collab decision to a standing doctrine per moderator instruction.
