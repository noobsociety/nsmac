# `workRepo` remediation index

Durable definitions for R1–R7 from collab #50 (`2026-06-02-external-repo-seal-failure-workrepo-default-trap`). These definitions were transcribed to satisfy the reviewer's Conclusion provenance precondition in that collab record. Do not mutate this file without reopening the source collab or opening a follow-up.

## Trigger

**Slash:** (reference only — not an invocable route)
**Search phrases:** workRepo remediation, R1, R2, R3, R4, R5, R6, R7, external repo seal failure

## Remediation items

**R1** — Resolve `workRepo` at init from the `.collab.json` marker directory (the same signal already used for registry resolution), persist the resolved absolute path, so every future helper invocation uses the correct repo without re-resolving from a possibly-drifted cwd.

**R2** — Remove the silent `workRepo→ROOT` fallback for external-project collabs; abort loudly when `workRepo` is unbound: `"work tree not bound; run (collab set) <target> work-repo <path>"`.

**R3** — Select execution commits by path history (`git log -1 -- <paths>`) rather than bare `HEAD`, so each recorded commit actually contains the declared touched paths.

**R4** — At execution-record time, verify that all declared `touchedPaths` exist under the bound `workRepo`; reject records that touch paths outside the bound repo.

**R5** — Seal git-state diagnostics must name the failure class precisely: missing `workRepo` binding, touched paths not found under `workRepo`, or commit SHA not found in the bound repo — each with a distinct error message and recovery hint.

**R6** — Provide a sanctioned completed-record provenance-repair path that atomically updates `workRepo` and recorded commits without requiring re-execution of the original work.

**R7** — The provenance repair must recompute `pairedExecutionSignature` atomically so the repaired record passes future seal verification without a full re-run.
