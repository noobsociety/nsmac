# /collab show flags

Display the generated collab flag inventory from the spec-owned flag taxonomy.

## Trigger

**Slash:** `/collab show flags`
**Signature:** `/collab show flags`
**Prose dispatch:** `(collab show flags)` — prose routing hint; not a terminal command.
**Search phrases:** collab flags, flag inventory, collab command flags

## Steps

1. Read [invariants.md](../../../core/collab/invariants.md) before executing; call the relevant helper fresh and do not trust prior reads from conversation context (Invariant #4). Call `tools/collab/registry.py flag-inventory`.
2. Display the helper output exactly. The helper reads `core/framework/flag-taxonomy.md`, groups rows by class, and emits one block per class.
3. Stop. This route is read-only and must not mutate the registry or transcript.

## Notes

- **Parameters:** none.
- **Source of truth:** `core/framework/flag-taxonomy.md` owns all flag rows and classifications. This route does not duplicate flag docs by hand.
- **Classes:** `advisory`, `helper-enforced`, and `generator-derived`.
- **Recovery flags:** `--turn-order` and `set --force` are classified in the spec and shown by this route.
