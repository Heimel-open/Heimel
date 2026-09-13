"""Operator binding for Health Pack intake proposals.

The Health Pack stays independent of Operator. This adapter converts a bounded,
non-authoritative HealthWorkProposalV1 into the existing CandidateOperation.
That still does not create a session, permit, authority or REHT decision.
"""

from __future__ import annotations

from valo_health_pack.intake import HealthWorkProposalV1

from .frontline import CandidateOperation


def bind_health_work_proposal(proposal: HealthWorkProposalV1) -> CandidateOperation:
    """Compile a health proposal into the existing frontline candidate shape."""
    return CandidateOperation(
        correlation_id=proposal.correlation_id,
        source_interaction_id=proposal.source_intake_ref,
        function_id=proposal.function_id,
        function_version=proposal.function_version,
        inputs={proposal.input_name: proposal.inputs},
        route_hint="health",
    )
