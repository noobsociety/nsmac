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
- [`commands/collab/engine/registry_constants.py`](../commands/collab/engine/registry_constants.py) — executable vocabulary (`PHASES`, `ALLOWED_VERDICT_OUTCOMES`, verification stage tokens)

### 3. Invariants — cross-route rules

Rules that all routes and the helper must obey; any route that contradicts an invariant is a defect.

- [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md) — invariants #1–#21 (agent-honor-system, disk-state authority, Action Plan shape, charter coverage, seal content-addressing, reopen carry-forward)

### 4. Lifecycle — schema and validation

The lifecycle schema describes the valid states the registry can hold and how transitions are validated.

- [`registry.schema.json`](../registry.schema.json) — reference/projection-only schema; parity-gated against the live validator (see [doctrine: schema posture](standards/doctrine.md#schema-posture))
- [`commands/collab/reference/registry.md`](../commands/collab/reference/registry.md) — registry field schema and field ownership
- [`commands/collab/reference/workflow-models.md`](../commands/collab/reference/workflow-models.md) — current reviewer-seal close model

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

- [`commands/collab/reference/verification.md`](../commands/collab/reference/verification.md) — `Completion.verification` sub-state semantics, seal object, reviewer obligation
- [`commands/collab/reference/invariants.md`](../commands/collab/reference/invariants.md) §17–21 — charter coverage, seal content-addressing, reopen carry-forward

## Source ledger

Use this ledger when the role-oriented paths above do not answer where a source
contract lives.

| Area | Sources |
| --- | --- |
| Command naming and arguments | [`command-convention.md`](standards/command-convention.md), [`command-grammar.md`](standards/command-grammar.md), [`command-default.md`](standards/command-default.md), [`command-argument.md`](standards/command-argument.md) |
| Command playbook quality | [`command-standard.md`](standards/command-standard.md), [`playbook-discipline.md`](standards/playbook-discipline.md), [`route-invariants.md`](standards/route-invariants.md), [`route-sufficiency.md`](standards/route-sufficiency.md) |
| Runtime and host boundaries | [`runtime-contract.md`](standards/runtime-contract.md), [`framework-boundaries.md`](standards/framework-boundaries.md), [`host-integration.md`](standards/host-integration.md) |
| Roles, flags, and helper subcommands | [`role-standard.md`](standards/role-standard.md), [`flag-taxonomy.md`](standards/flag-taxonomy.md), [`helper-subcommands.md`](standards/helper-subcommands.md), [`commands/collab/reference/anchor-convention.md`](../commands/collab/reference/anchor-convention.md) |
| Writing and publication style | [`style-guide.md`](standards/style-guide.md), [`document-standard.md`](standards/document-standard.md), [`author-voice.md`](standards/author-voice.md), [`devblog-discipline.md`](standards/devblog-discipline.md), [`markdown-workflow.md`](standards/markdown-workflow.md), [`git-convention.md`](standards/git-convention.md) |
| Collab engine and route references | [`engine-architecture.md`](../commands/collab/reference/engine-architecture.md), [`helper-output.md`](../commands/collab/reference/helper-output.md), [`tag-release-charter.md`](../commands/collab/reference/tag-release-charter.md), [`commands/collab/data/README.md`](../commands/collab/data/README.md) |
| Templates and QA specs | [`platform/templates/AGENTS.md`](templates/AGENTS.md), [`platform/templates/CLAUDE.md`](templates/CLAUDE.md), [`platform/templates/REPOSITORY.md`](templates/REPOSITORY.md), [`tests/specs/generated.md`](../tests/specs/generated.md), [`tests/specs/roles.md`](../tests/specs/roles.md), [`tests/specs/settings.md`](../tests/specs/settings.md), [`tests/specs/templates.md`](../tests/specs/templates.md), [`tests/specs/tests.md`](../tests/specs/tests.md), [`tests/suites/README.md`](../tests/suites/README.md) |
| Tooling contracts | [`advisory-coverage-policy.md`](tooling/advisory-coverage-policy.md), [`flag-scope-validator-contract.md`](tooling/flag-scope-validator-contract.md), [`placement-audit-contract.md`](tooling/placement-audit-contract.md), [`topology-validator-contract.md`](tooling/topology-validator-contract.md), [`coverage-gate-migration.md`](tooling/coverage-gate-migration.md), [`migrate-collab-state-dirs.md`](tooling/migrate-collab-state-dirs.md) |

## Generated mirrors

Generated files are produced by platform tooling and checked via `--check` gates. Do not edit them by hand.

- `generated/` — generated mirror content
- [`REPOSITORY.md`](../REPOSITORY.md) §5 — mirror generation and `--check` gating
