from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError
from valo_kernel import (
    CandidateKind,
    Entity,
    EntityType,
    FailClosedError,
    ProjectionSelector,
    Provenance,
    Purpose,
    TimeWindow,
    WorldState,
    compile_governed_workspace,
    utcnow,
)

from valo_function_fabric import (
    FunctionWorkspacePlan,
    WorkspacePlanError,
    compile_function_workspace_plan,
)


def _purpose(*, scope: list[str] | None = None, purpose_type: str = "payment"):
    now = utcnow()
    return Purpose(
        purpose_id="purpose-pay",
        purpose_type=purpose_type,
        scope=scope or ["payment-1"],
        basis="invoice-obligation",
        permitted_data=["entities:payment-1"],
        permitted_actions=["PAY"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )


def _pay_plan(stdlib_registry, snapshot, **updates):
    definition = stdlib_registry.get("valo.finance.pay@1.0.0")
    values = {
        "workspace_id": "workspace-pay-1",
        "work_unit_id": "work-pay-1",
        "tenant_id": "tenant-a",
        "purpose": _purpose(),
        "selectors": (
            ProjectionSelector(
                collection="entities",
                object_ids=("payment-1",),
            ),
        ),
        "targets_by_capability": {"PAY": ("payment-1",)},
        "expires_at": utcnow() + timedelta(minutes=20),
        "parameter_constraints_by_capability": {
            "PAY": {"amount": {"required": True, "max": 1000}}
        },
    }
    values.update(updates)
    return compile_function_workspace_plan(definition, snapshot, **values)


def test_function_lowers_to_sealed_non_authoritative_workspace_plan(
    stdlib_registry,
    snapshot,
) -> None:
    plan = _pay_plan(stdlib_registry, snapshot)
    capability = plan.workspace_spec.capabilities[0]

    assert plan.plan_digest == plan.computed_digest
    assert plan.authority_effect == "none"
    assert plan.can_issue_clearance is False
    assert plan.direct_execution is False
    assert plan.final_authorization_boundary == "REHT"
    assert plan.workspace_spec.program_ref == "valo.finance.pay@1.0.0"
    assert plan.workspace_spec.program_digest == plan.program_digest
    assert plan.workspace_spec.allowed_output_kinds == (CandidateKind.EXTERNAL_ACTION,)
    assert plan.workspace_spec.step_up_required is True
    assert capability.capability == "PAY"
    assert capability.target_refs == ("payment-1",)
    assert capability.allowed_effects == ("MOVE_MONEY",)
    assert capability.parameter_constraints["amount"]["max"] == 1000


def test_kernel_compiles_plan_against_authoritative_purpose_and_state(
    stdlib_registry,
    snapshot,
) -> None:
    plan = _pay_plan(stdlib_registry, snapshot)
    purpose = _purpose()
    state = WorldState(
        tenant_id="tenant-a",
        entities={
            "payment-1": Entity(
                entity_id="payment-1",
                entity_type=EntityType.ACCOUNT,
                tenant_id="tenant-a",
                state="OPEN",
                provenance=Provenance(
                    source_type="system",
                    source_id="test",
                    source_system="kernel",
                ),
            )
        },
        purposes={purpose.purpose_id: purpose},
    )

    workspace = compile_governed_workspace(
        state,
        plan.workspace_spec,
        source_event_position=1,
    )
    assert workspace.spec.program_digest == plan.program_digest
    assert workspace.projection.source_state_root == state.root_hash()
    assert workspace.can_issue_clearance is False


def test_kernel_remains_final_owner_of_purpose_scope(
    stdlib_registry,
    snapshot,
) -> None:
    purpose = _purpose(scope=["another-payment"])
    plan = _pay_plan(stdlib_registry, snapshot, purpose=purpose)
    state = WorldState(tenant_id="tenant-a", purposes={purpose.purpose_id: purpose})

    with pytest.raises(FailClosedError, match="outside purpose scope"):
        compile_governed_workspace(
            state,
            plan.workspace_spec,
            source_event_position=0,
        )


def test_workspace_plan_rejects_unpinned_or_inactive_function(
    stdlib_registry,
    snapshot,
) -> None:
    definition = stdlib_registry.get("valo.finance.pay@1.0.0")
    with pytest.raises(WorkspacePlanError, match="active function"):
        compile_function_workspace_plan(
            definition.model_copy(update={"status": "DRAFT"}),
            snapshot,
            workspace_id="w",
            work_unit_id="u",
            tenant_id="tenant-a",
            purpose=_purpose(),
            selectors=(
                ProjectionSelector(
                    collection="entities",
                    object_ids=("payment-1",),
                ),
            ),
            targets_by_capability={"PAY": ("payment-1",)},
            expires_at=utcnow() + timedelta(minutes=5),
        )

    with pytest.raises(WorkspacePlanError, match="snapshot seal"):
        _pay_plan(
            stdlib_registry,
            snapshot.model_copy(update={"hash": "0" * 64}),
        )


@pytest.mark.parametrize(
    "targets",
    [
        {},
        {"PAY": ("*",)},
        {"PAY": ("payment-1", "payment-1")},
        {"PAY": ("payment-1",), "DELETE": ("payment-1",)},
    ],
)
def test_capability_targets_are_exact_and_explicit(
    stdlib_registry,
    snapshot,
    targets,
) -> None:
    with pytest.raises(WorkspacePlanError):
        _pay_plan(
            stdlib_registry,
            snapshot,
            targets_by_capability=targets,
        )


def test_effect_mapping_cannot_hide_or_invent_function_effects(
    stdlib_registry,
    snapshot,
) -> None:
    with pytest.raises(WorkspacePlanError, match="preserve the function effect"):
        _pay_plan(
            stdlib_registry,
            snapshot,
            effects_by_capability={"PAY": ("DELETE_DATA",)},
        )


def test_multi_capability_function_requires_explicit_effect_binding(
    stdlib_registry,
    snapshot,
) -> None:
    definition = stdlib_registry.get("valo.lifecycle.onboard@1.0.0")
    targets = {
        "REGISTER": ("person-1",),
        "ALLOCATE": ("resource-1",),
        "NOTIFY": ("person-1",),
    }
    with pytest.raises(WorkspacePlanError, match="explicit effect bindings"):
        compile_function_workspace_plan(
            definition,
            snapshot,
            workspace_id="workspace-onboard",
            work_unit_id="work-onboard",
            tenant_id="tenant-a",
            purpose=_purpose(),
            selectors=(
                ProjectionSelector(
                    collection="entities",
                    object_ids=("payment-1",),
                ),
            ),
            targets_by_capability=targets,
            expires_at=utcnow() + timedelta(minutes=5),
        )


def test_non_authority_function_receives_no_capability_lease(
    stdlib_registry,
    snapshot,
) -> None:
    definition = stdlib_registry.get("valo.identity.verify_identity@1.0.0")
    plan = compile_function_workspace_plan(
        definition,
        snapshot,
        workspace_id="workspace-verify",
        work_unit_id="work-verify",
        tenant_id="tenant-a",
        purpose=_purpose(),
        selectors=(
            ProjectionSelector(
                collection="entities",
                object_ids=("payment-1",),
            ),
        ),
        targets_by_capability={},
        expires_at=utcnow() + timedelta(minutes=5),
    )
    assert plan.workspace_spec.capabilities == ()
    assert plan.workspace_spec.max_actions == 0
    assert plan.workspace_spec.allowed_output_kinds == (CandidateKind.ARTIFACT,)


def test_plan_digest_detects_tampering(stdlib_registry, snapshot) -> None:
    plan = _pay_plan(stdlib_registry, snapshot)
    payload = plan.model_dump(mode="json")
    payload["function_identity"] = "valo.finance.refund@1.0.0"
    with pytest.raises(ValidationError, match="program reference"):
        FunctionWorkspacePlan.model_validate(payload)


def test_snapshot_workflow_graph_with_undeclared_effect_rejected(stdlib_registry) -> None:
    from valo_workflow_isa.contracts import (
        EffectType,
        NodeClass,
        TypedRef,
        WorkflowGraph,
        WorkflowNode,
    )

    # Create a definition declaring only PURE, but its snapshot workflow contains MOVE_MONEY
    node = WorkflowNode(
        id="bad", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        inputs=[TypedRef(name="x", type="any")], outputs=[TypedRef(name="y", type="any")],
        effect_type=EffectType.MOVE_MONEY,
        config={"target": "t", "actor": "a"},
    )
    bad_wf = WorkflowGraph(id="wf.bad_leak", version="1", input_schema={"x": "any"}, output_schema={"y": "any"}, nodes=[node], edges=[], entry="bad", terminal_states=["bad"])
    def_pure = stdlib_registry.get("valo.finance.price@1.0.0").model_copy(update={"workflow_ref": "wf.bad_leak"})

    # Store in registry
    from valo_function_fabric.contracts.common import canonical_digest
    from valo_function_fabric.contracts.registry import RegistryEntry

    f_hash = canonical_digest(def_pure.model_dump(mode="json"))
    stdlib_registry._functions[def_pure.identity] = RegistryEntry(definition=def_pure, function_hash=f_hash)
    stdlib_registry._graphs["wf.bad_leak"] = bad_wf
    snapshot = stdlib_registry.snapshot()

    with pytest.raises(WorkspacePlanError, match="undeclared effect"):
        compile_function_workspace_plan(
            def_pure,
            snapshot,
            workspace_id="w-bad",
            work_unit_id="u-bad",
            tenant_id="tenant-a",
            purpose=_purpose(),
            selectors=(ProjectionSelector(collection="entities", object_ids=("p-1",)),),
            targets_by_capability={},
            expires_at=utcnow() + timedelta(minutes=5),
        )

