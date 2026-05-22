# Topology Validator Contract

Specifies what `tools/command-system/audit-topology.sh` must check once the command tree is restructured to the `commands/<ns>/index.md` layout.

## Scope

Applies only to the restructured `commands/` tree. Not applicable while namespaces still use the flat `commands/<ns>.md` form.

## Required Paths

For every namespace entry in the commands catalog (`commands/commands.md`):

- `commands/<ns>/index.md` must exist

For every command listed under a namespace in the commands catalog:

- `commands/<ns>/<cmd>/index.md` must exist

`<ns>` is the namespace slug and `<cmd>` is the command slug as they appear in the catalog.

## Error Conditions

### Missing required path — error

A catalog entry whose `index.md` does not exist on disk produces an error. Exit code is non-zero when any error is present.

Error message form:

```
ERROR: missing namespace entry point: commands/<ns>/index.md
ERROR: missing command entry point: commands/<ns>/<cmd>/index.md
```

### Orphaned entry point — warning

An `index.md` found at `commands/<ns>/index.md` or `commands/<ns>/<cmd>/index.md` that has no corresponding catalog entry produces a warning. Exit code is unaffected by warnings.

Warning message form:

```
WARN: orphaned entry point: commands/<ns>/index.md (no catalog entry for namespace <ns>)
WARN: orphaned entry point: commands/<ns>/<cmd>/index.md (no catalog entry for command <ns>/<cmd>)
```

## Registration Source

The commands catalog (`commands/commands.md`, `<!-- BEGIN GENERATED:COMMANDS_ROSTER -->` block) is the authoritative list of registered namespaces and commands. The validator reads the catalog to determine expected paths; it does not scan `_functions/` independently.

## Implementation Target

`tools/command-system/audit-topology.sh`

The validator is listed as a step in the restructure pilot sequence and must pass before any bulk namespace moves begin.
