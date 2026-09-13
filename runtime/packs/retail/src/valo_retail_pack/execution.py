from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Protocol

from .contracts import Decision, RetailActionIntentV1, RetailExecutionReceiptV1
from .policy import evaluate_retail_intent


@dataclass(frozen=True)
class RehtPermit:
    tenant_id: str
    idempotency_key: str
    authorized_action: dict[str, Any]
    valid_at_execution: bool


@dataclass(frozen=True)
class ProviderResult:
    ok: bool
    response: dict[str, Any]
    after_state: dict[str, Any] | None
    error: str | None = None


class ProviderAdapter(Protocol):
    def execute(self, request: dict[str, Any]) -> ProviderResult: ...
    def read_state(self, resource_id: str) -> dict[str, Any]: ...


class VeritasSink(Protocol):
    def append(self, receipt_payload: dict[str, Any]) -> str: ...


class RetailExecutor:
    def __init__(self) -> None:
        self._executed: set[tuple[str, str]] = set()

    def execute(self, *, intent: RetailActionIntentV1, permit: RehtPermit | None, adapter: ProviderAdapter,
                veritas: VeritasSink, now_ns: int, shadow: bool = False) -> RetailExecutionReceiptV1:
        policy = evaluate_retail_intent(intent, now_ns=now_ns)
        before = adapter.read_state(intent.resource_id)

        if before != intent.expected_before_state or str(before.get("version")) != intent.expected_version:
            decision, error = Decision.DENY, "compare-state failed"
            return self._receipt(intent, {}, None, before, None, decision, "NOT_EXECUTED", error, None, veritas)
        if policy.decision is not Decision.ALLOW:
            return self._receipt(intent, {}, None, before, None, policy.decision, "NOT_EXECUTED", policy.reason, None, veritas)
        if permit is None or not permit.valid_at_execution:
            return self._receipt(intent, {}, None, before, None, Decision.DENY, "NOT_EXECUTED", "missing/invalid reht permit", None, veritas)
        if permit.tenant_id != intent.tenant_id or permit.idempotency_key != intent.idempotency_key:
            return self._receipt(intent, {}, None, before, None, Decision.DENY, "NOT_EXECUTED", "permit binding mismatch", None, veritas)

        key = (intent.tenant_id, intent.idempotency_key)
        if key in self._executed:
            return self._receipt(intent, permit.authorized_action, None, before, None, Decision.DENY, "NOT_EXECUTED", "duplicate idempotency key", None, veritas)

        request = dict(permit.authorized_action)
        if shadow:
            return self._receipt(intent, request, request, before, before, Decision.ALLOW, "SHADOW_ONLY", None, None, veritas)

        result = adapter.execute(request)
        response_hash = sha256(json.dumps(result.response, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if not result.ok:
            return self._receipt(intent, request, request, before, None, Decision.ALLOW, "NOT_EXECUTED", result.error or "provider error", response_hash, veritas)

        after = adapter.read_state(intent.resource_id)
        self._executed.add(key)
        return self._receipt(intent, request, request, before, after, Decision.ALLOW, "EXECUTED", None, response_hash, veritas)

    def _receipt(self, intent, authorized, provider_request, before, after, decision, result, error, response_hash, veritas):
        payload = {
            "tenant_id": intent.tenant_id,
            "idempotency_key": intent.idempotency_key,
            "decision": decision.value,
            "result": result,
            "before_state": before,
            "after_state": after,
            "authority_chain": list(intent.authority_chain),
        }
        ref = veritas.append(payload)
        return RetailExecutionReceiptV1(
            tenant_id=intent.tenant_id,
            idempotency_key=intent.idempotency_key,
            proposed_action=intent.desired_change,
            authorized_action=authorized,
            provider_request=provider_request,
            before_state=before,
            after_state=after,
            result=result,
            error=error,
            provider_response_hash=response_hash,
            decision=decision,
            authority_chain=intent.authority_chain,
            reversal_ref=None,
            veritas_receipt_ref=ref,
        )
