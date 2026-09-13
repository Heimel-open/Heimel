#!/usr/bin/env bash
set -euo pipefail
fail(){ printf '%s\n' "$1" >&2; exit 1; }
command -v nvidia-smi >/dev/null 2>&1 || fail "NVIDIA GPU/driver not detected."
GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
VRAM_MB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1)"

BACKEND=""
if command -v ollama >/dev/null 2>&1; then BACKEND="ollama"; fi
if [[ -z "$BACKEND" ]] && command -v llama-server >/dev/null 2>&1; then BACKEND="llama.cpp"; fi
if [[ -z "$BACKEND" ]] && command -v vllm >/dev/null 2>&1; then BACKEND="vllm"; fi
[[ -n "$BACKEND" ]] || fail "No admitted NVIDIA local inference backend found."

MODEL="${RELAION_MODEL:-qwen2.5:0.5b}"
if [[ "$BACKEND" == "ollama" ]]; then
  ollama pull "$MODEL" >/dev/null
  PROBE="$(printf 'Reply with RELAION_READY.' | ollama run "$MODEL" 2>/dev/null | head -c 4096)"
  [[ -n "$PROBE" ]] || fail "NVIDIA local inference probe failed."
else
  fail "$BACKEND detected but this pilot requires explicit model/server configuration for that backend."
fi

printf '{"provider":"nvidia","gpu":"%s","vram_mb":%s,"backend":"%s","model":"%s","inference_verified":true}\n' "$GPU_NAME" "$VRAM_MB" "$BACKEND" "$MODEL"
