# QA — command roles

Deterministic QA for shared role JSON sources projected to `~/.cursor/core/collab/roles/`.

## Procedure

1. Load every `*.json` under the tracked source directory `core/collab/roles/`.
2. Validate the source roster is exact.
3. Validate each source file is valid JSON and uses the role schema in `core/framework/agent-role.md`.
4. Validate each filename stem equals its `key`.
5. Validate keys are globally unique.
6. Validate runtime mode copies `core/collab/roles/` to `~/.cursor/core/collab/roles/`.

## Required roster

<!-- BEGIN GENERATED:REQUIRED_ROSTER -->
<!-- shared-cmd-values exemption: registry-state mirror; role-key enumeration is generated output, not prose authorship. -->
_Generated from `core/collab/roles/*.json`; do not edit this block by hand._

Tracked role source files under `core/collab/roles/`:

- `mod.json`
- `pa.json`
- `pe.json`
- `tw.json`
<!-- END GENERATED:REQUIRED_ROSTER -->

## Output

Return pass/fail per check and list exact failing file paths.
