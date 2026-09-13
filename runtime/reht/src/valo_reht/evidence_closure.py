"""Mandatory execution-evidence closure for the two-core runtime.

The consequence path is not evidence-closed until the exact EffectBoundary
receipt has been admitted to Veritas WORM and that Veritas-backed outcome has
been appended to Kernel history. Neither step can grant or extend authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping, Protocol

from .runtime_interlocks import ExecutionReceipt

_EFFECT_BOUNDARY_SCHEMA = "valo.reht.effect-boundary-observation.v1"


@dataclass(frozen=True)
class EvidenceClosure:
    """Non-authoritative proof that execution evidence reached both durable legs."""

    receipt_id: str
    veritas_ref: str | None
    kernel_ref: str | None
    closed: bool
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("evidence closure cannot grant authority")
        if self.closed and (not self.veritas_ref or not self.kernel_ref):
            raise ValueError("closed evidence requires Veritas and Kernel references")


class EvidenceClosureError(RuntimeError):
    """Evidence could not be closed after a terminal boundary observation."""

    def __init__(
        self,
        message: str,
        *,
        receipt_id: str,
        stage: str,
        veritas_ref: str | None = None,
    ) -> None:
        super().__init__(message)
        self.receipt_id = receipt_id
        self.stage = stage
        self.veritas_ref = veritas_ref


class ExecutionEvidenceClosureSink(Protocol):
    """Terminal evidence sink used by production EffectBoundary."""

    def close(self, receipt: ExecutionReceipt) -> EvidenceClosure: ...


class VeritasEvidenceAdmissionPort(Protocol):
    """Structural port implemented by VeritasChainService."""

    def store_effect_boundary_execution_observation(
        self,
        payload: Mapping[str, Any],
    ) -> str: ...


class KernelOutcomeAdmissionPort(Protocol):
    """Structural port implemented by KernelExecutionOutcomeConsumer."""

    def append_verified_execution_outcome(
        self,
        outcome: Mapping[str, Any],
    ) -> str: ...


class DevelopmentEvidenceClosureSink:
    """Explicit test/dev sink. It records receipts but never claims closure."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._receipts: list[ExecutionReceipt] = []

    def close(self, receipt: ExecutionReceipt) -> EvidenceClosure:
        with self._lock:
            self._receipts.append(receipt)
        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref=None,
            kernel_ref=None,
            closed=False,
        )

    def receipts(self) -> list[ExecutionReceipt]:
        with self._lock:
            return list(self._receipts)


class VeritasKernelExecutionEvidenceSink:
    """Production sink: EffectBoundary -> Veritas WORM -> Kernel history.

    The exact REHT receipt is first verified and durably admitted by Veritas.
    Only the resulting WORM reference is then supplied to Kernel's verified
    outcome consumer. A failure at either leg raises and no closed result is
    returned. The sink performs no authorization logic.
    """

    def __init__(
        self,
        *,
        veritas: VeritasEvidenceAdmissionPort,
        kernel: KernelOutcomeAdmissionPort,
    ) -> None:
        self._veritas = veritas
        self._kernel = kernel

    @staticmethod
    def _veritas_ref(value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("Veritas WORM admission returned no reference")
        if value.startswith("veritas-worm:"):
            return value
        if value.startswith("sha256:"):
            return "veritas-worm:" + value
        return "veritas-worm:sha256:" + value

    def close(self, receipt: ExecutionReceipt) -> EvidenceClosure:
        payload = {"schema": _EFFECT_BOUNDARY_SCHEMA, **receipt.to_dict()}
        try:
            worm_hash = self._veritas.store_effect_boundary_execution_observation(payload)
            veritas_ref = self._veritas_ref(worm_hash)
        except Exception as exc:
            raise EvidenceClosureError(
                f"VERITAS_EVIDENCE_ADMISSION_FAILED:{type(exc).__name__}",
                receipt_id=receipt.receipt_id,
                stage="VERITAS",
            ) from exc

        outcome = {
            "receipt_id": receipt.receipt_id,
            "veritas_ref": veritas_ref,
            "status": receipt.status,
            "action_digest": receipt.action_digest,
            "execution_context_hash": receipt.execution_context_hash,
            "reht_decision": receipt.reht_decision,
            "clearance_ref": receipt.clearance_ref,
            "permit_ref": receipt.permit_ref,
            "effect_result_digest": receipt.effect_result_digest,
            "observed_at": receipt.created_at,
            "postconditions_verified": receipt.postconditions_verified,
            "authority_granted": False,
        }
        try:
            kernel_ref = self._kernel.append_verified_execution_outcome(outcome)
            if not isinstance(kernel_ref, str) or not kernel_ref:
                raise ValueError("Kernel outcome admission returned no reference")
        except Exception as exc:
            raise EvidenceClosureError(
                f"KERNEL_OUTCOME_ADMISSION_FAILED:{type(exc).__name__}",
                receipt_id=receipt.receipt_id,
                stage="KERNEL",
                veritas_ref=veritas_ref,
            ) from exc

        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref=veritas_ref,
            kernel_ref=kernel_ref,
            closed=True,
        )


__all__ = [
    "DevelopmentEvidenceClosureSink",
    "EvidenceClosure",
    "EvidenceClosureError",
    "ExecutionEvidenceClosureSink",
    "KernelOutcomeAdmissionPort",
    "VeritasEvidenceAdmissionPort",
    "VeritasKernelExecutionEvidenceSink",
]
