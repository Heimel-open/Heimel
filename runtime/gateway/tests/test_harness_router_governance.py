import pytest

from valo_gateway.harness import BaseRuntimeAdapter, HarnessRouter
from valo_gateway.harness_conformance import (
    HarnessAdmissionEvidence,
    HarnessDescriptor,
    HarnessState,
)


def admission(*, residual_ok: bool = True):
    incoming = HarnessDescriptor(
        harness_id="provider-internal",
        version="v1",
        config_digest="sha256:" + "a" * 64,
        provenance_ref="provider:internal:v1",
        state=HarnessState.KNOWN,
    )
    external = HarnessDescriptor(
        harness_id="heimel-external",
        version="v1",
        config_digest="sha256:" + "b" * 64,
        provenance_ref="heimel:harness:v1",
        state=HarnessState.KNOWN,
    )
    return HarnessAdmissionEvidence(
        incoming_harness=incoming,
        external_harness=external,
        pre_induction_assessed=True,
        controlled_regrounding_applied=True,
        residual_induction_measured=True,
        residual_induction_within_bound=residual_ok,
        equivalence_scope="bounded-task-profile-v1",
        evidence_ref="veritas:harness-admission-1",
    )


def router():
    return HarnessRouter({"local": BaseRuntimeAdapter()})


def test_non_consequence_bearing_internal_work_can_run_without_admission():
    action_id = router().submit({"type": "simulate", "consequence_bearing": False})
    assert action_id.startswith("act-")


def test_consequence_bearing_work_requires_harness_admission():
    with pytest.raises(ValueError, match="requires governed harness admission"):
        router().submit({"type": "act", "consequence_bearing": True})


def test_consequence_bearing_work_passes_with_admitted_harness_transition():
    action_id = router().submit(
        {"type": "act", "consequence_bearing": True},
        harness_admission=admission(),
    )
    assert action_id.startswith("act-")


def test_residual_induction_out_of_bound_blocks_runtime_submission():
    with pytest.raises(ValueError, match="NO_UNGOVERNED_HARNESS_TRANSITION"):
        router().submit(
            {"type": "act", "consequence_bearing": True},
            harness_admission=admission(residual_ok=False),
        )
