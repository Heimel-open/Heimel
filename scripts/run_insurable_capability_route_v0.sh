#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install -q -e '.[dev]'

pytest -q \
  tests/test_insurable_capability_route_v0.py \
  examples/demonstrator_7_personal_compute_v0.py \
  examples/demonstrator_8_insurable_capability_route_v0.py

python examples/demonstrator_8_insurable_capability_route_v0.py
