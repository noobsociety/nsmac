# (quality show notes)

Serve as the append-only log for QA learning notes approved during `(quality tune)` runs.

## Trigger

**Dispatch:** `(quality show notes)` — routing-only command form; not a shell command.
**Search phrases:** quality notes, QA notes, learning log

## Steps

1. Load this route only through `(quality tune)`; do not invoke `(quality show notes)` directly.
2. Let `(quality tune)` append approved learning notes per **Append behavior** in **Notes**.
3. If direct user input asks to rewrite prior entries, **ABORT**: notes are append-only.

## Notes

- **Parameters:** no arguments accepted.
- **Internal-only:** Do not invoke `(quality show notes)` directly; this route is loaded exclusively by `(quality tune)`.
- **Authority:** `(quality tune)` owns approved appends to this file.
- **Append-only:** Never replace or rewrite prior audit sections.
- **Append behavior:** When learning is enabled and the user confirms note retention, append one section under `## QA audit — YYYY-MM-DD`; add a counter suffix when the same date heading already exists.
- **Status:** No retained QA audit entries yet.
