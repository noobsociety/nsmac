#!/usr/bin/env bash
set -euo pipefail
"$(dirname "$0")/admin-guard-case.sh" unset-field-not-unsettable
