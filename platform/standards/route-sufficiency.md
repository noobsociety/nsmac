# Route sufficiency

A route is sufficient when an agent that has read the route file, its explicit forward references, and the resume signal can execute it correctly without inference.

The file is the first checked against its own mechanical rubric. If the file fails a mechanical check, the rubric item is defective and must be corrected before any route migration relies on it.

## Mechanical sufficiency

Mechanical obligations a checker can verify by inspecting route text. Items are addressed by section heading and item number.

1. **Target resolution.** The route explicitly names how the target resource is resolved before any write, and names the ABORT path when resolution fails.
2. **Helper-owned writes.** Every Step that mutates state either names the helper subcommand that performs the write or carries a Notes-level exemption citing `platform/standards/route-invariants.md` floor rule 3.
3. **Role and phase preconditions.** The route explicitly states which roles may act and which phases the command admits before any write step.
4. **Stop conditions.** The route ends with an explicit stop step and names every ABORT condition with a reason before that stop.
5. **Write scope.** The route declares which files or directories may be written to; writes outside the declared scope are not permitted.
6. **Resume signals.** A Notes entry declares the post-state resume signal to run after the command completes.
7. **Recovery paths.** For every Step that can produce partial output — a helper omission, a failed write, or a skipped lifecycle effect — the route names the recovery path or declares the omission a helper defect with a visible ABORT.

## Execution sufficiency

Fixture obligations that require a constrained-bootstrap execution run to verify. The section is not lintable.

A route satisfies execution sufficiency when a fresh agent — with no prior conversation context, no memory beyond the bootstrap chain, and no registry or transcript edits not sanctioned by the route — can follow the route from the bootstrap entry point plus its explicit forward references and reach the expected helper and transcript state.

The fixture must model context loss: fresh bootstrap, active collab resolved from disk, no remembered role, no remembered phase, and no direct registry editing unless the route explicitly declares an exemption. The fixture shape is a required deliverable for any pilot route; its specific harness design is left to the implementing executor.
