# Flag-scope validator contract

The document specifies what `platform/tooling/audit-flag-scope.sh` must check when validating the three-tier flag inheritance model used in the restructured command tree.

## Scope tiers

Flags are declared at one of three tiers, ordered from broadest to narrowest:

1. **system** — applies across all namespaces
2. **namespace** — applies to all commands within a namespace
3. **command** — applies to a single command

Non-conflicting flags across tiers union automatically. No declaration is required.

## Conflict definition

A **conflict** exists when the same flag name (the long-form token, e.g. `--dry-run`) appears at two or more tiers for the same command resolution path.

## Override declaration form

When a narrower scope declares a flag that conflicts with a broader scope, the narrower scope's flag block must include the following field:

```
override: <parent-scope> — <reason>
```

Where:

- `<parent-scope>` is exactly one of: `system`, `namespace`
- ` — ` is the em-dash delimiter (U+2014), with a single space on each side
- `<reason>` is a non-empty free-text explanation of why the narrower scope narrows or overrides the parent

The hyphen form (U+002D, `-`) and en-dash form (U+2013, `–`) are not valid. The validator enforces the em-dash delimiter (U+2014).

Example:

```
override: namespace — command-scoped --dry-run affects only catalog write, not registry state
```

## Error conditions

### Missing override declaration — error

A flag name present at the command or namespace tier that also appears at a broader tier, without an `override:` declaration in the narrower tier's flag block, produces an error. Exit code is non-zero when any error is present.

Error message form:

```
ERROR: flag '<name>' at <narrow-scope> scope shadows <broad-scope> scope without override declaration
  field: <path-to-flag-block>
  conflicting scopes: <narrow-scope>, <broad-scope>
  required form: override: <broad-scope> — <reason>
```

### Malformed override declaration — error

An `override:` line present but using the wrong delimiter (e.g. hyphen (U+002D) or en-dash (U+2013) instead of em-dash (U+2014)) or missing the reason field also produces an error.

Error message form:

```
ERROR: malformed override declaration for flag '<name>' at <narrow-scope> scope
  field: <path-to-flag-block>
  found: override: <found-text>
  required form: override: <parent-scope> — <reason>
```

### Unresolved inherited origin — error

An `override:` line that is correctly formed (em-dash delimiter, non-empty reason) but declares a parent scope (`system` or `namespace`) where no matching flag exists produces an error. The override references an origin that does not exist in the tree.

Error message form:

```
ERROR: unresolved inherited flag origin for flag '<name>' at <narrow-scope> scope
  field: <path-to-flag-block>
  found: override: <found-text>
  missing origin: <parent-scope>
```

## Implementation target

`platform/tooling/audit-flag-scope.sh`
