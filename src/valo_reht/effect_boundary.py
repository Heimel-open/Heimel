"""Production mechanical effect boundary for the two-core runtime.

Kernel owns operative state. REHT owns execution authorization. Everything in
this module is subordinate mechanical enforcement: local stop probes, runtime
HALT/revocation, containment/path checks, single-use permits, resource-budget
consumption, boundary-only invocation and execution evidence.

No mechanism here can turn a non-ALLOW into authority or mint a clearance.
Production construction requires an explicitly production-safe permit store,
execution journal, and evidence-closure sink. Multi-host construction additionally
requires distributed-consensus scope for all mutable consequence state: permit
truth, execution journal, runtime HALT/revocation control and resource budgets.
Test/dev use must be explicit through :meth:`EffectBoundary.for_development`.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Any, Protocol, Sequence

from .consistency import (
    ConsistencyScope,
    DeploymentTopology,
    require_deployment_consistency,
)
from .contracts import DecisionResult, RehtPort
from .evidence_closure import (
    DevelopmentEvidenceClosureSink,
    EvidenceClosure,
    EvidenceClosureError,
    ExecutionEvidenceClosureSink,
)
from .execution_journal import (
    DevelopmentExecutionJournal,
    ExecutionJournal,
    ExecutionRecoveryRequired,
    inspect_recovery,
)
from .runtime_interlocks import (
    BoundaryEffect,
    ContainmentInterlock,
    ExecutionReceipt,
    MechanicalBlock,
    PostconditionChecker,
    PostconditionResult,
    PreCommitProbe,
    ProbeDisposition,
    ResourceBudgetLedger,
    RuntimeControlPlane,
    _BOUNDARY_PROOF,
    build_execution_receipt,
    canonical_digest,
)

ContextFactory = Callable[[dict[str, Any]], dict[str, Any]]


class EffectDenied(RuntimeError):
    """Mechanical refusal at the effect boundary."""

    def __init__(
        self,
        message: str,
        *,
        receipt: ExecutionReceipt | None = None,
        evidence_closure: EvidenceClosure | None = None,
    ) -> None:
        super().__init__(message)
        self.receipt = receipt
        self.evidence_closure = evidence_closure


class PermitStore(Protocol):
    """Atomic single-use permit store.

    Production implementations must explicitly declare ``production_safe=True``
    and provide shared/durable semantics appropriate to the deployment so
    restart or multi-worker execution cannot re-arm a consumed permit.
    """

    production_safe: bool
    consistency_scope: ConsistencyScope

    def consume_once(self, permit_ref: str) -> bool:
        """Atomically consume a permit; return False when already consumed."""

    def is_consumed(self, permit_ref: str) -> bool:
        """Return whether the permit has already been consumed."""


class InMemoryPermitStore:
    """Process-local permit store for tests and single-process development only."""

    production_safe = False
    consistency_scope = ConsistencyScope.PROCESS_LOCAL

    def __init__(self) -> None:
        self._consumed: set[str] = set()
        self._lock = Lock()

    def consume_once(self, permit_ref: str) -> bool:
        with self._lock:
            if permit_ref in self._consumed:
                return False
            self._consumed.add(permit_ref)
            return True

    def is_consumed(self, permit_ref: str) -> bool:
        with self._lock:
            return permit_ref in self._consumed


@dataclass(frozen=True)
class EffectCommitResult:
    """Result of one commit attempt through the production effect boundary."""

    decision: DecisionResult
    effect_committed: bool
    effect_result: Any | None = None
    receipt: ExecutionReceipt | None = None
    evidence_closure: EvidenceClosure | None = None
    valid_completion: bool = False
    postcondition: PostconditionResult | None = None


class EffectBoundary:
    """Single governed consequence path subordinate to REHT authorization.

    Production construction requires an explicit production-safe permit store,
    execution journal, and evidence sink. The journal is opened before permit
    consumption so a crash can never erase the existence of an execution
    attempt. No recovery path in this class replays an external effect.

    ``MULTI_HOST`` is a deployment claim, not an authority claim. It is accepted
    only when permit, journal, runtime-control and resource-ledger state all
    explicitly declare ``DISTRIBUTED_CONSENSUS`` consistency scope.
    """

    def __init__(
        self,
        permit_store: PermitStore,
        *,
        evidence_sink: ExecutionEvidenceClosureSink,
        execution_journal: ExecutionJournal,
        deployment_topology: DeploymentTopology | str = DeploymentTopology.SINGLE_HOST,
        runtime_control: RuntimeControlPlane | None = None,
        resource_ledger: ResourceBudgetLedger | None = None,
        containment: ContainmentInterlock | None = None,
        probes: Sequence[PreCommitProbe] = (),
        postcondition_checker: PostconditionChecker | None = None,
        _allow_unclosed_evidence: bool = False,
    ) -> None:
        if not _allow_unclosed_evidence and not bool(
            getattr(permit_store, "production_safe", False)
        ):
            raise ValueError(
                "production EffectBoundary requires explicitly production-safe "
                "shared/durable permit store; use EffectBoundary.for_development() "
                "for process-local stores"
            )
        if not _allow_unclosed_evidence and not bool(
            getattr(execution_journal, "production_safe", False)
        ):
            raise ValueError(
                "production EffectBoundary requires explicitly production-safe "
                "execution journal"
            )
        if isinstance(evidence_sink, DevelopmentEvidenceClosureSink) and not _allow_unclosed_evidence:
            raise ValueError(
                "production EffectBoundary cannot use development evidence sink; "
                "use EffectBoundary.for_development() explicitly"
            )

        resolved_runtime_control = runtime_control or RuntimeControlPlane()
        resolved_resource_ledger = resource_ledger or ResourceBudgetLedger()

        if _allow_unclosed_evidence:
            self._deployment_topology = DeploymentTopology.SINGLE_HOST
        else:
            self._deployment_topology = require_deployment_consistency(
                topology=deployment_topology,
                permit_store=permit_store,
                execution_journal=execution_journal,
                runtime_control=resolved_runtime_control,
                resource_ledger=resolved_resource_ledger,
            )
        self._permit_store = permit_store
        self._execution_journal = execution_journal
        self._runtime_control = resolved_runtime_control
        self._resource_ledger = resolved_resource_ledger
        self._containment = containment or ContainmentInterlock()
        self._evidence_sink = evidence_sink
        self._probes = tuple(probes)
        self._postcondition_checker = postcondition_checker
        self._require_closed_evidence = not _allow_unclosed_evidence

    @classmethod
    def for_development(
        cls,
        permit_store: PermitStore,
        *,
        runtime_control: RuntimeControlPlane | None = None,
        resource_ledger: ResourceBudgetLedger | None = None,
        containment: ContainmentInterlock | None = None,
        probes: Sequence[PreCommitProbe] = (),
        postcondition_checker: PostconditionChecker | None = None,
    ) -> "EffectBoundary":
        """Explicit process-local test/dev mode; never claims durable closure."""
        return cls(
            permit_store,
            evidence_sink=DevelopmentEvidenceClosureSink(),
            execution_journal=DevelopmentExecutionJournal(),
            runtime_control=runtime_control,
            resource_ledger=resource_ledger,
            containment=containment,
            probes=probes,
            postcondition_checker=postcondition_checker,
            _allow_unclosed_evidence=True,
        )

    @property
    def evidence_sink(self) -> ExecutionEvidenceClosureSink:
        return self._evidence_sink

    @property
    def execution_journal(self) -> ExecutionJournal:
        return self._execution_journal

    @property
    def deployment_topology(self) -> DeploymentTopology:
        return self._deployment_topology

    @property
    def runtime_control(self) -> RuntimeControlPlane:
        return self._runtime_control

    @property
    def resource_ledger(self) -> ResourceBudgetLedger:
        return self._resource_ledger

    def _record(
        self,
        *,
        status: str,
        action: dict[str, Any],
        execution_context_hash: str | None,
        decision: DecisionResult | None,
        effect: BoundaryEffect,
        effect_result: Any | None = None,
        reason: str | None = None,
        postconditions_verified: bool | None = None,
        journal_terminal: bool = False,
    ) -> tuple[ExecutionReceipt, EvidenceClosure]:
        receipt = build_execution_receipt(
            status=status,
            action=action,
            execution_context_hash=execution_context_hash,
            reht_decision=decision.decision if decision is not None else None,
            clearance_ref=decision.clearance_ref if decision is not None else None,
            permit_ref=decision.permit_ref if decision is not None else None,
            effect_name=effect.name,
            effect_result=effect_result,
            reason=reason,
            postconditions_verified=postconditions_verified,
        )
        permit_ref = decision.permit_ref if decision is not None else None
        if journal_terminal:
            if not permit_ref:
                raise RuntimeError("journal terminal receipt requires permit binding")
            self._execution_journal.mark_receipt_ready(permit_ref, receipt)
            self._execution_journal.mark_evidence_closing(permit_ref)
        closure = self._evidence_sink.close(receipt)
        if closure.receipt_id != receipt.receipt_id:
            raise EvidenceClosureError(
                "EVIDENCE_CLOSURE_RECEIPT_MISMATCH",
                receipt_id=receipt.receipt_id,
                stage="CLOSURE",
                veritas_ref=closure.veritas_ref,
            )
        if closure.authority_granted:
            raise EvidenceClosureError(
                "EVIDENCE_CLOSURE_CANNOT_GRANT_AUTHORITY",
                receipt_id=receipt.receipt_id,
                stage="CLOSURE",
                veritas_ref=closure.veritas_ref,
            )
        if self._require_closed_evidence and not closure.closed:
            raise EvidenceClosureError(
                "EVIDENCE_CLOSURE_INCOMPLETE",
                receipt_id=receipt.receipt_id,
                stage="CLOSURE",
                veritas_ref=closure.veritas_ref,
            )
        if journal_terminal:
            self._execution_journal.mark_closed(permit_ref, closure)
        return receipt, closure

    def _deny_mechanically(
        self,
        reason: str,
        *,
        action: dict[str, Any],
        execution_context_hash: str | None,
        decision: DecisionResult | None,
        effect: BoundaryEffect,
        journal_terminal: bool = False,
    ) -> None:
        receipt, closure = self._record(
            status="BLOCKED",
            action=action,
            execution_context_hash=execution_context_hash,
            decision=decision,
            effect=effect,
            reason=reason,
            journal_terminal=journal_terminal,
        )
        raise EffectDenied(
            reason,
            receipt=receipt,
            evidence_closure=closure,
        )

    def _assert_runtime_open(
        self,
        *,
        action: dict[str, Any],
        execution_context: dict[str, Any],
        execution_context_hash: str,
        decision: DecisionResult | None,
        effect: BoundaryEffect,
        journal_terminal: bool = False,
    ) -> None:
        reason = self._runtime_control.check(action, execution_context)
        if reason is not None:
            self._deny_mechanically(
                reason,
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
                journal_terminal=journal_terminal,
            )

    def _run_probes(
        self,
        *,
        action: dict[str, Any],
        execution_context: dict[str, Any],
        execution_context_hash: str,
        effect: BoundaryEffect,
    ) -> None:
        for probe in self._probes:
            try:
                result = probe.evaluate(action, execution_context)
            except Exception as exc:
                self._deny_mechanically(
                    f"PRECOMMIT_PROBE_FAILURE:{type(exc).__name__}",
                    action=action,
                    execution_context_hash=execution_context_hash,
                    decision=None,
                    effect=effect,
                )
            if result.disposition in {
                ProbeDisposition.BLOCK,
                ProbeDisposition.STEP_UP,
            }:
                reason = result.reason or f"PRECOMMIT_{result.disposition.value}"
                self._deny_mechanically(
                    reason,
                    action=action,
                    execution_context_hash=execution_context_hash,
                    decision=None,
                    effect=effect,
                )

    def _assert_containment(
        self,
        *,
        action: dict[str, Any],
        execution_context: dict[str, Any],
        execution_context_hash: str,
        decision: DecisionResult | None,
        effect: BoundaryEffect,
    ) -> None:
        reason = self._containment.check(action, execution_context)
        if reason is not None:
            self._deny_mechanically(
                reason,
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
            )

    def commit(
        self,
        *,
        reht: RehtPort,
        context_factory: ContextFactory,
        action_contract: dict[str, Any],
        effect: BoundaryEffect,
    ) -> EffectCommitResult:
        """Attempt one exact consequence transition."""
        if not isinstance(effect, BoundaryEffect):
            raise TypeError("production EffectBoundary requires BoundaryEffect")

        action = copy.deepcopy(action_contract)
        execution_context = copy.deepcopy(context_factory(copy.deepcopy(action)))
        execution_context_hash = _digest(execution_context)

        self._assert_runtime_open(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            decision=None,
            effect=effect,
        )
        self._run_probes(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            effect=effect,
        )
        self._assert_containment(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            decision=None,
            effect=effect,
        )

        decision = reht.authorize(execution_context, action)
        if decision.decision != "ALLOW":
            receipt, closure = self._record(
                status="NOT_COMMITTED",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
                reason=decision.reason or decision.decision,
            )
            return EffectCommitResult(
                decision=decision,
                effect_committed=False,
                receipt=receipt,
                evidence_closure=closure,
                valid_completion=False,
            )

        permit_ref = decision.permit_ref
        if not permit_ref:
            self._deny_mechanically(
                "ALLOW_WITHOUT_REHT_PERMIT",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
            )
        if not decision.clearance_ref:
            self._deny_mechanically(
                "ALLOW_WITHOUT_CLEARANCE_REF",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
            )
        if not decision.execution_context_hash:
            self._deny_mechanically(
                "ALLOW_WITHOUT_EXECUTION_CONTEXT_BINDING",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
            )
        if execution_context_hash != decision.execution_context_hash:
            self._deny_mechanically(
                "EXECUTION_CONTEXT_BINDING_MISMATCH",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
            )

        self._assert_runtime_open(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            decision=decision,
            effect=effect,
        )
        self._assert_containment(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            decision=decision,
            effect=effect,
        )

        opened = self._execution_journal.open_intent(
            permit_ref=permit_ref,
            action_digest=canonical_digest(action),
            execution_context_hash=execution_context_hash,
            clearance_ref=decision.clearance_ref,
            effect_name=effect.name,
        )
        if not opened:
            raise ExecutionRecoveryRequired(
                inspect_recovery(
                    journal=self._execution_journal,
                    permit_store=self._permit_store,
                    permit_ref=permit_ref,
                )
            )

        if not self._permit_store.consume_once(permit_ref):
            self._deny_mechanically(
                "PERMIT_REPLAY",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
                journal_terminal=True,
            )

        reservation_id = action.get("resource_reservation_id")
        if action.get("resource_bounds_required") and not reservation_id:
            self._deny_mechanically(
                "RESOURCE_RESERVATION_REQUIRED",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
                journal_terminal=True,
            )
        if reservation_id:
            try:
                consumed = self._resource_ledger.consume_once(
                    str(reservation_id),
                    action_digest=canonical_digest(action),
                    permit_ref=permit_ref,
                )
            except MechanicalBlock as exc:
                self._deny_mechanically(
                    str(exc),
                    action=action,
                    execution_context_hash=execution_context_hash,
                    decision=decision,
                    effect=effect,
                    journal_terminal=True,
                )
            if not consumed:
                self._deny_mechanically(
                    "RESOURCE_RESERVATION_REPLAY",
                    action=action,
                    execution_context_hash=execution_context_hash,
                    decision=decision,
                    effect=effect,
                    journal_terminal=True,
                )

        # A HALT/revocation may arrive after the earlier post-REHT check while
        # permit/resource state is being consumed. Re-check after those writes.
        # A stop here is terminal for the one-shot permit and must be receipted;
        # it never re-arms or retries the consequence.
        self._assert_runtime_open(
            action=action,
            execution_context=execution_context,
            execution_context_hash=execution_context_hash,
            decision=decision,
            effect=effect,
            journal_terminal=True,
        )

        self._execution_journal.mark_effect_invoking(permit_ref)
        try:
            result = effect._invoke_from_boundary(copy.deepcopy(action), _BOUNDARY_PROOF)
        except Exception as exc:
            self._record(
                status="INDETERMINATE",
                action=action,
                execution_context_hash=execution_context_hash,
                decision=decision,
                effect=effect,
                reason=f"EFFECT_EXCEPTION:{type(exc).__name__}:{exc}",
                journal_terminal=True,
            )
            raise

        postcondition: PostconditionResult | None = None
        valid_completion = True
        status = "COMMITTED"
        postconditions_verified: bool | None = None
        reason: str | None = None

        if action.get("postconditions_required"):
            if self._postcondition_checker is None:
                valid_completion = False
                status = "COMMITTED_UNVERIFIED"
                postconditions_verified = False
                reason = "POSTCONDITION_CHECKER_MISSING"
            else:
                try:
                    postcondition = self._postcondition_checker.check(
                        action, execution_context, result
                    )
                except Exception as exc:
                    postcondition = PostconditionResult(
                        verified=False,
                        reason=f"POSTCONDITION_CHECK_FAILURE:{type(exc).__name__}",
                    )
                postconditions_verified = postcondition.verified
                if not postcondition.verified:
                    valid_completion = False
                    status = "COMMITTED_WITH_DEVIATION"
                    reason = postcondition.reason or "POSTCONDITION_NOT_VERIFIED"

        receipt, closure = self._record(
            status=status,
            action=action,
            execution_context_hash=execution_context_hash,
            decision=decision,
            effect=effect,
            effect_result=result,
            reason=reason,
            postconditions_verified=postconditions_verified,
            journal_terminal=True,
        )
        return EffectCommitResult(
            decision=decision,
            effect_committed=True,
            effect_result=result,
            receipt=receipt,
            evidence_closure=closure,
            valid_completion=valid_completion,
            postcondition=postcondition,
        )


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "ContextFactory",
    "EffectBoundary",
    "EffectCommitResult",
    "EffectDenied",
    "InMemoryPermitStore",
    "PermitStore",
]
