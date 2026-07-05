# Runtime contract

The document specifies the execution prerequisites for `~/nsmac` tooling. A host that does not meet these requirements may fail with an opaque error mid-run rather than a named failure at startup. `platform/tooling/audit.sh` runs a preflight against these requirements and fails early with a named message before downstream validators run.

## Python

**Minimum: Python 3.9**

All tooling scripts require `str.removeprefix` and `str.removesuffix`, introduced in Python 3.9. No `from __future__` import substitutes these methods; a host on Python 3.8 or earlier fails at the first affected call.

Affected files: `audit-reachability.sh`, `coverage-gate.sh`, `audit.sh`.

## Shell

**Required: bash ≥ 3.2** (the macOS system default; must be available as `bash` on `$PATH`)

All shell scripts target bash. The declared convention is `set -euo pipefail`.

Scripts invoke Python tooling as `python3 <script>` from the repository root. The invocation requires `python3` on `$PATH` to resolve to a conforming interpreter.

## Required binaries

On `$PATH`:

| Binary | Minimum | Use |
|--------|---------|-----|
| `python3` | 3.9 | All embedded Python tooling |
| `git` | any | `audit.sh`, `coverage-gate.sh` |
| `bash` | 3.2 | All shell scripts |

POSIX utilities (`find`, `grep`, `sort`, `awk`, `sed`, `cut`, `tr`, `wc`) are used without version constraints; any POSIX-conforming implementation suffices.

## No third-party packages

Python tooling uses only the standard library. There is no `requirements.txt`, `pyproject.toml`, or `.tool-versions`. Adding a third-party import violates this constraint and silently fails on any host that has not installed the package.
