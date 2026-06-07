# Repository Contract

Contract between this repository (source plane) and the global agent runtime at `~/.cursor/*`.

## 1) System Model

The contract has three planes:

- **Source plane:** version-controlled files in this repository.
- **Global runtime plane:** `~/.cursor/*`.
- **Project overlay plane:** optional project-local overlay.

Only the source plane is authoritative. Runtime planes are derived execution contexts.

## 2) Authority Chain

Authority is strict and ordered:

1. Repo-owned executable checks and scripts:
   <!-- TODO(patch): list repo-specific validation and contract scripts -->
2. Repo-owned source files and policy documents:
   <!-- TODO(patch): describe authoritative source directories and documents -->
3. Derived runtime or generated outputs:
   <!-- TODO(patch): describe runtime mirrors, generated files, or overlays -->

## 3) Output Chain Contract

<!-- TODO(patch): describe the root outputs this repo projects or generates, their deepest dependency chains, and how each output is validated -->

## 4) Mutation Protocol and Ownership

- Must edit tracked source only.
<!-- TODO(patch): define repo-specific ownership boundaries, generated outputs, and files that must not be edited directly -->

## 5) Validation Modes

### Source Mode (required)

<!-- TODO(patch): list required source-mode validation commands -->

### Runtime Mode (required if the repo projects runtime state)

<!-- TODO(patch): list runtime or projection validation commands, or state explicitly that none exist -->

### Overlay Mode (optional)

<!-- TODO(patch): describe any project-local or environment-specific validation gates -->

## 6) Reporting Contract

<!-- TODO(patch): define the validation results and residual risks that must be reported when work completes -->
