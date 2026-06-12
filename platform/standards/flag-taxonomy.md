# Flag taxonomy

## Trigger

**Dispatch:** (reference only — not an invocable route)
**Reference surface:** collab flag taxonomy
**Search phrases:** collab flag taxonomy, flag inventory source, helper enforced flags

## Steps

1. Read this document when changing or displaying collab command flag classifications.
2. Do not mutate registry or transcript state from this documentation-only reference.

## Notes

Defines the three-class taxonomy for collab command flags. Authoritative for the flag inventory generator under items #7, #11, and #15.

## Three classes

| Class | Meaning | Who enforces |
|---|---|---|
| `advisory` | Documented for human use; no helper enforcement; caller may ignore without gate consequence | Route prose |
| `helper-enforced` | Validated by the helper before any write; invalid value causes exit 1 with a named error | `registry.py` |
| `generator-derived` | Produced by a generator command; not accepted as user input on the consuming command | Generator output |

A flag belongs to exactly one class. When a flag's enforcement changes, the entry in this spec must be updated before the helper change ships.

## Flag inventory

### `(collab join)`

| Flag | Class | Notes |
|---|---|---|
| `--role <role>` | `helper-enforced` | Required; helper rejects missing or unreadable role file |
| `--agent-id <id>` | `helper-enforced` | Required; helper rejects blank value; `unknown` is the only permitted fallback |

### `(collab speak)`

| Flag | Class | Notes |
|---|---|---|
| `<message>` | `helper-enforced` | Required for moderator-role contributions; helper aborts when absent |
| `--turn-order <key>...` | `helper-enforced` | Recovery-only; all keys must be registered; helper rejects unknown or duplicate keys |

### `(collab set)`

| Flag | Class | Notes |
|---|---|---|
| `reviewer --clear` | `helper-enforced` | Clears `reviewerRole`; helper validates that `reviewerRole` is set before clearing |
| `turn-order <keys>` | `helper-enforced` | Aliases `--turn-order` write path; same validation as speak-time |
| `--force` | `helper-enforced` | Recovery-only; bypasses normal gate checks; helper logs use; requires explicit declaration in route |

### `(collab run plan)`

| Flag | Class | Notes |
|---|---|---|
| `--scope <path>` | `helper-enforced` | Per-subagent write scope; helper rejects overlapping sibling scopes |
| `--sibling-scope <path>...` | `helper-enforced` | Declared sibling scopes; conflict check against `--scope` |
| `--returned-path <path>` | `advisory` | Returned subagent paths; helper logs but does not enforce scope boundaries at return time |

### `(collab show)`

| Flag | Class | Notes |
|---|---|---|
| `policy` | `advisory` | Displays gate rules and reviewer contract; no write side effects |

## Generator-derived flags

The flag inventory command generates the inventory table above from this spec. The generator:

1. Reads all `Flag inventory` subsections from this file
2. Classifies each row by the `Class` column value
3. Emits one output block per class, listing all flags of that class
4. Includes the `Notes` field verbatim for each flag

The generator does not accept flag-class input at runtime. The classification is read from this spec.

## Explicit classifications

- **`--turn-order`:** `helper-enforced` — recovery-only flag with key validation before any write; callers must not use it as a routine ordering mechanism
- **`set --force`:** `helper-enforced` — recovery-only; logs use; requires route-level declaration; not a general bypass

## Adding a flag

1. Identify the class: does the helper gate on it (`helper-enforced`), is it documentation-only (`advisory`), or is it produced by a generator (`generator-derived`)?
2. Add the row to the appropriate command subsection above
3. If `helper-enforced`: write a test for the rejection path and the acceptance path
4. If `generator-derived`: confirm the generator reads from this spec, not from inline code
5. Ship the spec change before or alongside the helper or generator change
