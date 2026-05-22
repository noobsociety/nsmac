# Placement Audit Contract

Specifies the reference predicate and traversal scope used by `tools/command-system/audit-placement.sh` to determine whether a file must live under `core/<ns>/` rather than inside the `commands/` tree.

## Placement Rule

A file that is referenced by more than one command within the same namespace must live under `core/<ns>/`.

A file that is referenced by commands in more than one namespace must live under `core/`.

## Reference Predicate

A file `F` is considered **referenced by a command** when `F` appears in that command's `index.md` via either of the following forms:

**Markdown link:**

```
[label](path/to/F)
```

Any relative or repo-root-relative markdown link whose resolved path equals `F`.

**Slash-dispatch token:**

A bare path token that appears as a slash-dispatch reference, i.e. a line of the form:

```
/<ns> <cmd> path/to/F
```

where `path/to/F` resolves to `F`.

Both forms are treated as equivalent references for the purpose of counting.

## Traversal Scope

The audit traverses only the `commands/` tree. Specifically:

- Source files examined: `commands/<ns>/<cmd>/index.md` for every namespace and command
- Files from `_functions/`, `core/`, `_tests/`, `tools/`, or any path outside `commands/` are not examined as **sources** of references
- However, the **targets** of references (the files being pointed to) may be located anywhere in the repository

## Multi-Command Threshold

"Referenced by more than one command" means the file appears as a reference (by either form above) in two or more distinct `commands/<ns>/<cmd>/index.md` files within the same namespace.

## Audit Output

For each file that meets the multi-command threshold but does not reside under the correct `core/` path, the audit produces an error:

```
ERROR: shared file must move to core/<ns>/: <current-path>
  referenced by: commands/<ns>/<cmd1>/index.md, commands/<ns>/<cmd2>/index.md
```

For cross-namespace shared files not under `core/`:

```
ERROR: cross-namespace shared file must move to core/: <current-path>
  referenced by: commands/<ns1>/<cmd>/index.md, commands/<ns2>/<cmd>/index.md
```

Exit code is non-zero when any error is present.

## Implementation Target

`tools/command-system/audit-placement.sh`

The audit runs as step 2 of the restructure pilot sequence, after the topology and flag-scope validators pass and before any file moves begin.
