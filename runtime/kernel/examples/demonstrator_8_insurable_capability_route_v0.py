"""Demonstrator 8: Insurable Capability Route v0.

Runs the existing sovereign personal-compute execution path, then binds its
route/effect evidence into a deterministic underwriting signal. This does not
price insurance or make an insurer decision.
"""

from examples.demonstrator_7_personal_compute_v0 import run as run_personal_compute
from valo_kernel.contracts.common import canonical_digest
from valo_kernel.kernel.insurable_route import (
    assess_insurable_route,
    seal_insurable_route_evidence,
)


def run() -> dict[str, object]:
    executed = run_personal_compute()
    route_evidence_digest = canonical_digest(
        {
            "route": executed["route"],
            "conformance": executed["conformance"],
            "state_root": executed["state_root"],
        }
    )
    evidence = seal_insurable_route_evidence(
        route_evidence_digest=route_evidence_digest,
        route_passed=executed["route"] == "PASS",
        reht_evaluation_id="reht-v0-eval-1",
        consequence_authorized=True,
        authority_fresh_at_consequence=True,
        receipt_digest=executed["receipt"],
        receipt_verified=True,
        consequence_limit_minor_units=50_000,
        provider_trust_domain="external",
        execution_replayable=True,
        state_integrity_verified=True,
    )
    assessment = assess_insurable_route(evidence)
    return {
        "execution_effect": executed["effect"],
        "route": executed["route"],
        "receipt": executed["receipt"],
        "insurability": assessment.outcome.value,
        "risk_band": assessment.risk_band.value,
        "risk_score": assessment.risk_score,
        "risk_factors": assessment.risk_factors,
        "assessment_digest": assessment.assessment_digest,
    }


def test_demonstrator_8_insurable_capability_route_v0() -> None:
    result = run()
    assert result["execution_effect"] == "BOOKED"
    assert result["route"] == "PASS"
    assert result["insurability"] == "ASSESSABLE"
    assert result["risk_band"] == "LOW"
    assert result["risk_score"] == 15


if __name__ == "__main__":
    print(run())
