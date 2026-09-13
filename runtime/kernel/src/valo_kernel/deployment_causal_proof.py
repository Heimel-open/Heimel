from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .causal_capacity import CausalCapacityAssessment
from .effect_boundary import BoundaryDisposition


class DeploymentCausalPathProof(BaseModel):
    """Bounded evidence contract for a concrete deployment claim.

    This does not manufacture completeness. The caller must provide the declared
    reachable path inventory produced by architecture analysis, threat modeling,
    runtime discovery or other evidence. Any mismatch or unknown path fails closed.
    """

    schema_version: Literal["deployment_causal_path_proof.v1"] = (
        "deployment_causal_path_proof.v1"
    )
    deployment_id: str
    assessed_source_commit: str
    declared_reachable_channel_ids: tuple[str, ...]
    assessed_channel_ids: tuple[str, ...]
    unknown_paths_fail_closed: bool
    boundary_assessment: CausalCapacityAssessment
    inventory_evidence_refs: tuple[str, ...]
    enforcement_evidence_refs: tuple[str, ...]
    coverage_assertion: Literal["BOUNDED_DECLARED_REACHABILITY"] = (
        "BOUNDED_DECLARED_REACHABILITY"
    )

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_identity(self) -> "DeploymentCausalPathProof":
        if not self.deployment_id or not self.assessed_source_commit:
            raise ValueError("deployment identity and source commit are required")
        if len(self.declared_reachable_channel_ids) != len(
            set(self.declared_reachable_channel_ids)
        ):
            raise ValueError("declared reachable channel IDs must be unique")
        if len(self.assessed_channel_ids) != len(set(self.assessed_channel_ids)):
            raise ValueError("assessed channel IDs must be unique")
        return self

    @property
    def inventory_complete_for_declared_scope(self) -> bool:
        return set(self.declared_reachable_channel_ids) == set(self.assessed_channel_ids)

    @property
    def evidence_present(self) -> bool:
        return bool(self.inventory_evidence_refs) and bool(self.enforcement_evidence_refs)

    @property
    def conformant_for_declared_scope(self) -> bool:
        return all(
            (
                self.inventory_complete_for_declared_scope,
                self.unknown_paths_fail_closed,
                self.evidence_present,
                self.boundary_assessment.disposition
                in (BoundaryDisposition.GOVERNED, BoundaryDisposition.INTERNAL_ONLY),
            )
        )
