from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..memory_provider import canonical_digest


class ProcurementGovernanceMode(str, Enum):
    UNRESTRICTED = "unrestricted"
    CLASSIC_CONTROLS = "classic_controls"
    EMOS_ACE = "emos_ace"


class ProcurementScenarioKind(str, Enum):
    PRICE_ONLY_AWARD = "price_only_award"
    LABOUR_INTENSIVE_WEIGHTING = "labour_intensive_weighting"
    AMBIGUOUS_CRITERIA = "ambiguous_criteria"
    ALGORITHMIC_SHORTLIST_BIAS = "algorithmic_shortlist_bias"
    STALE_ELIGIBILITY = "stale_eligibility"
    THIRD_COUNTRY_CONTROL = "third_country_control"
    SUPPLIER_BANK_CHANGE = "supplier_bank_change"
    MATERIAL_CONTRACT_MODIFICATION = "material_contract_modification"
    EMERGENCY_PROCUREMENT = "emergency_procurement"
    SUPPLIER_UNDERPERFORMANCE = "supplier_underperformance"
    INCOMPLETE_LIFECYCLE_PUBLICATION = "incomplete_lifecycle_publication"


class SimulationDecision(str, Enum):
    COMMIT = "commit"
    DEFER = "defer"
    STEP_UP = "step_up"
    DENY = "deny"


class ProcurementScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: str = Field(min_length=1)
    kind: ProcurementScenarioKind
    title: str = Field(min_length=1)
    proposed_action: str = Field(min_length=1)
    loss_exposure_nok: Decimal = Field(ge=0, max_digits=24, decimal_places=2)
    safe_to_commit_without_step_up: bool
    requires_human_step_up: bool
    classic_control_detects: bool
    governance_steps_classic: int = Field(ge=0)
    governance_steps_emos: int = Field(ge=0)
    classic_delay_hours: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    emos_delay_hours: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    ace_minutes: int = Field(ge=0)
    grants_authority: bool = False

    @model_validator(mode="after")
    def scenario_is_not_authority(self) -> "ProcurementScenario":
        if self.grants_authority:
            raise ValueError("simulation scenario cannot grant authority")
        return self


class ProcurementSimulationOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: str
    scenario_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mode: ProcurementGovernanceMode
    decision: SimulationDecision
    committed: bool
    safe_outcome: bool
    prevented_loss_nok: Decimal = Field(ge=0, max_digits=24, decimal_places=2)
    realized_loss_nok: Decimal = Field(ge=0, max_digits=24, decimal_places=2)
    delay_hours: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    ace_minutes: int = Field(ge=0)
    governance_steps: int = Field(ge=0)
    outcome_quality: Decimal = Field(ge=0, le=1, max_digits=4, decimal_places=3)
    grants_authority: bool = False

    @model_validator(mode="after")
    def outcome_is_not_clearance(self) -> "ProcurementSimulationOutcome":
        if self.grants_authority:
            raise ValueError("simulation outcome cannot grant authority")
        if self.committed != (self.decision is SimulationDecision.COMMIT):
            raise ValueError("committed must match simulation decision")
        return self


class ProcurementSimulationComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario: ProcurementScenario
    outcomes: tuple[ProcurementSimulationOutcome, ...]

    @model_validator(mode="after")
    def preserve_identical_inputs(self) -> "ProcurementSimulationComparison":
        expected_modes = set(ProcurementGovernanceMode)
        actual_modes = {outcome.mode for outcome in self.outcomes}
        if actual_modes != expected_modes or len(self.outcomes) != len(expected_modes):
            raise ValueError("comparison must contain exactly one outcome per governance mode")
        expected_digest = procurement_scenario_digest(self.scenario)
        if any(outcome.scenario_digest != expected_digest for outcome in self.outcomes):
            raise ValueError("all modes must use identical scenario inputs")
        return self


class ProcurementCatalogueMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: ProcurementGovernanceMode
    scenario_count: int = Field(ge=1)
    safe_outcomes: int = Field(ge=0)
    committed_actions: int = Field(ge=0)
    prevented_loss_nok: Decimal = Field(ge=0, max_digits=24, decimal_places=2)
    realized_loss_nok: Decimal = Field(ge=0, max_digits=24, decimal_places=2)
    total_delay_hours: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    total_ace_minutes: int = Field(ge=0)
    total_governance_steps: int = Field(ge=0)
    average_outcome_quality: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)


def procurement_scenario_digest(scenario: ProcurementScenario) -> str:
    return canonical_digest(scenario.model_dump(mode="json"))


def _scenario(
    scenario_id: str,
    kind: ProcurementScenarioKind,
    title: str,
    proposed_action: str,
    loss_exposure_nok: str,
    *,
    safe: bool = False,
    step_up: bool = True,
    classic_detects: bool = False,
    classic_steps: int = 2,
    emos_steps: int = 4,
    classic_delay: str = "2.00",
    emos_delay: str = "1.00",
    ace_minutes: int = 20,
) -> ProcurementScenario:
    return ProcurementScenario(
        scenario_id=scenario_id,
        kind=kind,
        title=title,
        proposed_action=proposed_action,
        loss_exposure_nok=Decimal(loss_exposure_nok),
        safe_to_commit_without_step_up=safe,
        requires_human_step_up=step_up,
        classic_control_detects=classic_detects,
        governance_steps_classic=classic_steps,
        governance_steps_emos=emos_steps,
        classic_delay_hours=Decimal(classic_delay),
        emos_delay_hours=Decimal(emos_delay),
        ace_minutes=ace_minutes,
    )


def default_procurement_scenarios() -> tuple[ProcurementScenario, ...]:
    return (
        _scenario(
            "proc-001",
            ProcurementScenarioKind.PRICE_ONLY_AWARD,
            "Price-only award hides quality failure",
            "Commit award based only on lowest price",
            "800000.00",
            classic_detects=False,
            ace_minutes=25,
        ),
        _scenario(
            "proc-002",
            ProcurementScenarioKind.LABOUR_INTENSIVE_WEIGHTING,
            "Labour-intensive contract uses insufficient quality weighting",
            "Publish criteria with inadequate quality weighting",
            "500000.00",
            classic_detects=True,
            classic_delay="4.00",
            ace_minutes=15,
        ),
        _scenario(
            "proc-003",
            ProcurementScenarioKind.AMBIGUOUS_CRITERIA,
            "Ambiguous quality criteria create evaluator disagreement",
            "Commit award despite unresolved evaluator disagreement",
            "650000.00",
            classic_detects=False,
            ace_minutes=45,
        ),
        _scenario(
            "proc-004",
            ProcurementScenarioKind.ALGORITHMIC_SHORTLIST_BIAS,
            "Algorithmic shortlist contains unexplained bias",
            "Accept algorithmic shortlist",
            "1200000.00",
            step_up=False,
            classic_detects=False,
            ace_minutes=0,
        ),
        _scenario(
            "proc-005",
            ProcurementScenarioKind.STALE_ELIGIBILITY,
            "Eligibility evidence expired before award",
            "Commit award using stale eligibility evidence",
            "900000.00",
            classic_detects=True,
            classic_delay="3.00",
            ace_minutes=10,
        ),
        _scenario(
            "proc-006",
            ProcurementScenarioKind.THIRD_COUNTRY_CONTROL,
            "Supplier control or data location conflicts with policy",
            "Sign contract with unresolved control and residency evidence",
            "1800000.00",
            classic_detects=True,
            classic_delay="8.00",
            ace_minutes=30,
        ),
        _scenario(
            "proc-007",
            ProcurementScenarioKind.SUPPLIER_BANK_CHANGE,
            "Supplier bank details change immediately before payment",
            "Execute supplier payment to changed bank account",
            "2500000.00",
            classic_detects=False,
            emos_delay="2.00",
            ace_minutes=20,
        ),
        _scenario(
            "proc-008",
            ProcurementScenarioKind.MATERIAL_CONTRACT_MODIFICATION,
            "Post-award modification changes value and scope materially",
            "Commit material contract modification",
            "1400000.00",
            classic_detects=True,
            classic_delay="12.00",
            ace_minutes=35,
        ),
        _scenario(
            "proc-009",
            ProcurementScenarioKind.EMERGENCY_PROCUREMENT,
            "Emergency procedure lacks proportionality evidence",
            "Invoke emergency procurement route",
            "1000000.00",
            classic_detects=False,
            emos_delay="0.50",
            ace_minutes=30,
        ),
        _scenario(
            "proc-010",
            ProcurementScenarioKind.SUPPLIER_UNDERPERFORMANCE,
            "Supplier underperformance is ignored before renewal",
            "Renew underperforming supplier contract",
            "1100000.00",
            classic_detects=False,
            ace_minutes=40,
        ),
        _scenario(
            "proc-011",
            ProcurementScenarioKind.INCOMPLETE_LIFECYCLE_PUBLICATION,
            "Lifecycle publication omits required source receipts",
            "Publish incomplete procurement lifecycle data",
            "150000.00",
            step_up=False,
            classic_detects=True,
            classic_delay="1.00",
            ace_minutes=0,
        ),
    )


def run_procurement_scenario(
    scenario: ProcurementScenario,
    mode: ProcurementGovernanceMode,
) -> ProcurementSimulationOutcome:
    digest = procurement_scenario_digest(scenario)

    if mode is ProcurementGovernanceMode.UNRESTRICTED:
        decision = SimulationDecision.COMMIT
        delay = Decimal("0")
        ace = 0
        steps = 0
    elif mode is ProcurementGovernanceMode.CLASSIC_CONTROLS:
        decision = (
            SimulationDecision.DEFER
            if scenario.classic_control_detects
            else SimulationDecision.COMMIT
        )
        delay = scenario.classic_delay_hours
        ace = 0
        steps = scenario.governance_steps_classic
    else:
        if scenario.safe_to_commit_without_step_up:
            decision = SimulationDecision.COMMIT
            ace = 0
        elif scenario.requires_human_step_up:
            decision = SimulationDecision.STEP_UP
            ace = scenario.ace_minutes
        else:
            decision = SimulationDecision.DENY
            ace = 0
        delay = scenario.emos_delay_hours
        steps = scenario.governance_steps_emos

    committed = decision is SimulationDecision.COMMIT
    unsafe_commit = committed and not scenario.safe_to_commit_without_step_up
    safe_outcome = not unsafe_commit
    realized_loss = scenario.loss_exposure_nok if unsafe_commit else Decimal("0")
    prevented_loss = (
        scenario.loss_exposure_nok
        if not committed and not scenario.safe_to_commit_without_step_up
        else Decimal("0")
    )

    if safe_outcome and committed:
        quality = Decimal("1.000")
    elif safe_outcome and decision is SimulationDecision.STEP_UP:
        quality = Decimal("0.950")
    elif safe_outcome:
        quality = Decimal("0.900")
    else:
        quality = Decimal("0.100")

    return ProcurementSimulationOutcome(
        scenario_id=scenario.scenario_id,
        scenario_digest=digest,
        mode=mode,
        decision=decision,
        committed=committed,
        safe_outcome=safe_outcome,
        prevented_loss_nok=prevented_loss,
        realized_loss_nok=realized_loss,
        delay_hours=delay,
        ace_minutes=ace,
        governance_steps=steps,
        outcome_quality=quality,
    )


def compare_governance_modes(scenario: ProcurementScenario) -> ProcurementSimulationComparison:
    return ProcurementSimulationComparison(
        scenario=scenario,
        outcomes=tuple(
            run_procurement_scenario(scenario, mode)
            for mode in ProcurementGovernanceMode
        ),
    )


def run_procurement_catalogue() -> tuple[ProcurementSimulationComparison, ...]:
    return tuple(compare_governance_modes(scenario) for scenario in default_procurement_scenarios())


def aggregate_catalogue_metrics(
    comparisons: tuple[ProcurementSimulationComparison, ...],
) -> tuple[ProcurementCatalogueMetrics, ...]:
    if not comparisons:
        raise ValueError("comparisons cannot be empty")

    results: list[ProcurementCatalogueMetrics] = []
    for mode in ProcurementGovernanceMode:
        outcomes = [
            outcome
            for comparison in comparisons
            for outcome in comparison.outcomes
            if outcome.mode is mode
        ]
        scenario_count = len(outcomes)
        quality_total = sum((outcome.outcome_quality for outcome in outcomes), Decimal("0"))
        results.append(
            ProcurementCatalogueMetrics(
                mode=mode,
                scenario_count=scenario_count,
                safe_outcomes=sum(outcome.safe_outcome for outcome in outcomes),
                committed_actions=sum(outcome.committed for outcome in outcomes),
                prevented_loss_nok=sum(
                    (outcome.prevented_loss_nok for outcome in outcomes), Decimal("0")
                ),
                realized_loss_nok=sum(
                    (outcome.realized_loss_nok for outcome in outcomes), Decimal("0")
                ),
                total_delay_hours=sum(
                    (outcome.delay_hours for outcome in outcomes), Decimal("0")
                ),
                total_ace_minutes=sum(outcome.ace_minutes for outcome in outcomes),
                total_governance_steps=sum(outcome.governance_steps for outcome in outcomes),
                average_outcome_quality=(quality_total / Decimal(scenario_count)).quantize(
                    Decimal("0.0001")
                ),
            )
        )
    return tuple(results)
