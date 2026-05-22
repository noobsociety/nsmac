# QA — command _settings

Deterministic QA for user settings settings sources and their linked runtime JSON files.

## Procedure

1. Load every `*.json` under the tracked source directory `_settings/`.
2. Validate the source roster is exact.
3. Validate each source file is valid JSON and <= 250 lines.
4. Validate runtime mode links each source file to the user settings directory, not to `~/.cursor/_settings/`.
5. Validate no path-like values reference parent-repo authoring-only folders (`../`, `_core`, `~/.cursor/_core`).

## Required roster

Tracked user settings settings source files under `_settings/`:

- `settings.json`
- `keybindings.json`

Runtime user settings settings targets mirror the same filenames in the user settings directory.

## Output

Return pass/fail per check and list exact failing file paths.
