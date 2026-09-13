"""
VAIG Embedded — On-Device Runtime for macOS/Linux/Windows
"Little Snitch for AI" — monitors every LLM token locally

No network calls. No external APIs. Pure stdlib.

STATUS: edge-oriented reference runtime. This is Python and NOT
accelerator-backed; it demonstrates the on-device pattern. For production
edge deploys target Rust/C/TFLite/NPU with the same five-instrument contract
(LiteEnsemble.score_token -> combined score + per-instrument breakdown).
Use SQLiteWORM for on-device WORM logging and hardware_detect to probe
available acceleration.
"""
from vaig.vaig_embedded.core.ensemble import LiteEnsemble
from vaig.vaig_embedded.core.worm_sqlite import SQLiteWORM
from vaig.vaig_embedded.core.hardware_detect import (
    HWAccel,
    detect_hardware,
    get_optimal_threads,
)
from vaig.vaig_embedded.core.vu_meter import VUMeter

__version__ = "0.1.0"

__all__ = [
    "LiteEnsemble",
    "SQLiteWORM",
    "VUMeter",
    "HWAccel",
    "detect_hardware",
    "get_optimal_threads",
]
