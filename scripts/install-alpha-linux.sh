#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${RELAION_VENV_DIR:-$HOME/.local/share/relaion/venv}"
STATE_DIR="${RELAION_STATE_DIR:-$HOME/.local/share/relaion/alpha}"
BIN_DIR="${RELAION_BIN_DIR:-$HOME/.local/bin}"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY

mkdir -p "$VENV_DIR" "$STATE_DIR" "$BIN_DIR"
chmod 700 "$STATE_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install "$ROOT_DIR"

cat > "$BIN_DIR/relaion-alpha" <<EOF
#!/usr/bin/env bash
export RELAION_NODE_NAME=Alpha
export RELAION_STATE_DIR="$STATE_DIR"
exec "$VENV_DIR/bin/relaion" "\$@"
EOF
chmod 700 "$BIN_DIR/relaion-alpha"

"$BIN_DIR/relaion-alpha" init
"$BIN_DIR/relaion-alpha" health

echo "Alpha installed. Command: $BIN_DIR/relaion-alpha"
