"""Local VAIG Edge Profile: evidence evaluation without execution authority."""

from valo_edge.vaig.contracts import (
    DeviceAttestationEvidenceV1,
    EvidenceGapSeverity,
    EvidenceGapV1,
    EvidenceRequirementsV1,
    LocalVaigAssessmentV1,
    ModelSignalV1,
    PhysicalStateEvidenceV1,
    SensorEvidenceV1,
)
from valo_edge.vaig.evaluator import LocalVaigEdge

__all__ = [
    "DeviceAttestationEvidenceV1",
    "EvidenceGapSeverity",
    "EvidenceGapV1",
    "EvidenceRequirementsV1",
    "LocalVaigAssessmentV1",
    "LocalVaigEdge",
    "ModelSignalV1",
    "PhysicalStateEvidenceV1",
    "SensorEvidenceV1",
]
