"""Canonical OWASP Top 10 for LLM Applications 2026 crosswalk for REHT.

This module does not add ten new security mechanisms. It records which existing
VALO boundary owns or contributes to each OWASP risk, what REHT can prove, and
what remains outside REHT. The executable acceptance suite consumes this data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OwaspRisk:
    risk_id: str
    title: str
    reht_role: str
    boundaries: tuple[str, ...]
    controls: tuple[str, ...]
    evidence: tuple[str, ...]
    negative_tests: tuple[str, ...]
    residual_or_external: tuple[str, ...] = ()


OWASP_LLM_2026: tuple[OwaspRisk, ...] = (
    OwaspRisk(
        "LLM01",
        "Prompt Injection",
        "CONTRIBUTING",
        ("upstream ingest/admissibility", "REHT", "external execution boundary"),
        (
            "model output cannot create identity or authority",
            "revalidate principal, capability, scope, purpose, constraints and freshness at execution",
            "bind permit to the exact action contract",
        ),
        ("DENY reason", "execution_context_hash", "action-bound clearance/permit on ALLOW"),
        (
            "tests/test_owasp_llm_2026_acceptance.py::test_llm01_injected_capability_cannot_create_authority",
            "tests/test_owasp_llm_2026_acceptance.py::test_llm01_injected_target_cannot_escape_scope",
        ),
        ("modality filtering, memory/RAG isolation and prompt-injection detection are outside REHT",),
    ),
    OwaspRisk(
        "LLM02",
        "Sensitive Information Disclosure",
        "CONTRIBUTING",
        ("governed projection/data plane", "REHT", "external PEP"),
        ("principal binding", "scope binding", "purpose binding", "least-privilege action authorization"),
        ("DENY reason", "execution_context_hash", "permit_ref"),
        (
            "tests/test_owasp_llm_2026_acceptance.py::test_llm02_cross_scope_action_is_denied",
            "tests/test_reht.py::test_deny_required_purpose_not_permitted",
        ),
        ("authorize-before-retrieval, redaction, DLP and log hygiene are outside REHT",),
    ),
    OwaspRisk(
        "LLM03",
        "Excessive Agency",
        "PRIMARY",
        ("REHT", "EAR v1", "external execution boundary"),
        (
            "minimum authorized capability and scope",
            "execute in the bound principal context",
            "complete deterministic pre-execution mediation",
            "fresh authority revalidation",
            "verified human/dual-control gates for protected actions",
        ),
        ("DENY reason", "execution_context_hash", "action-bound clearance_ref", "action-bound permit_ref"),
        (
            "tests/test_owasp_llm_2026_acceptance.py::test_llm03_excess_tool_functionality_cannot_expand_capability",
            "tests/test_reht.py::test_deny_wrong_principal",
            "tests/test_execution_requirements.py::test_ea11_denies_high_impact_without_explicit_gate_policy",
            "tests/test_execution_requirements.py::test_ea06_denies_transitive_multi_hop_authority",
        ),
    ),
    OwaspRisk(
        "LLM04",
        "Supply Chain",
        "EXTERNAL",
        ("MAL", "build/release provenance", "signed artifact verification"),
        ("admit only approved model/tool artifacts and pinned dependencies",),
        ("artifact identity", "provenance/signature evidence", "admissibility decision"),
        ("external:supply-chain-tamper-rejection",),
        ("REHT does not validate model, dataset, package, MCP or tool supply chains",),
    ),
    OwaspRisk(
        "LLM05",
        "Data and Model Poisoning",
        "CONTRIBUTING",
        ("upstream ingest/admissibility", "MAL", "EAR v1", "REHT"),
        ("require fresh admissible evidence when policy marks it required", "require current reality validation"),
        ("evidence_ref", "reality-validation evidence_ref", "DENY reason"),
        (
            "tests/test_execution_requirements.py::test_ea08_denies_missing_required_evidence",
            "tests/test_execution_requirements.py::test_ea09_denies_unverified_reality",
        ),
        ("poison detection and corpus/model repair are outside REHT",),
    ),
    OwaspRisk(
        "LLM06",
        "Unbounded Consumption",
        "EXTERNAL",
        ("external PEP", "resource/cost budget", "circuit breaker"),
        ("per-user/per-workload budgets", "rate limits", "fan-out and recursion circuit breakers"),
        ("budget/usage receipt", "halt/escalation event"),
        ("external:resource-budget-exhaustion",),
        ("REHT currently has no resource-consumption accounting primitive",),
    ),
    OwaspRisk(
        "LLM07",
        "Misinformation",
        "CONTRIBUTING",
        ("evidence/admissibility producers", "EAR v1", "REHT"),
        (
            "required evidence must be valid and fresh",
            "required reality validation must match current state",
            "verified prior outcomes may gate recursive execution",
        ),
        ("evidence_ref", "reality evidence_ref", "verified outcome evidence", "DENY reason"),
        (
            "tests/test_execution_requirements.py::test_ea08_denies_missing_required_evidence",
            "tests/test_execution_requirements.py::test_ea09_denies_unverified_reality",
        ),
        ("REHT does not decide whether arbitrary model prose is true",),
    ),
    OwaspRisk(
        "LLM08",
        "Hidden Context Exposure",
        "EXTERNAL",
        ("context construction/governed projection", "secret management", "tool boundary"),
        ("do not use hidden prompts as an authorization boundary", "keep credentials outside model context"),
        ("context/projection audit", "secret-access audit"),
        ("external:hidden-context-secret-exposure",),
        ("REHT authorization is deterministic code and authority state; prompt secrecy is not a REHT control",),
    ),
    OwaspRisk(
        "LLM09",
        "Vector and Embedding Weaknesses",
        "CONTRIBUTING",
        ("retrieval/index authorization", "upstream ingest/admissibility", "REHT"),
        ("authorize retrieval upstream", "revalidate downstream action scope and purpose before consequence"),
        ("retrieval authorization evidence", "REHT DENY reason/permit"),
        (
            "tests/test_owasp_llm_2026_acceptance.py::test_llm09_retrieved_content_cannot_expand_action_scope",
        ),
        ("embedding inversion, index ACLs, tenant isolation and poisoning defenses are outside REHT",),
    ),
    OwaspRisk(
        "LLM10",
        "Improper Output Handling",
        "CONTRIBUTING",
        ("trusted application validation", "REHT", "external execution boundary"),
        (
            "LLM output is candidate action data, not authority",
            "validate authorization in deterministic logic",
            "bind authorization artifact to the exact action contract",
        ),
        ("action-bound permit_ref", "clearance_ref", "execution_context_hash"),
        (
            "tests/test_owasp_llm_2026_acceptance.py::test_llm10_changed_model_output_invalidates_prior_permit_binding",
            "tests/test_reht.py::test_permit_binds_full_action_contract",
        ),
        ("encoding/escaping and downstream parser safety remain application/PEP responsibilities",),
    ),
)

OWASP_LLM_2026_BY_ID = {risk.risk_id: risk for risk in OWASP_LLM_2026}
