"""
Tests — BARO Motivational Drift Observer (#448, experimental/shadow).

Covers: empty input, single tension dominance, mixed tensions,
value asymmetry, collapse pattern mapping, experimental mode marking,
RealityPackage output shape (no decision fields), and confidence model.
"""

from src.valo_platform.baro_motivational_drift import (
    MotivationalDriftObserver,
    ValuePair,
    CollapsePattern,
)


# --- experimental / shadow mode --------------------------------------------

def test_mode_is_experimental_shadow():
    """Observer marks itself as experimental/shadow per #448 research constraints."""
    obs = MotivationalDriftObserver()
    result = obs.observe(
        subject_id="test-agent",
        behaviour_pairs=[
            ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5),
        ],
    )
    assert result.mode == "experimental_shadow"
    assert "experimental" in result.estimator_version
    assert result.model == "desire_signature_v0"


# --- no decision fields ----------------------------------------------------

def test_no_decision_fields_in_reality_package():
    """BARO observes only — RealityPackage MUST NOT carry allow/deny."""
    obs = MotivationalDriftObserver()
    result = obs.observe(
        subject_id="test-agent",
        behaviour_pairs=[
            ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=3),
        ],
    )
    rp = result.as_reality_package()
    assert "allow" not in rp
    assert "deny" not in rp
    assert "admissible" not in rp
    assert "decision" not in rp
    assert rp["observer"] == "baro_motivational_drift"


# --- empty input -----------------------------------------------------------

def test_empty_behaviour_pairs_rejected():
    """Empty input should produce a rejected observation."""
    obs = MotivationalDriftObserver()
    result = obs.observe(subject_id="test-agent", behaviour_pairs=[])
    assert result.rejected is True
    assert result.rejection_reason == "no_behaviour_pairs"


# --- single tension dominance ----------------------------------------------

def test_single_tension_dominance():
    """When all behaviour is one tension, drift_score should be 1.0."""
    obs = MotivationalDriftObserver()
    pairs = [
        ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=10),
    ]
    result = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    assert result.drift_score == 1.0
    assert result.dominant_value == "efficiency"
    assert result.subordinated_value == "human_control"
    assert result.tension == "efficiency_vs_human_control"


# --- mixed tensions --------------------------------------------------------

def test_mixed_tensions_picks_dominant():
    """With mixed tensions, the most frequent one should be selected."""
    obs = MotivationalDriftObserver()
    pairs = [
        ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=8),
        ValuePair("safety", "freedom", "safety_vs_freedom", count=2),
    ]
    result = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    assert result.drift_score == 0.8  # 8/10
    assert result.dominant_value == "efficiency"
    assert result.tension == "efficiency_vs_human_control"


# --- collapse pattern mapping ----------------------------------------------

def test_collapse_pattern_is_mapped():
    """Each durable tension maps to an expected collapse pattern."""
    obs = MotivationalDriftObserver()
    pairs = [
        ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5),
    ]
    result = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    assert result.collapse_pattern == CollapsePattern.CONTROL_DISPLACEMENT.value


def test_multiple_tensions_have_collapse_patterns():
    """Multiple durable tensions should all map to known patterns."""
    mapping = {
        "efficiency_vs_human_control": CollapsePattern.CONTROL_DISPLACEMENT.value,
        "safety_vs_freedom": CollapsePattern.RECKLESS_SAFETY.value,
        "consensus_vs_truth": CollapsePattern.ECHO_CHAMBER.value,
        "stability_vs_adaptation": CollapsePattern.RIGIDITY_SPIRAL.value,
        "autonomy_vs_accountability": CollapsePattern.ACCOUNTABILITY_VOID.value,
        "growth_vs_integrity": CollapsePattern.EROSION.value,
        "memory_vs_forgetting": CollapsePattern.AMNESIA.value,
        "rule_compliance_vs_judgment": CollapsePattern.LEGALISM.value,
    }
    for tension, expected_pattern in mapping.items():
        dominant, subordinated = tension.split("_vs_")
        obs = MotivationalDriftObserver()
        result = obs.observe(
            subject_id="test-agent",
            behaviour_pairs=[ValuePair(dominant, subordinated, tension, count=3)],
        )
        assert result.collapse_pattern == expected_pattern, (
            f"{tension} should map to {expected_pattern}, got {result.collapse_pattern}"
        )


# --- value asymmetry -------------------------------------------------------

def test_value_asymmetry_zero_when_balanced():
    """Perfectly balanced value trade-offs produce asymmetry ~0."""
    obs = MotivationalDriftObserver()
    pairs = [
        ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5),
        ValuePair("human_control", "efficiency", "efficiency_vs_human_control", count=5),
    ]
    result = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    assert result.value_asymmetry_score is not None
    assert result.value_asymmetry_score <= 0.01  # effectively balanced
    assert result.collapse_pattern is None
    assert result.collapse_proximity == 0.0


def test_value_asymmetry_high_when_lopsided():
    """Highly lopsided value subordination produces high asymmetry."""
    obs = MotivationalDriftObserver()
    pairs = [
        ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=10),
        ValuePair("human_control", "efficiency", "efficiency_vs_human_control", count=1),
    ]
    result = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    assert result.value_asymmetry_score is not None
    assert result.value_asymmetry_score > 0.5


# --- confidence / uncertainty ----------------------------------------------

def test_confidence_increases_with_more_evidence():
    """More observations should increase evidence confidence."""
    obs = MotivationalDriftObserver()
    low_result = obs.observe(
        subject_id="test-agent",
        behaviour_pairs=[ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=1)],
    )
    high_result = obs.observe(
        subject_id="test-agent",
        behaviour_pairs=[ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=20)],
    )
    assert high_result.evidence_confidence is not None
    assert low_result.evidence_confidence is not None
    assert high_result.evidence_confidence > low_result.evidence_confidence


def test_uncertainty_field_present():
    """Observation should carry uncertainty for key metrics."""
    obs = MotivationalDriftObserver()
    result = obs.observe(
        subject_id="test-agent",
        behaviour_pairs=[ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5)],
    )
    assert "drift_score_std" in result.uncertainty
    assert "persistence_std" in result.uncertainty
    assert "asymmetry_std" in result.uncertainty


# --- signature / determinism -----------------------------------------------

def test_signature_is_deterministic():
    """Same inputs at the same time should produce the same signature."""
    obs = MotivationalDriftObserver()
    pairs = [ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5)]
    r1 = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    # Second call on the same observer instance in the same millisecond
    r2 = obs.observe(subject_id="test-agent", behaviour_pairs=pairs)
    # Timestamps may differ by microseconds; compare core metrics instead
    assert r1.drift_score == r2.drift_score
    assert r1.confidence == r2.confidence
    assert r1.value_asymmetry_score == r2.value_asymmetry_score
    assert r1.tension == r2.tension


def test_reverse_observed_direction_is_preserved():
    """The reported direction comes from observations, not tension-name order."""
    result = MotivationalDriftObserver().observe(
        subject_id="test-agent",
        behaviour_pairs=[
            ValuePair("human_control", "efficiency", "efficiency_vs_human_control", count=10),
        ],
    )
    assert result.dominant_value == "human_control"
    assert result.subordinated_value == "efficiency"
    assert result.collapse_pattern is None
    assert result.collapse_proximity == 0.0


def test_unknown_tensions_never_emit_negative_normalized_scores():
    """Non-canonical observations remain bounded if supplied by an upstream adapter."""
    pairs = [
        ValuePair(f"dominant-{index}", f"subordinated-{index}", f"custom-{index}", count=1)
        for index in range(12)
    ]
    result = MotivationalDriftObserver().observe("test-agent", pairs)
    assert result.compensation_pattern_score is not None
    assert result.compensation_pattern_score >= 0.0


def test_signature_ignores_observation_timestamp():
    """Identical evidence has one replay signature even when observed later."""
    observer = MotivationalDriftObserver()
    pairs = [ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=5)]
    first = observer.observe(subject_id="test-agent", behaviour_pairs=pairs)
    second = observer.observe(subject_id="test-agent", behaviour_pairs=pairs)
    second.timestamp = second.timestamp.replace(microsecond=(second.timestamp.microsecond + 1) % 1_000_000)
    assert first.signature() == second.signature()


def test_experimental_confidence_never_reaches_certainty():
    """Shadow-mode evidence remains explicitly falsifiable."""
    result = MotivationalDriftObserver().observe(
        subject_id="test-agent",
        behaviour_pairs=[
            ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=10_000),
        ],
    )
    assert result.confidence < 1.0


# --- subject_id propagation ------------------------------------------------

def test_subject_id_present():
    """Subject ID should propagate through to the observation."""
    obs = MotivationalDriftObserver()
    result = obs.observe(
        subject_id="agent-alpha-42",
        behaviour_pairs=[ValuePair("efficiency", "human_control", "efficiency_vs_human_control", count=3)],
    )
    assert result.subject_id == "agent-alpha-42"
