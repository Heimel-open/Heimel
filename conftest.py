import sys
from pathlib import Path

# Minimal src-layout path injection so `import valo_external_adapters` works
# under pytest without a full build/install step.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
