# Restructure Migration Plan

Corrected pilot sequence for migrating the command tree from the flat `commands/<ns>.md` layout to the directory-per-command `commands/<ns>/index.md` layout.

## Pilot Sequence

### Step 1 — Run topology and flag-scope validators

Run `tools/command-system/audit-topology.sh` and `tools/command-system/audit-flag-scope.sh` against the current tree. Both must pass before any structural changes begin.

Flag collisions without an explicit `override: <parent-scope> — <reason>` declaration are errors. Resolve all errors before proceeding.

### Step 2 — Run placement audit

Run `tools/command-system/audit-placement.sh`. Files referenced by more than one command in a namespace must move to `core/<ns>/` before namespace moves begin.

### Step 3 — Move shared files to `core/collab/`

Create `core/collab/` and move all files identified in step 2 as cross-command shared material for the `collab` namespace.

The unprefixed `core/` directory is created here only if cross-namespace material exists. Do not create `core/` speculatively.

### Step 4 — Run catalog gate

Run `./tools/command-system/sync-commands-catalog.sh --check` to confirm the commands catalog is fresh before the first namespace move.

This gate is a **precondition** for the pilot move. It must pass before step 5.

### Step 5 — Pilot move: one namespace/command pair

Move one namespace and one of its commands to the `index.md` layout:

- `commands/<ns>.md` → `commands/<ns>/index.md`
- `_functions/<ns>/<cmd>.md` content inline → `commands/<ns>/<cmd>/index.md`

After the move, re-run `sync-commands-catalog.sh` (write mode) to regenerate the catalog for the new structure.

### Step 6 — Test suite

Run the test suite scoped to the pilot namespace:

- Every generated link resolves
- Every inherited flag origin resolves
- `audit-topology.sh` passes on the moved namespace

Resolve any failures before proceeding to bulk moves.

### Step 7 — Bulk moves

Remaining namespaces are mechanical repeats of steps 4–6 (catalog gate → move → test). Each namespace is moved and validated independently before the next begins.

## Correction Note

The original Conclusion pilot sequence listed the catalog gate as step 5 (after the pilot move at step 4). This was incorrect: the catalog gate is a precondition for the first namespace move, not a follow-on check. The corrected order above places the catalog gate at step 4, before the pilot move at step 5.
