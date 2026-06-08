# Workflow models

Committed doctrine for the two supported collab workflow models. This document is the authoritative reference for how a collab record closes and what `--terminal` means at init time. All close-path logic in `commands/collab/engine/registry.py` and related helpers is downstream of this specification.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** workflow model, committed workflow model, seal terminal, issue terminal, seal-free close, replacement close-gate, issue lifecycle

## Committed workflow model

**Default terminal:** `seal`. All collabs initialized without `--terminal` use the seal workflow model. Defined in `registry_constants.py` as `DEFAULT_TERMINAL = 'seal'`. Valid terminals: `ALLOWED_TERMINALS = {'seal', 'issue'}`.

The seal workflow model is the invariant baseline. New terminal values are additions alongside it, not replacements. The `planned-routes.md` prerequisite gate guards against activating the issue bridge before the required contract surface is present, because bridging before prerequisites are satisfied bricks the collab tooling for the entire working tree.

## Seal workflow model (`--terminal seal`)

Governs collabs initialized with `--terminal seal` or with no `--terminal` flag (the default).

**Close-gate.** A seal-terminal collab may auto-close only when all three conditions hold:

1. Every non-moderator assigned role has a completed `execution` entry.
2. A current, non-stale `verificationSeal` exists (written by `/collab seal verification`).
3. The reviewer has emitted a `verdict` with `outcome == success`.

The full sub-state lifecycle (`Completion.verification`, `verification.participant`, `verification.seal`, `verification.assessment`) is defined in `verification.md`.

## Issue workflow model (`--terminal issue`)

Governs collabs initialized with `--terminal issue`. The collab closes via exported issue handoff evidence — no reviewer seal is required.

### Issue lifecycle

1. The collab proceeds through all phases (Audit → Discussion → Conclusion → Action Plan → Handoff → Completion) without deviation.
2. In `Completion.execution`, all assigned roles implement their Action Plan items and record `execution` entries in the normal way.
3. The platform engineer role runs `/collab export-issues` to record durable exported-issue handoff evidence. This evidence record is the terminal artifact.
4. When exported issue handoff evidence is present and all non-moderator assigned execution roles are complete, the collab auto-closes. It does not enter `Completion.verification`.

### Seal-free close

Issue terminal collabs do not require a `verificationSeal`. The `verificationSeal` field is absent from the registry entry at close time; its absence is not a validation error for `terminal == 'issue'` collabs. There is no reviewer seal turn and no reviewer assessment turn.

### Replacement close-gate

The seal verification sequence (`Completion.verification` → `verification.participant` → `verification.seal` → `verification.assessment`) is replaced by the exported issue evidence check. An issue-terminal collab auto-closes when:

1. Every non-moderator assigned role has a completed `execution` entry.
2. Exported issue handoff evidence exists and is recorded in the registry (written by `/collab export-issues`).

The close must not wait on a `verificationSeal`. A `verificationSeal` present on an issue-terminal collab is inert and is not consulted at close time.

### Export evidence boundary

`/collab export-issues` records externally supplied issue handoff evidence from a caller-provided evidence file. It does not derive `/git issue create` handoffs from Action Plan items. Automatic issue generation is outside the current workflow-model scope and belongs in a separately chartered collab if needed.

## Terminal selector

The `--terminal <seal|issue>` flag to `/collab init` selects the workflow model at creation time. The value is stored in the registry `terminal` field and governs close behavior for the record's lifetime. The terminal is immutable after init.

**Valid values:** `seal` (default), `issue`. Defined in `registry_constants.py:ALLOWED_TERMINALS`. See `glossary.md` for canonical term definitions.

**See also:** [`REPOSITORY.md` § Collab Workflow Models](../../../REPOSITORY.md#6-collab-workflow-models) for the repository-level summary; [`planned-routes.md`](planned-routes.md) for the prerequisite gate that guards issue bridge activation.
