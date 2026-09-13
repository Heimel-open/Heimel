from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from valo_kernel import KernelEngine
from valo_kernel.kernel.execution_outcome import KernelExecutionOutcomeConsumer
from valo_reht import (
    BoundaryEffect,
    EffectBoundary,
    RealReht,
    SQLiteExecutionJournal,
    SQLitePermitStore,
    VeritasKernelExecutionEvidenceSink,
)
from veritas import VeritasChainService, WORMLog


@dataclass(frozen=True)
class RuntimeExecution:
    """The complete result of one governed attempt."""

    result: Any
    ledger: VeritasChainService

    @property
    def committed(self) -> bool:
        return bool(self.result.effect_committed)

    @property
    def evidence_closed(self) -> bool:
        closure = self.result.evidence_closure
        return bool(closure and closure.closed)


class HeimelRuntime:
    """Runnable Kernel -> REHT -> EffectBoundary -> Veritas -> Kernel runtime.

    The caller supplies a Kernel context factory because only Kernel can build
    a fresh context from the application's authoritative state. This class
    owns the consequence boundary and makes bypassing it structurally harder.
    """

    def __init__(self, *, engine: KernelEngine, boundary: EffectBoundary, ledger: VeritasChainService) -> None:
        self.engine = engine
        self.boundary = boundary
        self.ledger = ledger
        self.reht = RealReht()

    @classmethod
    def production(cls, engine: KernelEngine, data_dir: str | Path) -> "HeimelRuntime":
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        permit_store = SQLitePermitStore(root / "permits.sqlite3")
        journal = SQLiteExecutionJournal(root / "execution-journal.sqlite3")
        ledger = VeritasChainService(WORMLog(root / "veritas-worm.jsonl"))
        consumer = KernelExecutionOutcomeConsumer(engine)
        sink = VeritasKernelExecutionEvidenceSink(veritas=ledger, kernel=consumer)
        boundary = EffectBoundary(
            permit_store,
            evidence_sink=sink,
            execution_journal=journal,
        )
        return cls(engine=engine, boundary=boundary, ledger=ledger)

    def execute(
        self,
        *,
        context_factory: Callable[[dict[str, Any]], dict[str, Any]],
        action_contract: dict[str, Any],
        effect_name: str,
        effect: Callable[[dict[str, Any]], Any],
    ) -> RuntimeExecution:
        result = self.boundary.commit(
            reht=self.reht,
            context_factory=context_factory,
            action_contract=action_contract,
            effect=BoundaryEffect.seal(effect_name, effect),
        )
        return RuntimeExecution(result=result, ledger=self.ledger)
