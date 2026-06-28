#!/usr/bin/env bash
set -euo pipefail
"$(dirname "$0")/admin-guard-case.sh" rewrite-summary-no-prior-summary
