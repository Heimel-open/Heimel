#!/usr/bin/env bash
set -euo pipefail

if [ ! -f tools/tla2tools.jar ]; then
  mkdir -p tools
  curl -L -o tools/tla2tools.jar https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar
fi

# The active VALO Core verification target is the VALO-owned state machine.
# Historical collaboration models under mecha/ remain available only when
# their path is supplied explicitly.
MODEL="${1:-formal-verification/ValoStateMachine.tla}"
CONFIG="${2:-}"

if [ -z "$CONFIG" ]; then
  CONFIG="${MODEL%.tla}.cfg"
fi

if [ ! -f "$MODEL" ]; then
  echo "Model not found: $MODEL" >&2
  exit 1
fi

if [ ! -f "$CONFIG" ]; then
  echo "Config not found: $CONFIG" >&2
  exit 1
fi

java -cp tools/tla2tools.jar tlc2.TLC "$MODEL" -config "$CONFIG"
