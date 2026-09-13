from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    HALT = "HALT"


@dataclass(frozen=True)
class State:
    semantic: float
    policy: float
    authority: float
    trust: float
    context: float
    tool: float
    provenance: float


@dataclass(frozen=True)
class Environment:
    trust_level: float
    authority_level: float
    isolation_level: float
    domain_multiplier: float
    criticality_penalty: float
    mode: str = "normal"


def squared_distance_to_admissible_region(x: State) -> float:
    """Toy admissible region centered at zero with independent dimensions."""
    return sum(value * value for value in x.__dict__.values())


def transition_energy(previous: State, candidate: State) -> float:
    return sum(
        (getattr(candidate, key) - getattr(previous, key)) ** 2
        for key in previous.__dict__.keys()
    )


def barrier(candidate: State) -> float:
    """Penalty for approaching a hard semantic or authority boundary."""
    hard_limit = 1.0
    margin = 0.15
    max_abs = max(abs(value) for value in candidate.__dict__.values())
    if max_abs >= hard_limit:
        return 10.0
    if max_abs >= hard_limit - margin:
        return 2.0
    return 0.0


def constraint_violation(candidate: State, env: Environment) -> float:
    """Deterministic hard constraint term."""
    if candidate.authority > env.authority_level:
        return 100.0
    if candidate.tool > env.authority_level:
        return 100.0
    return 0.0


def lambda_for(env: Environment) -> float:
    if env.mode == "halt":
        return -1.0
    if env.mode == "critical":
        return 0.05

    lambda_base = 1.0
    lam = (
        lambda_base
        * env.trust_level
        * env.authority_level
        * env.isolation_level
        * env.domain_multiplier
        - env.criticality_penalty
    )
    return max(lam, 0.0)


def free_energy(previous: State, candidate: State, env: Environment) -> float:
    w1 = 0.45
    w2 = 0.30
    w3 = 0.15
    w4 = 1.00
    return (
        w1 * squared_distance_to_admissible_region(candidate)
        + w2 * transition_energy(previous, candidate)
        + w3 * barrier(candidate)
        + w4 * constraint_violation(candidate, env)
    )


def phi(previous: State, candidate: State, env: Environment) -> Decision:
    lam = lambda_for(env)
    if lam < 0:
        return Decision.HALT
    return Decision.ALLOW if free_energy(previous, candidate, env) <= lam else Decision.BLOCK


def test_small_transition_under_normal_trust_is_allowed():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    candidate = State(0.1, 0.1, 0.1, 0.1, 0.1, 0.0, 0.1)
    env = Environment(
        trust_level=1.0,
        authority_level=1.0,
        isolation_level=1.0,
        domain_multiplier=1.0,
        criticality_penalty=0.0,
    )

    assert phi(previous, candidate, env) == Decision.ALLOW


def test_same_transition_under_low_trust_is_blocked():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    candidate = State(0.1, 0.1, 0.1, 0.1, 0.1, 0.0, 0.1)
    env = Environment(
        trust_level=0.2,
        authority_level=0.2,
        isolation_level=0.5,
        domain_multiplier=0.5,
        criticality_penalty=0.02,
    )

    assert lambda_for(env) >= 0.0
    assert phi(previous, candidate, env) == Decision.BLOCK


def test_boundary_crossing_is_blocked():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    candidate = State(1.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    env = Environment(
        trust_level=1.0,
        authority_level=1.0,
        isolation_level=1.0,
        domain_multiplier=1.0,
        criticality_penalty=0.0,
    )

    assert phi(previous, candidate, env) == Decision.BLOCK


def test_authority_violation_is_blocked_even_if_geometry_is_small():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    candidate = State(0.0, 0.0, 0.4, 0.0, 0.0, 0.4, 0.0)
    env = Environment(
        trust_level=1.0,
        authority_level=0.2,
        isolation_level=1.0,
        domain_multiplier=1.0,
        criticality_penalty=0.0,
    )

    assert phi(previous, candidate, env) == Decision.BLOCK


def test_critical_mode_has_near_zero_permeability():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    small_candidate = State(0.01, 0.01, 0.01, 0.01, 0.01, 0.0, 0.01)
    larger_candidate = State(0.2, 0.2, 0.2, 0.2, 0.2, 0.0, 0.2)
    env = Environment(
        trust_level=1.0,
        authority_level=1.0,
        isolation_level=1.0,
        domain_multiplier=1.0,
        criticality_penalty=0.0,
        mode="critical",
    )

    assert phi(previous, small_candidate, env) == Decision.ALLOW
    assert phi(previous, larger_candidate, env) == Decision.BLOCK


def test_halt_mode_allows_no_transition():
    previous = State(0, 0, 0, 0, 0, 0, 0)
    candidate = State(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    env = Environment(
        trust_level=1.0,
        authority_level=1.0,
        isolation_level=1.0,
        domain_multiplier=1.0,
        criticality_penalty=0.0,
        mode="halt",
    )

    assert phi(previous, candidate, env) == Decision.HALT
