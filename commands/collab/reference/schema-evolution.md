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

**`registryRevision`** — helper-output presentation label. This name appears in `speak-state` and similar helper JSON output as a human-readable label sourced from the `revision` field (`speak_commands.py:216`, `:224`). The label is not an independently stored counter; renaming or removing it does not require changing the stored `revision` field.

**`eventIndex`** — log sequence counter, backed by the append-only revision writer (`<state-root>/revisions/`). Increments only on explicit registry log events. Header rewrites, transcript rendering, and state repair must not increment `eventIndex` unless they deliberately emit a registry log event.

### Non-schema top-level fields

`registryRevision` is not a declared field in `registry.schema.json`. A registry that carries a top-level `registryRevision` key hits the unknown-field path: `retire_legacy_registry_fields()` (`registry_io.py:101`, invoked from `load_registry()` and `save_registry()`) strips a top-level `registryRevision` key on every load-save cycle, so this key does not persist. `revision` is the sole write-guard counter (Counter lifecycle, above).

**Seal-evidence sub-key `registryRevision`:** `validate_verdict_evidence()` (`seal_verification_logic.py:476-490`) accepts a verdict-evidence object with either a `revision` key or a `registryRevision` key, and rejects an object carrying both. `evidence_revision` in `seal_verification_render.py:511` reads `revision` first and falls back to `registryRevision` when only that key is present. This lets a verdict-evidence object recorded with either key render correctly; new writes use `revision` (`seal_verification_logic.py:783`, `:876`).

### Compatibility readers

Two reader-side paths accept an older shape alongside the current one:

- `LEGACY_EXPANDED_RE` and `LEGACY_HEADING_RE` (`transcript_readers.py:13-14`) match the bold-expanded (`**role —`) and heading (`### role —`) contribution-heading formats as a fallback in `contribution_roles()` (`transcript_readers.py:125`), alongside the current `<details><summary>role</summary>` shape. Both shapes appear in transcripts under `~/.collabs/nsmac/records/`.
- `ensure_legacy_revision_baselines()` (`registry_io.py:204-217`) writes a `legacy-baseline.json` sentinel into a collab's revision-event directory when that directory has no revision event yet; `restore --to` (`reactivation_commands.py:117`) rejects any event with `eventType == "legacy-baseline"` as non-restorable. Revision roots under `~/.collabs/nsmac/revisions/` carry `legacy-baseline.json` files.
