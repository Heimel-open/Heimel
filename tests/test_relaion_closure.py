from dataclasses import replace

from paios.relaion_asset_pool import AssetProfile, ServiceRequirement, build_pool_offer
from paios.relaion_closure import ClosureState, asset_pool_contract, run_asset_pool_closure


def _offer():
    return build_pool_offer(
        AssetProfile("asset-1", "owner-1", "cottage", "NO", 100_000, 2_000_000, 20),
        owner_days_reserved=30,
        expected_daily_revenue=2_000,
        expected_occupancy=0.2,
        services=(ServiceRequirement("cleaning", "before_guest", 500),),
        risks=(),
    )


def test_asset_pool_closure_reaches_verified_with_exact_scope_and_integration_proof():
    result = run_asset_pool_closure(
        _offer(),
        contract=asset_pool_contract(canonical_target="nsolland/PersonalAI-OS:main"),
        actor_id="relaion-1",
        mandate_id="mandate-1",
        policy_id="asset-pool-v1",
        builder_id="builder-1",
        verifier_id="auditor-1",
        canonical_integration_ref="nsolland/PersonalAI-OS@615f64b0a701385e9f3f5a4adca0ff2ff2161151",
    )
    assert result.state is ClosureState.COMPLETED_VERIFIED
    assert [event.kind for event in result.events] == [
        "need_bound", "contract_bound", "implementation_bound", "execution_observed",
        "evidence_emitted", "verification_recorded", "independent_sign_off", "canonical_integration",
    ]


def test_closure_fails_closed_without_canonical_integration_proof():
    result = run_asset_pool_closure(
        _offer(), contract=asset_pool_contract(canonical_target="nsolland/PersonalAI-OS:main"),
        actor_id="relaion-1", mandate_id="m", policy_id="p", builder_id="b", verifier_id="v",
        canonical_integration_ref="local-branch",
    )
    assert result.state is ClosureState.UNKNOWN
    assert result.verification.reason == "canonical_integration_proof_required"
    assert not result.events


def test_builder_cannot_self_close():
    result = run_asset_pool_closure(
        _offer(), contract=asset_pool_contract(canonical_target="nsolland/PersonalAI-OS:main"),
        actor_id="relaion-1", mandate_id="m", policy_id="p", builder_id="same", verifier_id="same",
        canonical_integration_ref="nsolland/PersonalAI-OS@615f64b0a701385e9f3f5a4adca0ff2ff2161151",
    )
    assert result.state is ClosureState.UNKNOWN
    assert result.verification.reason == "builder_self_verification"


def test_scope_mismatch_is_unknown():
    contract = replace(asset_pool_contract(canonical_target="nsolland/PersonalAI-OS:main"), acceptance_scope="wrong.scope")
    result = run_asset_pool_closure(
        _offer(), contract=contract, actor_id="relaion-1", mandate_id="m", policy_id="p", builder_id="b", verifier_id="v",
        canonical_integration_ref="nsolland/PersonalAI-OS@615f64b0a701385e9f3f5a4adca0ff2ff2161151",
    )
    assert result.state is ClosureState.UNKNOWN
    assert result.verification.reason == "scope_mismatch"
