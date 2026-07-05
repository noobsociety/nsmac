# NSMAC system reference

The document maps the `~/.cursor` platform for readers who need to navigate the system as a whole. Consult the document when the per-route playbooks or reference docs leave system-level context unclear. Do not duplicate generated-mirror tables; follow the links to the authoritative sources.

## Audience routing

| Audience | Start here | Then read |
|----------|------------|-----------|
| **Moderator** — runs `init`, `advance`, `close` | [`commands/commands.md`](../commands/commands.md) · `(collab init / advance / close)` routes | [`commands/collab/reference/workflow-models.md`](../commands/collab/reference/workflow-models.md), [`commands/collab/reference/phase-admissibility.md`](../commands/collab/reference/phase-admissibility.md) |
| **Participant agent** — contributes `speak`, `run plan`, `participant verify` | [`AGENTS.md`](../AGENTS.md) → [`commands/commands.md`](../commands/commands.md) | [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md), [`commands/collab/reference/phase-admissibility.md`](../commands/collab/reference/phase-admissibility.md), [`commands/collab/reference/agent-effort.md`](../commands/collab/reference/agent-effort.md) |
| **Reviewer** — issues `seal verification`, emits verdict | [`commands/collab/reference/verification.md`](../commands/collab/reference/verification.md) | [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md) §17–21, [`commands/collab/seal-verification/index.md`](../commands/collab/seal-verification/index.md) |
| **System maintainer** — changes routes, helpers, or tooling | [`REPOSITORY.md`](../REPOSITORY.md) | [`platform/standards/doctrine.md`](standards/doctrine.md), [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md), [`commands/collab/engine/registry.py`](../commands/collab/engine/registry.py) |

## Four contracts

The platform is organized around four binding contracts. A change that violates one violates all.

### 1. Doctrine — per-design rulings

Per-design rationale for every non-obvious system opinion. Start here when a design choice is ambiguous or recurring debates need pre-answering.

- [`platform/standards/doctrine.md`](standards/doctrine.md) — binding per-design rulings (JSON registry, Markdown transcripts, MCP boundary, single-writer helper, human-only moderator, reopen-as-full-reset, schema posture)
- [`platform/data/doctrines.md`](data/doctrines.md) — standing cross-collab rules (hard-cutover naming, etc.)

### 2. Vocabulary — canonical terms and constants

Authoritative term definitions and the constants the engine dispatches on. Prose that diverges from the constants is a vocabulary defect.

- [`commands/collab/reference/glossary.md`](../commands/collab/reference/glossary.md) — one canonical term per concept; prose mirror of the vocabulary constants
- [`commands/collab/engine/registry_constants.py`](../commands/collab/engine/registry_constants.py) — executable vocabulary (`PHASES`, `ALLOWED_TERMINALS`, `ALLOWED_VERDICT_OUTCOMES`, cap-exit tokens, stage tokens)

### 3. Invariants — cross-route rules

Rules that all routes and the helper must obey; any route that contradicts an invariant is a defect.

- [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md) — invariants #1–#21 (agent-honor-system, disk-state authority, Action Plan shape, charter coverage, seal content-addressing, reopen carry-forward)

### 4. Lifecycle — schema and validation

The lifecycle schema describes the valid states the registry can hold and how transitions are validated.

- [`registry.schema.json`](../registry.schema.json) — reference/projection-only schema; parity-gated against the live validator (see [doctrine: schema posture](standards/doctrine.md#schema-posture))
- [`commands/collab/reference/registry.md`](../commands/collab/reference/registry.md) — registry field schema and field ownership
- [`commands/collab/reference/workflow-models.md`](../commands/collab/reference/workflow-models.md) — `seal` vs `issue` terminal models

## Command grammar

All collab commands are dispatched through the `~/.cursor` routing system.

- [`commands/commands.md`](../commands/commands.md) — command roster; public router and route playbook index
- [`platform/standards/command-standard.md`](standards/command-standard.md) — command convention and namespace rules
- [`platform/standards/command-argument.md`](standards/command-argument.md) — `route-arg` and `route-flag` schema

## Roles

- [`platform/standards/role-standard.md`](standards/role-standard.md) — joinable-role definitions (mod, tw, pe, pa)
- [`commands/collab/reference/agent-effort.md`](../commands/collab/reference/agent-effort.md) — per-phase effort expectations by role
- [`commands/collab/reference/agent-model.md`](../commands/collab/reference/agent-model.md) — agent identity and capability model

## Verification

- [`commands/collab/reference/verification.md`](../commands/collab/reference/verification.md) — `Completion.verification` sub-state semantics, seal object, cap-exit options, reviewer obligation
- [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md) §17–21 — charter coverage, seal content-addressing, reopen carry-forward

## Source ledger


## Generated mirrors

Generated files are produced by platform tooling and checked via `--check` gates. Do not edit them by hand.

- `generated/` — generated mirror content
- [`REPOSITORY.md`](../REPOSITORY.md) §5 — mirror generation and `--check` gating
