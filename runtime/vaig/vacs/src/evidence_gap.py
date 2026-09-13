"""
ACS Evidence Gap Analyzer v0.1
Simple rule-based evidence gap calculation.
"""

from typing import List, Dict, Any

class ACSEvidenceGapAnalyzer:
    """
    Calculates evidence gap: (required - present) / required
    This is "artificial cortisol" — stops agents from guessing.
    """

    EVIDENCE_REQUIREMENTS = {
        "modify_document": ["document", "policy"],
        "transfer_money": ["account", "authorization", "policy"],
        "send_email": ["recipient", "content"],
        "execute_code": ["code_review", "test_result", "policy"],
        "delete_data": ["authorization", "backup_confirmation", "policy"]
    }

    def calculate(self, packet: Dict[str, Any]) -> float:
        action = packet.get("intent", {}).get("action", "unknown")
        sources = packet.get("evidence", {}).get("sources", [])

        required_types = self.EVIDENCE_REQUIREMENTS.get(action, [])

        if not required_types:
            return 1.0  # Unknown action = maximum uncertainty

        present_types = set()
        for source in sources:
            if source.get("verified", False):
                present_types.add(source.get("type"))

        missing = len(required_types) - len(present_types.intersection(required_types))
        gap = max(0, missing) / len(required_types)

        return round(gap, 2)

    def get_requirements(self, action: str) -> List[str]:
        return self.EVIDENCE_REQUIREMENTS.get(action, [])
