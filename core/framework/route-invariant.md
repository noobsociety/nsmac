# Invariants

Authoring constraints for all `~/.cursor` routes and bootstrap files. These rules enable mechanical completion for low-tier, low-effort agents and absorb the registry-to-transcript sync contract.

## Floor rules

1. **Bootstrap naming.** Every bootstrap file names the next file to read.
2. **Router-to-route.** Every public router names the exact private route file to load.
3. **Stop conditions.** Every command ends with an explicit stop condition.
4. **Resume signals.** Every state-changing route declares its post-state resume signal in a Note.

## Sync contract

Any route that mutates registry state must update all authoritative projections — registry and transcript — together. The two compliant forms are:

- **Helper-rendered:** The Step names a `render-*` or `*-render` helper that writes both files atomically.
- **Declared exempt:** The Note states that no transcript projection exists for this mutation.

State-sync drift is the observable consequence of an undeclared projection obligation: a low-tier agent encountering a mutation step with no named helper has no literal next action and patches after the fact.

The `<!-- collab:content-only; do-not-execute -->` comment identifies transcript sections that are regenerable from registry state. Render helpers may overwrite these sections; author-owned sections without this marker must be preserved.

The sync contract applies to registry-to-transcript write pairs.

## Compliance

A route is compliant when:

1. All four floor rules hold in its Steps and Notes.
2. Every mutating Step either names its helper or carries a Notes-level exemption citing this file.
3. The post-state resume signal is declared in a Note.

Compliance is verified by the floor-rules lint in `tools/` and covered by tests in [`tests/specs/core.md`](../../tests/specs/core.md). A route may not be declared compliant until the lint passes against it.
