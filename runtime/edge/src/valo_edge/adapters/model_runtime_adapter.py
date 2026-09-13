"""Model runtime adapter interface (RunAnywhere / LiteRT.js candidate interface)."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from valo_edge.contracts import EdgeActionProposal, EdgeClearance, EdgeExecutionReceipt


class ModelRuntimeAdapter(ABC):
    """Abstract model runtime boundary. Ensures local LLM / SLM models only propose actions
    and do not dereference physical actuators directly."""

    @abstractmethod
    def generate_proposal(
        self,
        context_prompt: str,
        sensor_data: Dict[str, Any],
        timestamp_iso: str,
    ) -> EdgeActionProposal:
        """Generates a proposed device action based on model inference."""
        pass
