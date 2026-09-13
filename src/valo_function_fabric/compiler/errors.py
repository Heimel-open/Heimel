from __future__ import annotations


class CompileError(ValueError):
    """Function Fabric static compilation failed. Fail closed: nothing is
    compiled or executed."""


class ResolverError(CompileError):
    """Unknown function/version or a reference to an unregistered function."""


class TypecheckError(CompileError):
    """Typed composition is invalid."""


class EffectsError(CompileError):
    """Golden invariant violated: an effect not declared by the Function."""


class GovernanceError(CompileError):
    """Governance monotonicity violated: risk/effects/authority/evidence/
    autonomy weakened through composition."""
