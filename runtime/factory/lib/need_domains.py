from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NeedDomain:
    domain_id: str
    name: str
    definition: str
    examples: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.domain_id or not self.name or not self.definition:
            raise ValueError("need domain requires id, name and definition")
        if not self.examples:
            raise ValueError("need domain requires examples")


WELLBEING = NeedDomain(
    domain_id="wellbeing",
    name="Velvære",
    definition=(
        "Enhver ønsket personlig livsendring som øker opplevd eller faktisk livsverdi, "
        "inkludert endringer i trivsel, muligheter, tilgang, relasjoner, status, kapasitet, "
        "økonomi, omgivelser eller fremtidig livsbane. Velvære er derfor bredere enn wellness."
    ),
    examples=(
        "ferie og reise",
        "fritid, rekreasjon og opplevelser",
        "hvile og restitusjon",
        "helse og fysisk form",
        "mental trivsel",
        "dating, partner og relasjoner",
        "utdanning, læring og ferdigheter",
        "bedre jobb, karriere og inntekt",
        "nettverk og sosial tilhørighet",
        "bolig, nærmiljø og flytting",
        "bil, mobilitet og andre ønskede eiendeler",
        "hobbyer, sport og underholdning",
        "identitet, stil, status og personlig uttrykk",
        "nye muligheter og tilgang til miljøer eller erfaringer",
    ),
)


NEED_DOMAINS = {WELLBEING.domain_id: WELLBEING}


def get_need_domain(domain_id: str) -> NeedDomain:
    try:
        return NEED_DOMAINS[domain_id]
    except KeyError as exc:
        raise ValueError(f"unknown need domain: {domain_id}") from exc


@dataclass(frozen=True)
class NeedHypothesis:
    """A possible need inferred by relAIon. It is not authority to act."""

    need_id: str
    domain_id: str
    current_state: str
    proposed_change: str
    rationale: str
    evidence_refs: tuple[str, ...] = ()
    direct_effect_path: bool = False

    def __post_init__(self) -> None:
        if not self.need_id or not self.current_state or not self.proposed_change:
            raise ValueError("need hypothesis requires identity, current state and proposed change")
        get_need_domain(self.domain_id)
        if self.direct_effect_path:
            raise ValueError("need discovery must not create a direct effect path")


@dataclass(frozen=True)
class ConfirmedNeed:
    """Human-confirmed need that may become the mandate for work toward done."""

    need_id: str
    domain_id: str
    desired_outcome: str
    confirmed_by_human: bool
    confirmation_ref: str
    constraints: tuple[str, ...] = ()
    direct_effect_path: bool = False

    def __post_init__(self) -> None:
        if not self.need_id or not self.desired_outcome:
            raise ValueError("confirmed need requires identity and desired outcome")
        get_need_domain(self.domain_id)
        if not self.confirmed_by_human or not self.confirmation_ref:
            raise ValueError("a need must be explicitly confirmed by the human before it becomes a mandate")
        if self.direct_effect_path:
            raise ValueError("confirmation creates a mandate, not a direct effect path")


@dataclass(frozen=True)
class NeedToDoneContract:
    """Boundary between relAIon need discovery and the governed path toward done."""

    need: ConfirmedNeed
    done_definition: str
    outcome_evidence_required: bool = True
    direct_effect_path: bool = False

    def __post_init__(self) -> None:
        if not self.done_definition:
            raise ValueError("done_definition is required")
        if not self.outcome_evidence_required:
            raise ValueError("done must require outcome evidence")
        if self.direct_effect_path:
            raise ValueError("need-to-done planning must remain behind governed execution")


def confirm_need(
    hypothesis: NeedHypothesis,
    *,
    desired_outcome: str,
    confirmation_ref: str,
    constraints: tuple[str, ...] = (),
) -> ConfirmedNeed:
    """Convert a relAIon hypothesis into a mandate only after explicit human confirmation."""
    return ConfirmedNeed(
        need_id=hypothesis.need_id,
        domain_id=hypothesis.domain_id,
        desired_outcome=desired_outcome,
        confirmed_by_human=True,
        confirmation_ref=confirmation_ref,
        constraints=constraints,
        direct_effect_path=False,
    )
