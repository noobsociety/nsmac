# Workflow models

How collab records close, and what `--terminal` means at init time. Close behavior in `registry.py` and related helpers follows this spec.

## Trigger

**Slash:** (reference only — not an invocable route)
**Prose dispatch:** (reference only — not an invocable route)
**Search phrases:** workflow model, committed workflow model, seal terminal, issue terminal, seal-free close, replacement close-gate, issue lifecycle

## Committed workflow model

`seal` is the default. Any collab initialized without `--terminal` uses the seal model (`DEFAULT_TERMINAL = 'seal'` in `registry_constants.py`).

New terminal values are additions, not replacements. The `planned-routes.md` gate blocks `--terminal issue` until its prerequisites are in place — using it too early breaks the collab tooling for the whole working tree.

## Seal model (`--terminal seal`)

The default. Closes when all three hold:

1. Every non-moderator assigned role has a completed `execution` entry.
2. A current, non-stale `verificationSeal` exists (written by `(collab seal verification)`).
3. The reviewer has emitted a `verdict` with `outcome == success`.

The sub-state lifecycle (`Completion.verification`, `verification.participant`, `verification.seal`, `verification.assessment`) is defined in `verification.md`.

## Issue workflow model (`--terminal issue`)

Closes when the platform engineer exports issue evidence — no reviewer seal needed.

### Issue lifecycle

1. All phases run normally (Audit → Discussion → Conclusion → Action Plan → Handoff → Completion).
2. In `Completion.execution`, roles implement their Action Plan items and record `execution` entries as usual.
3. The platform engineer runs `(collab export-issues)` to write the issue evidence. This record closes the collab.
4. When evidence is written and all assigned execution is done, the collab closes — no `Completion.verification`.

### Seal-free close

Issue-terminal collabs close without a `verificationSeal`; its absence is not an error. There is no reviewer seal or assessment turn. A `verificationSeal` present on an issue-terminal collab is ignored.

### Replacement close-gate

`(collab export-issues)` writes evidence from a file you supply. It does not create issues from Action Plan items. Automatic issue creation is not supported; open a new collab to charter that work.

## `--terminal` flag

Pass `--terminal <seal|issue>` to `(collab init)`. Stored in the `terminal` field; cannot be changed after init. Valid values in `registry_constants.py:ALLOWED_TERMINALS`. See `glossary.md` for definitions.

**See also:** [`REPOSITORY.md` §6](../../../REPOSITORY.md#6-collab-workflow-models); [`planned-routes.md`](planned-routes.md) for the gate that blocks early activation.
