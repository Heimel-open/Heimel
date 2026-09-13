"""Source-level audit for the new AI-PLS golden execution path."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NEW_PATH_FILES = [
    ROOT / "ai-pls-golden-path" / "src" / "lib.rs",
    ROOT / "ai-pls-racs-bridge" / "src" / "lib.rs",
    ROOT / "ai-pls-racs-bridge" / "src" / "main.rs",
    ROOT / "l2-orchestrator" / "src" / "golden_path.py",
]

FORBIDDEN_TOKENS = {
    "ai_confidence",
    "confidence_score",
    "c0_threshold",
    "validate_decision",
    "check_coherence",
    "evaluate_prompt",
}


def test_new_path_does_not_reintroduce_legacy_confidence_language():
    for path in NEW_PATH_FILES:
        text = path.read_text(encoding="utf-8")
        hits = sorted(token for token in FORBIDDEN_TOKENS if token in text)
        assert not hits, f"{path} contains legacy tokens: {hits}"
