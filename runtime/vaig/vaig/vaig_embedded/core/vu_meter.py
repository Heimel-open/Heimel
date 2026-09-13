"""
VAIG Embedded — VU Meter (3-Channel Coherence Display)
Visual feedback: GREEN (coherent) / YELLOW (monitoring) / RED (halted)
"""
from typing import Dict, Optional, Callable

class VUMeter:
    """3-channel coherence display. Maps instrument scores to visual channels."""

    def __init__(self, threshold_yellow: float = 0.5, threshold_red: float = 0.8):
        self.threshold_yellow = threshold_yellow
        self.threshold_red = threshold_red
        self.history = []
        self.max_history = 100

    def update(self, scores: Dict[str, float]):
        """Update VU channels from instrument scores."""
        self.history.append(scores)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def channels(self) -> Dict[str, float]:
        """Return 3 channel levels [0.0-1.0]."""
        if not self.history:
            return {"coherence": 0.0, "stability": 0.0, "integrity": 0.0}

        recent = self.history[-10:]
        coherence = sum(s.get('text_similarity', 0.5) for s in recent) / len(recent)
        stability = sum(s.get('semantic_entropy', 0.5) for s in recent) / len(recent)
        integrity = sum(s.get('perturbation', 0.5) for s in recent) / len(recent)

        return {
            "coherence": coherence,
            "stability": stability,
            "integrity": integrity,
        }

    def status(self) -> str:
        """Overall status: GREEN / YELLOW / RED."""
        ch = self.channels()
        avg = sum(ch.values()) / 3
        if avg < self.threshold_yellow:
            return "GREEN"
        elif avg < self.threshold_red:
            return "YELLOW"
        return "RED"

    def __str__(self) -> str:
        ch = self.channels()
        status = self.status()
        bars = "█" * int(sum(ch.values()) / 3 * 20)
        return f"[{status:6}] {bars:<20} C:{ch['coherence']:.2f} S:{ch['stability']:.2f} I:{ch['integrity']:.2f}"
