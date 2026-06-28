# Schema evolution

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** schema evolution, field lifecycle, unknown fields preserved, field retirement, registry field classification

## Steps

1. Read this document when adding, renaming, or retiring a field in `registry.json` or in any helper-output JSON.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

The file is the canonical owner of registry field lifecycle rules. Both `registry.schema.json` (load-time validation) and any load-time validation note in `commands/collab/engine/registry.py` must link to this file rather than restating the rules inline.

### Field classification

**Known fields** are fields whose names and types are declared in `registry.schema.json`. A known field with the wrong type or an out-of-range value is **rejected** at load time; the helper exits with a structured error naming the field and constraint.

**Unknown fields** are fields not declared in `registry.schema.json`. An unknown field at any schema depth — top-level, inside a collab entry, or inside a nested lifecycle object — is **preserved unchanged** through every mutating operation. Unknown fields must survive a load-validate-write cycle without modification. The rule is the "unknown fields preserved" contract; breaking the rule is a breaking schema change regardless of field name.

The preserved-unknown rule applies to:
- Top-level registry fields other than those declared in the schema
- Fields inside a collab entry object
- Fields inside nested lifecycle objects (e.g., `execution`, `verdict`, `handoff`)

### Malformed-rejected / unknown-preserved rule

One rule, two cases:

| Field type | Behavior |
|---|---|
| Known, wrong type or invalid value | **Rejected** at load time |
| Unknown (not in schema) | **Preserved** through load-validate-write |

The implementation contract: `registry.schema.json` validation must be applied on load, before any mutation, and the schema validator must not strip unknown fields. A closed-schema validator that silently drops unknown keys violates the preserved-unknown contract.

### Required round-trip test shape

Every commit that adds or modifies schema validation must include same-commit tests covering both cases:

1. **Malformed-known rejection:** Inject a wrong type into a declared known field (e.g., `revision: "string"` instead of an integer). Assert that the helper exits with a non-zero status and names the field.
2. **Unknown-field round-trip:** Inject an unknown field at each of the three depths (top-level, collab entry, nested lifecycle). Run a mutating helper operation. Assert the unknown field is present and unchanged in the output registry.

Tests for case 2 must cover all three depths in the same commit; partial coverage (top-level only) does not satisfy the round-trip test requirement.

### Counter lifecycle

The registry uses two distinct counters with non-overlapping roles:

**`revision`** — write-guard counter. Stored as the top-level `revision` field in `registry.json`. Incremented by `bump_registry_revision()` on every registry write. The stale-write guard (`speak-render`, `execute`) reads this field to detect concurrent writes. This field must not be renamed unless the rename is atomic across: the stored field name, every read site in `commands/collab/engine/registry.py`, and all helper-output labels that reference it.

**`registryRevision`** — helper-output presentation label. This name appears in `speak-state` and similar helper JSON output as a human-readable label sourced from the `revision` field (`registry.py:229`). The label is not an independently stored counter. The label may be retired or renamed in a future collab without touching the stored `revision` field.

**`eventIndex`** — log sequence counter. A new counter to be introduced with the append-only revision writer (`<state-root>/revisions/`). Increments only on explicit registry log events. Header rewrites, transcript rendering, and state repair must not increment `eventIndex` unless they deliberately emit a registry log event.

### Field-retirement records

| Field | Last known value | Retired in | Retirement reason |
|---|---|---|---|
| `registryRevision` (top-level in `registry.json`) | `1552` | collab #52 `collab-state-observability` | Vestigial. The `revision` field became the canonical write-guard counter; `registryRevision` was never updated after the rename and no read path consulted it. |

**Seal-evidence sub-key `registryRevision`:** The seal-evidence object uses `registryRevision` as a sub-key (`registry.py:1238`, `:5560`) to record the registry revision at seal time. The sub-key is sourced from the `revision` field (not from the retired top-level `registryRevision`). The sub-key is retained as a named evidence anchor; its source must remain `revision`.
