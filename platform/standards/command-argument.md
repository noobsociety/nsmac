# Command Argument

Command argument contract for command routes. Routes adopt named flags by declaring a `route-flag` block, and routes with user-facing mutation gates declare a `route-gate` block.

## Flag Parsing Semantics

- **Long-form tokens only.** Flags use the `--name` form. Short aliases (e.g., `-f`) are not recognized.
- **Exact case-sensitive match.** `--force` and `--Force` are distinct tokens; only the declared form matches.
- **Flags appear immediately after the route selector and before positional arguments.** A route signature of the form `/agent install --force` places the flag after the command verb and before any positional.
- **Flag-and-positional interleaving is not supported.** Interleaving flags with positional arguments is not supported. A future route requiring trailing flags must amend this document; the absence of that support is intentional, not an oversight.
- **Unsupported flags abort before any route mutation.** A route that does not declare a `route-flag` block for a given flag must abort with a clear error when that flag is supplied; it must not silently ignore or pass through the flag.

## `route-flag` Block Schema

Every route that supports or explicitly rejects a named flag must carry a fenced `route-flag` block. The block is machine-readable and validated by the route-flag lint in `platform/tooling/`.

**Required fields**

| Field | Allowed values |
|-------|----------------|
| `flag` | Flag token (e.g., `force`) |
| `eligibility` | `eligible` or `ineligible` |
| `guard-class` | One value from the eligibility or ineligibility table; unknown values fail the lint |
| `ineligibility-reason` | Required when `eligibility: ineligible`; non-empty prose |

**Composition rules**

- `eligibility: eligible` + a `guard-class` listed in the ineligibility table -> lint error.
- `eligibility: ineligible` + empty or absent `ineligibility-reason` -> lint error.
- At most one `route-flag` block per `flag` value per route.

**Example — eligible**

````route-flag
flag: force
eligibility: eligible
guard-class: hard-abort
````

**Example — ineligible**

````route-flag
flag: force
eligibility: ineligible
guard-class: registry-integrity
ineligibility-reason: Bypass would create state that other helpers assume cannot exist.
````

## Force Eligibility Table

| Guard class | Description |
|-------------|-------------|
| `hard-abort` | Route aborts unconditionally on conflict; `--force` redirects to the diff-then-gate path. |
| `gated-overwrite` | Route already presents a destructive gate on conflict; `--force` computes the candidate patch before entering that gate. |
| `recovery-only` | Route normally delegates mutation to lifecycle-specific routes; `--force` admits a narrowly documented metadata repair path. |

## Force Ineligibility Table

| Guard class | Ineligibility reason | Governing contract |
|-------------|----------------------|--------------------|
| `registry-integrity` | Bypass would create state that other helpers assume cannot exist. | `collab/init` steps 8, 12; shared-state invariants |
| `lifecycle-gate` | Guard enforces phase or completion state, not an overwritable artifact. | Phase gating contracts |
| `role-gate` | Guard enforces role membership or reviewer presence. | Role and reviewer contracts |
| `schema-validation` | Guard enforces structural correctness of role JSON or configuration. | `platform/standards/agent-role.md` schema |
| `unreadable-context` | Guard aborts on unreadable input; there is no artifact to diff. | Route-specific abort steps |
| `destructive-delete` | Guard covers `delete`, `archive`, `kick`, `purge`, `reset`, `overwrite` verbs. | Command argument destructive verb set |

## Diff-Then-Write Atomicity Invariant

A route adopting a flag with diff-then-write semantics must produce a single patch object. Use the canonical phrase `the candidate patch` to name it. The diff renderer takes `the candidate patch` as its sole input. The post-confirmation write applies `the candidate patch` without recomputation or re-read of source. The phrase `the candidate patch` must appear in both the diff step and the write step of the adopting route.

This invariant closes the TOCTOU window between diff display and write. A route that recomputes the patch after user confirmation provides weaker guarantees than what the gate contract implies.

## Gate Tiers

**Standard** — the operation modifies state that is reversible by an obvious counter-operation the user already knows (for example, `git reset` for commits). Standard gates use `confirm` to proceed and `cancel` to abort.

**Destructive** — the operation modifies state that is not reversible by an obvious counter-operation. Destructive gates use a closed-set action verb plus a required operand to proceed, and `cancel` to abort.

## Gate Interaction

Flag adoption does not change the gate shape or exact-confirmation-token contract.

## Author-Intent Decision Tree

Apply this tree when choosing a gate tier for a new mutation gate:

1. Does the operation modify state outside framework-owned ungated write paths (such as registry-mediated writes performed by `/collab speak`)? If no, no gate. If yes, continue.
2. Is the modification reversible by an obvious counter-operation the user already knows? If yes, **standard** tier. If no, **destructive** tier.

## Reserved Keyword Vocabulary

Gate tokens are reserved keywords recognized only when a route is in a documented gate state. They are not public commands, do not appear in `commands/`, and are not listed in the command roster.

**Standard tier tokens**

| Purpose | Token |
|---------|-------|
| Proceed | `confirm` |
| Abort | `cancel` |

**Destructive tier tokens**

| Purpose | Token |
|---------|-------|
| Proceed | `<verb> <operand>` — verb drawn from the closed set; operand uniquely identifies the artifact |
| Abort | `cancel` |

**Closed destructive verb set:** `delete`, `archive`, `kick`, `purge`, `reset`, `overwrite`

A new destructive route must map its proceed verb to one of these. If no existing verb fits, extend this list by amending this file — never invent a route-local verb.

## Match Semantics

A gate input matches a token when the input string, after stripping leading and trailing whitespace, equals the token string exactly. Matching is case-sensitive. No regex, no aliases, no shell-completion, no substring matching.

For destructive gates the full `<verb> <operand>` string must match — both verb and operand must be present and correct.

## Token Equivalence

`confirm` == `(confirm)` as syntax sugar; the bare word is canonical. The same equivalence applies to `cancel` and to destructive verb tokens. Both forms satisfy the gate check.

## Gate Declaration Block

Every mutating route must carry a fenced `route-gate` block declaring its gate. The block is machine-readable and validated by the route-gate lint in `platform/tooling/`.

**Required fields**

| Field | Allowed values |
|-------|----------------|
| `gate-class` | `standard` or `destructive` |
| `proceed` | Exact token the user must type to proceed |
| `abort` | `cancel` |
| `operand-format` | `none` for standard; operand description for destructive |
| `invalid-input` | `re-prompt` |
| `re-prompt-template` | Exact prompt text re-displayed on invalid input |

**Example — destructive gate**

````route-gate
gate-class: destructive
proceed: delete <slug>
abort: cancel
operand-format: collab registry id
invalid-input: re-prompt
re-prompt-template: Type "delete <slug>" to delete this collab, or "cancel" to abort.
````

**Example — standard gate**

````route-gate
gate-class: standard
proceed: confirm
abort: cancel
operand-format: none
invalid-input: re-prompt
re-prompt-template: Type "confirm" to proceed, or "cancel" to abort.
````

## Re-Prompt Contract

On invalid input or silence, the gate re-displays the `re-prompt-template` verbatim. The gate remains unresolved until the user types a valid proceed or abort token. There is no "later" or "defer" path — the gate resolves to proceed or abort only.

This file defines what the prompt must convey: proceed token, abort token, and artifact identity for destructive gates. The route's gate declaration block carries the exact `re-prompt-template` text.

## Verb Extension Procedure

To add a verb to the closed destructive set:

1. Amend the **Closed destructive verb set** in this file.
2. Update the route-gate lint in `platform/tooling/` to recognize the new verb.
3. Document the new verb's operand-format convention in this file.

Never add a verb at the route level without amending this file first.

## `route-arg` Block Schema

Every route that declares user-facing arguments must carry a fenced `route-arg` block. The block is machine-readable and validated by `platform/tooling/audit.sh`.

**Required fields**

| Field | Description |
|-------|-------------|
| `dispatch` | Full dispatch signature, mirroring the route signature in the Trigger section |
| `param` | One line per parameter; see **`param` field** below |

**`param` field**

Each `param` line is a semicolon-delimited list of key-value pairs.

Required keys:

| Key | Allowed values | Description |
|-----|----------------|-------------|
| `name` | Flag or positional name | Flag names begin with `--`; positionals use angle-bracket form |
| `required` | `required` or `optional` | Whether the parameter must be supplied by the caller |
| `placeholder` | Literal token or `<placeholder>` | Example token shown in route signatures |
| `class` | `type` or `dynamic` | `type` — a literal or enumerated value; `dynamic` — resolved at runtime from an external source |
| `rule` | Prose or `<type> flag` | Short constraint description |

Optional keys:

| Key | Allowed values | Description |
|-----|----------------|-------------|
| `source` | Command path | Required when `class=dynamic`; identifies the helper that provides the allowed value set |
| `requires` | Flag name | Declares a prerequisite flag; the parameter is only valid when the named flag is also present |
| `default` | `literal:<v>`, `derived:<source>`, or `none` | Default behavior when the parameter is omitted; required on every `required=optional` row |

**`default=` values**

| Value | Meaning |
|-------|---------|
| `literal:<v>` | Omitting the parameter uses the literal value `<v>` |
| `derived:<source>` | The default is computed at runtime from the named source (context variable, sibling flag, or inferred input) |
| `none` | No default; omitting this parameter triggers the abort-with-contextual-help policy in [`platform/standards/command-default.md`](command-default.md) |

**Composition rules**

- `required=required` rows must not carry a `default=` key.
- `required=optional` rows must carry a `default=` key.
- `class=dynamic` rows must carry a `source=` key.
- `default=none` on a `required=optional` row means bare invocation of that parameter triggers the abort-with-contextual-help policy.

**Example**

````route-arg
dispatch: (example cmd "<name>" [--target <role>] [--dry-run])
param: name=<name>; required=required; placeholder=<name>; class=type; rule=title text
param: name=--target; required=optional; placeholder=<role>; class=dynamic; source=commands/example/data/roles.py; default=none
param: name=--dry-run; required=optional; placeholder=--dry-run; class=type; rule=boolean flag; default=literal:false
````

## Negative-Test Category Table

The following categories must each have at least one test before the first flag-adopting batch ships. Test scope is derivable from this table without tracing individual route steps.

| Category | Governing rule |
|----------|----------------|
| Flag position | Command argument parse-position constraint |
| Confirmation token | Command argument exact-token match |
| Registry-integrity guards | `collab/init` steps 8, 12; shared-state invariant |
| Lifecycle and role gates | Phase/role gating contracts |
| Schema and role-JSON validation | Role schema in `platform/standards/agent-role.md` |
| Unreadable context | Route-specific abort on unreadable inputs |
| Destructive-delete guards | Command argument destructive verb set |
| Patch-reference uniqueness | Command argument atomicity invariant; grep confirms no two distinct patch identifiers in the same eligible route |
