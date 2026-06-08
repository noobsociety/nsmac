# Runtime Contract

Specifies the execution prerequisites for `~/.cursor` tooling. A host that does not meet these requirements may fail with an opaque error mid-run rather than a named failure at startup. `platform/tooling/audit.sh` runs a preflight against these requirements and fails early with a named message before downstream validators run.

## Python floor

**Minimum: Python 3.9**

All tooling scripts require `str.removeprefix` and `str.removesuffix`, introduced in Python 3.9. No `from __future__` import substitutes these methods; a host on Python 3.8 or earlier fails at the first affected call.

Affected files: `check-source-ledger.py`, `audit-reachability.sh`, `coverage-gate.sh`, `audit.sh`.

## Shell

**Required: bash ≥ 3.2** (the macOS system default; must be available as `bash` on `$PATH`)

All shell scripts target bash. The declared convention is `set -euo pipefail`.

Scripts invoke Python tooling as `python3 <script>` from the repository root. The invariant is that `python3` on `$PATH` resolves to a conforming interpreter.

## External-binary set

Required executables on `$PATH`:

| Binary | Minimum | Use |
|--------|---------|-----|
| `python3` | 3.9 | All embedded Python tooling |
| `git` | any | `audit.sh`, `check-source-ledger.py`, `coverage-gate.sh` |
| `bash` | 3.2 | All shell scripts |

POSIX utilities (`find`, `grep`, `sort`, `awk`, `sed`, `cut`, `tr`, `wc`) are used without version constraints; any POSIX-conforming implementation suffices.

## stdlib-only guarantee

Python tooling uses only the Python standard library. No `requirements.txt`, `pyproject.toml`, or `.tool-versions` is present; none is expected. Adding a third-party import violates this contract and introduces a setup dependency that fails silently on a fresh host.
