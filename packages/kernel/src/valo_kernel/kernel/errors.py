from __future__ import annotations


class KernelError(RuntimeError):
    """Base class for all kernel failures."""


class FailClosedError(KernelError):
    """The kernel refuses to proceed: unknown schema, missing tenant/identity,
    broken hash, or any other unverifiable precondition."""


class KernelInvariantViolation(FailClosedError):
    """A world invariant would be broken by this event. Fail closed."""


class IntegrityError(FailClosedError):
    """Raised when any hash chain or state root is inconsistent (tamper)."""


class ConcurrencyError(KernelError):
    """Optimistic concurrency conflict: expected_version did not match."""


class IdempotentReplay(KernelError):
    """The event was already applied (idempotency_key matched)."""


class TransitionError(KernelError):
    """A transition contract precondition did not hold."""


class DivergenceError(KernelError):
    """Expected postcondition was not produced by observed reality."""


class ExecutionContextError(KernelError):
    """The kernel cannot produce a safe execution context. Fail closed."""

