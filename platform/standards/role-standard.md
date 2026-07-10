# Role standard

The role standard defines the schema for role JSON files, the global key registry, and the canonical invocation form for any command that accepts a role argument. See [`commands/collab/reference/agent-model.md`](../../commands/collab/reference/agent-model.md) for per-role join-time model recommendations and [`commands/collab/join/index.md`](../../commands/collab/join/index.md) for agentId capture semantics.

## Schema

Each role is defined by a single JSON file. The core identity fields are required. Advisory metadata fields are optional.

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | Global primary key. Unique across all role files; must match the filename stem. |
| `displayName` | string | Human-readable role name. Non-empty. |
| `concerns` | string[] | The role's fixed review lens. Non-empty; at least one item. |
| `dimensions` | string[] | The role's primary review/advisory domain(s), drawn from the domain taxonomy. Required (non-empty) for every role except the moderator; forbidden for the moderator role. See "Dimensions semantics". |
| `prohibitions` | string[] | Optional advisory, principle-level behavioral constraints. Not a runtime enforcement list. |

**Example:**

```json
{
  "key": "tw",
  "displayName": "Technical Writer",
  "concerns": ["clarity", "conciseness", "accuracy", "developer experience", "voice"],
  "dimensions": ["narrative"],
  "prohibitions": ["Do not transform user-supplied quoted text unless the route asks for editing."]
}
```

**Example (arbitrary domain):**

```json
{
  "key": "le",
  "displayName": "Lyric Essayist",
  "concerns": ["voice", "rhythm", "imagery", "restraint"]
}
```

## Concerns semantics

`concerns` values are fixed globally per role. Consuming commands may choose which concerns to surface in a given context, but no command may redefine or override the values declared in the role file. Modification requires changing the role file itself, which is a contract change affecting every consumer.

`concerns` describes review *posture* — the lens a role applies, as declared per role under `commands/collab/reference/roles/`. This is a distinct axis from `dimensions` (see "Dimensions semantics" below), which classifies each role's *subject-matter domain*. Do not collapse the two: a role's `concerns` words are not expected to restate its `dimensions`, and no command may overload one field with both meanings.

## Dimensions semantics

`dimensions` values classify each role's primary review/advisory domain, drawn from a nine-value taxonomy. `platform/data/domain-taxonomy.json` is the machine source of truth; the table below is its human-readable mirror.

| Domain | Meaning |
|---|---|
| `architecture` | control flow, state model, engine seams |
| `delivery` | sequencing, dependencies, ownership, execution |
| `hygiene` | dead code, drift, present-state, residue |
| `narrative` | prose clarity, docs, transcript legibility |
| `product` | capability fit, usefulness, user value |
| `reliability` | failure behavior, recovery, operational continuity |
| `security` | trust boundaries, abuse resistance, exposure |
| `strategy` | goals, intent, prioritization, decision rationale |
| `structure` | file/slice layout, boundaries, placement |

`dimensions` is required (non-empty) for every role except the moderator; the moderator role must not declare it — it stays coverage-only, consistent with its scope/sequencing/framing/pacing/integrity concerns. Assignments designate primary ownership, not exclusive permission: any role may raise an issue outside its declared dimensions when the active work exposes one.

Values must be drawn from the taxonomy above; the role validation harness (`platform/tooling/roles.py`) rejects unknown values and rejects the moderator role declaring the field at all.

## Prohibitions semantics

`prohibitions` values are optional role-local advisory metadata. They document principle-level behaviors a role must avoid, but they are not allow lists, deny lists, capability keys, route-key matching rules, or helper-enforced policy. Helper behavior must not depend on parsing the text.

When a generated or prose surface needs a compact field note, use this exact wording: `principle-level behavioral constraints; not a runtime enforcement list`. Do not insert comments into role JSON.

For the reference inventory of declared prohibitions across registered roles, see [`role-prohibitions.md`](../../commands/collab/reference/role-prohibitions.md).

## Key uniqueness

Keys are globally reserved as a 1:1 primary key mapping to a specific role. No two role files may share a key. The filename stem must equal the `key` field. Uniqueness is machine-enforced by the role validation harness. The agent executing the role is recorded at join time in the collab registry, not in the role file.

## Canonical invocation

`--role <key>` is the standard flag for any command that accepts a role. The flag is always required when a command uses roles; there is no default role.

**Example:** `(collab join --role tw)`

## Reviewer obligations

A role registered as `reviewerRole` with `reviewerMode: last-in-convergent-phases` must, before approving close, verify that every assigned role's Action Plan checklist items are fully checked and consistent with that role's execution history. The `speak-state` helper surfaces this check via the `uncheckedAssignedItemsByRole` field (present when a reviewer is configured): a non-zero count for any role whose execution is recorded `completed` is a coherence contradiction that must be resolved before close. The helper also blocks close directly when such a contradiction exists (`commands/collab/engine/registry.py close`).

## Role roster

**Tool boundary.** The spec accepts any valid role JSON; the roster is open. Tools and test fixtures that enumerate a specific key set (such as the registered role keys) may need updating when a new role is added — the spec does not enforce this automatically. Check `commands/collab/engine/registry.py` snapshot fixtures and generated surfaces such as `generated/command-reference.md` when adding a role.

<!-- BEGIN GENERATED:ROLES_ROSTER -->
_Generated by `platform/tooling/sync-roles-roster.sh`; do not edit this block by hand._

| Key | Display name |
|-----|--------------|
| `mod` | Moderator |
| `pa` | Principal Architect |
| `pe` | Platform Engineer |
| `tl` | Technical Lead |
| `tw` | Technical Writer |
<!-- END GENERATED:ROLES_ROSTER -->

The roster above is generated from every `*.json` under `commands/collab/reference/roles/`.
