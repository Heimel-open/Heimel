"""Inspect registry for TOFOO relational rule-recovery evaluation."""

from .task import (
    central_iterative,
    central_iterative_solver,
    isolated,
    pooled_raw,
    relational_adaptive,
    relational_adaptive_solver,
    structured_raw,
    system_choice_scorer,
)

__all__ = [
    "central_iterative",
    "central_iterative_solver",
    "isolated",
    "pooled_raw",
    "relational_adaptive",
    "relational_adaptive_solver",
    "structured_raw",
    "system_choice_scorer",
]
