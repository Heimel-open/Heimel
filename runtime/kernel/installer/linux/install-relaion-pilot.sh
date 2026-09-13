#!/usr/bin/env bash
set -euo pipefail

fail(){ printf '\nrelAIon was not activated.\n%s\n' "$1" >&2; exit 1; }
step(){ printf '[relAIon] %s\n' "$1"; }

[[ "$(uname -s)" == "Linux" ]] || fail "Linux is required."
ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/relaion"
STATE="$ROOT/state"
mkdir -p "$STATE"

step "Checking this machine"
ARCH="$(uname -m)"
MEM_KB="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
MEM_GB=$(( MEM_KB / 1024 / 1024 ))
(( MEM_GB >= 8 )) || fail "At least 8 GB RAM is required."

GPU="none"
if command -v nvidia-smi >/dev/null 2>&1; then GPU="nvidia"; fi

step "Checking local inference"
RUNTIME=""
if command -v ollama >/dev/null 2>&1; then RUNTIME="ollama"; fi
if [[ -z "$RUNTIME" ]] && command -v llama-server >/dev/null 2>&1; then RUNTIME="llama.cpp"; fi
[[ -n "$RUNTIME" ]] || fail "No admitted local inference runtime found. Pilot supports Ollama or llama.cpp."

MODEL="${RELAION_MODEL:-qwen2.5:0.5b}"
if [[ "$RUNTIME" == "ollama" ]]; then
  step "Verifying local inference"
  ollama pull "$MODEL" >/dev/null
  PROBE="$(printf 'Reply with the single token RELAION_READY.' | ollama run "$MODEL" 2>/dev/null | head -c 4096)"
else
  fail "llama.cpp route requires an explicitly supplied local model path in this pilot."
fi
[[ -n "$PROBE" ]] || fail "Local inference probe failed."

step "Running Handlingsrett self-test"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"
PY="${RELAION_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || fail "Bundled Python runtime missing."
RESULT="$($PY - <<'PY'
from datetime import datetime, timezone, timedelta
from valo_kernel.windows_capability_adapter import EffectRequest, WindowsCapabilitySurface, AuthorizationDisposition, CommitAuthorization, invoke_governed_windows_capability
r=EffectRequest(request_id='linux-selftest',actor_id='relaion',principal_id='local-user',surface=WindowsCapabilitySurface.MCP,capability_id='test.effect',provider_id='linux.local',target='selftest',purpose='bootstrap-selftest',mandate_ref='selftest',requested_at=datetime.now(timezone.utc))
called=[]
def auth(req, at):
    return CommitAuthorization(decision_id='deny-selftest',disposition=AuthorizationDisposition.DENY,effect_digest=req.effect_digest,evaluated_at=at,valid_until=at+timedelta(seconds=5),reasons=('SELFTEST_DENY',))
receipt=invoke_governed_windows_capability(request=r,authorize=auth,provider_invoke=lambda req: called.append(True),commit_time=datetime.now(timezone.utc))
print('READY' if (not called and not receipt.invoked and receipt.receipt_digest) else 'FAILED')
PY
)"
[[ "$RESULT" == "READY" ]] || fail "Handlingsrett negative test failed."

cat > "$STATE/ready.json" <<EOF
{"state":"READY","platform":"linux","architecture":"$ARCH","gpu":"$GPU","inference_route":"$RUNTIME:$MODEL","governance_gate":true,"denied_effect_contained":true,"remote_processing":"OFF"}
EOF
printf '\nrelAIon Node: READY\nLocal route: %s:%s\nHandlingsrett gate: ACTIVE\nRemote processing: OFF\n' "$RUNTIME" "$MODEL"
