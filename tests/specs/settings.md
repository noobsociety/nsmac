# QA — command settings

Deterministic QA for the absence of tracked user-settings sources in this repository.

## Procedure

1. Confirm the tracked source directory `settings/` is absent.
2. Validate no tracked file under this repository is projected as a user settings source.
3. Validate no runtime-mode link points to `~/nsmac/settings/`.
4. Validate no path-like values reference parent-repo authoring-only folders (`../`, `core`, `~/nsmac/core`).

## Required roster

Tracked user-settings source files under `settings/`: none.

Runtime user-settings targets are not owned by this repository.

## Output

Return pass/fail per check and list exact failing file paths.
