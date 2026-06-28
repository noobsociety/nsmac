#!/usr/bin/env bash
set -euo pipefail
"$(dirname "$0")/admin-guard-case.sh" rewrite-execution-role-not-registered
