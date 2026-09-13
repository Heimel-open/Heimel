from __future__ import annotations

from valo_workflow_isa import compile_graph as isa_compile

from valo_public_pack import build_golden_graph, build_public_registry, compile_golden
from valo_public_pack.functions import CORE_REUSE_CHECK


def test_pack_reuses_exact_core_functions() -> None:
    """The golden graph references the exact core Function versions that run
    through the runtime (no forks)."""
    registry = build_public_registry()
    used = {call.function_ref.function_id for call in build_golden_graph(registry).nodes}
    for core in CORE_REUSE_CHECK:
        assert core in used, f"pack must reuse core Function {core}"
        assert registry.resolve(core, "1.0.0") is not None


def test_no_public_leakage_into_core() -> None:
    """Public types never appear in Kernel/ISA core; the pack layers domain
    semantics on top."""
    registry = build_public_registry()
    identity = registry.resolve("valo.identity.verify_identity")
    assert "Case" not in identity.input_type.type
    assert "PublicDecision" not in identity.output_type.type


def test_no_writes_bypass_isa_reht() -> None:
    registry = build_public_registry()
    for function_id in ["valo.public.issue_public_decision", "valo.public.notify", "valo.public.create_appeal_right", "valo.public.close_case"]:
        workflow = registry.graph_for(registry.get(f"{function_id}@1.0.0"))
        write = [n for n in workflow.nodes if n.node_class.value == "WRITE"]
        assert write and write[0].policies.authority is not None, f"{function_id} must carry an authority boundary"


def test_compiled_golden_is_valid_isa() -> None:
    isa_compile(compile_golden(build_public_registry()).workflow_graph)


def test_no_local_authorization_boundary() -> None:
    """The pack has no local REHT: the real REHT (the valo-reht package, a
    separate v1.1-candidate dependency) decides solely on the Kernel-produced
    execution context. The pack owns no authorize() logic."""
    from valo_reht import RealReht

    reht = RealReht()
    base = {
        "actor": "system-1",
        "identity": "id-system-1",
        "time": {"now": "2026-08-08T00:00:00+00:00"},
    }
    assert reht.authorize({**base, "authority": []}, {"capability": "ISSUE_DECISION", "target": "case-1"}).decision == "DENY"
    assert reht.authorize({**base, "authority": []}, {"capability": "ISSUE_DECISION"}).decision == "DENY"
    # an in-scope, in-principal, active, timezone-aware authority allows
    assert reht.authorize(
        {**base, "authority": [{
            "authority_id": "auth-1", "principal": "system-1", "capability": "ISSUE_DECISION",
            "scope": ["case-1"], "status": "ACTIVE",
            "validity": {"valid_from": "2020-01-01T00:00:00+00:00", "valid_until": "2100-01-01T00:00:00+00:00"},
        }]},
        {"capability": "ISSUE_DECISION", "target": "case-1"},
    ).decision == "ALLOW"


def test_no_legal_llm_authority() -> None:
    """The LLM cannot alone declare legal basis authoritative or grant
    competence: both are Kernel authorities with explicit validity, checked by
    REHT at the write boundary."""
    registry = build_public_registry()
    decision = registry.get("valo.public.issue_public_decision@1.0.0")
    # autonomy is STEP_UP for a rights-impacting decision, never AUTO
    assert "AUTO_EXECUTE" not in {a.value for a in decision.autonomy_profile.allowed_autonomy_levels}
