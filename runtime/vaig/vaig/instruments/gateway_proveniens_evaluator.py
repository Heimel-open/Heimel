"""Gatway Proveniens Evaluator — evalueringskontekst for gateway provenance.

Vurderer om ein MCP Gateway-innvokasjon har gyldig, fullstendig og
kontinuerleg provenance-kjede. Koblar mot WORM-logg for etterprøvbarhet.

Bruksområde:
  - Etter kvart MCP Gateway tool-kall verifisere at provenance er intakt
  - Oppdage manglande, brotne eller manipulerte provenance-kjeder
  - Rapportere provenance-helse tilbake til dirigent/orkestrator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ProvenanceEvaluation:
    """Resultat av éi provenance-evaluering."""

    invocation_id: str
    tool_id: str
    session_id: str
    client_id: str

    # Provenance-dimensjonar
    has_chain_id: bool = False
    chain_complete: bool = False
    has_timestamp: bool = False
    has_governance_decision: bool = False
    has_audit_link: bool = False
    arguments_redacted: bool = False

    # Samla vurdering
    score: float = 0.0  # 0.0–1.0
    verdict: str = "insufficient"  # full | partial | insufficient | failed
    details: list[str] = field(default_factory=list)
    evaluated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class GatewayProveniensEvaluator:
    """Vurderer gateway provenance-kvalitet for kvar tool-innvokasjon.

    Dette er evalueringskonteksten for gateway_proveniens — utvida som
    del av BO#34. Den kan brukast som eit VAIG-instrument i dirigentens
    instrument-orkester eller som ein frittståande sjekk i MCP Gateway-pipelinen.
    """

    def __init__(self) -> None:
        self._evaluations: list[ProvenanceEvaluation] = []

    def evaluate(
        self,
        invocation_id: str,
        tool_id: str,
        session_id: str,
        client_id: str,
        provenance_data: dict[str, Any] | None = None,
    ) -> ProvenanceEvaluation:
        """Køyr provenance-evaluering for éi innvokasjon.

        `provenance_data` kan innehalde nøklar som:
          - chain_id: unik kjede-ID
          - chain_links: liste over lenkjer i kjeda
          - governance_decision: governance-avgjerd
          - audit_ref: referanse til WORM-audit
          - redacted_args: bool
        """
        pd = provenance_data or {}

        has_chain_id = bool(pd.get("chain_id"))
        chain_complete = bool(pd.get("chain_links")) and len(pd.get("chain_links", [])) >= 1
        has_timestamp = bool(pd.get("timestamp"))
        has_governance_decision = bool(pd.get("governance_decision"))
        has_audit_link = bool(pd.get("audit_ref"))
        arguments_redacted = bool(pd.get("redacted_args", False))

        # Poengberekning: 6 dimensjonar
        dims = [
            has_chain_id,
            chain_complete,
            has_timestamp,
            has_governance_decision,
            has_audit_link,
            arguments_redacted,  # redacted er positivt — viser medvit om sensitivitet
        ]
        score = sum(1 for d in dims if d) / len(dims)

        # Verdict
        details = []
        if not has_chain_id:
            details.append("Manglar chain_id — kan ikkje knyte til provenance-kjede")
        if not chain_complete:
            details.append("Manglar chain_links — ufullstendig kjede")
        if not has_timestamp:
            details.append("Manglar timestamp")
        if not has_governance_decision:
            details.append("Manglar governance_decision")
        if not has_audit_link:
            details.append("Manglar audit_ref — ikkje knytt til WORM-logg")
        if arguments_redacted:
            details.append("Arguments er redacted — sensitive data skjerma")

        if score >= 0.83:
            verdict = "full"
        elif score >= 0.5:
            verdict = "partial"
        elif score >= 0.17:
            verdict = "insufficient"
        else:
            verdict = "failed"

        evaluation = ProvenanceEvaluation(
            invocation_id=invocation_id,
            tool_id=tool_id,
            session_id=session_id,
            client_id=client_id,
            has_chain_id=has_chain_id,
            chain_complete=chain_complete,
            has_timestamp=has_timestamp,
            has_governance_decision=has_governance_decision,
            has_audit_link=has_audit_link,
            arguments_redacted=arguments_redacted,
            score=score,
            verdict=verdict,
            details=details,
        )
        self._evaluations.append(evaluation)
        return evaluation

    def get_recent(self, limit: int = 10) -> list[ProvenanceEvaluation]:
        """Hent dei siste N evalueringane."""
        return self._evaluations[-limit:]

    @property
    def total_evaluations(self) -> int:
        return len(self._evaluations)

    @property
    def health_summary(self) -> dict[str, Any]:
        """Samla helsestatus for gateway provenance."""
        if not self._evaluations:
            return {"status": "no_data", "avg_score": 0.0, "count": 0}

        scores = [e.score for e in self._evaluations]
        verdicts = [e.verdict for e in self._evaluations]
        full_count = verdicts.count("full")
        partial_count = verdicts.count("partial")
        insufficient_count = verdicts.count("insufficient")
        failed_count = verdicts.count("failed")

        return {
            "status": "healthy" if full_count > partial_count else "degraded",
            "avg_score": sum(scores) / len(scores),
            "count": len(self._evaluations),
            "full": full_count,
            "partial": partial_count,
            "insufficient": insufficient_count,
            "failed": failed_count,
        }
