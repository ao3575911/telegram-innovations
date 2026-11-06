#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run ./scripts/install.sh first.' >&2
  exit 1
fi
# Environment is inherited; this script never executes configuration files.
umask 077
exec .venv/bin/python -m telegram_innovation run "$@"
