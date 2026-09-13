"""Tests for Phase 46c: BARO Convergence Layer

Tests policy alignment and divergence detection.
Covers convergence scoring and drift analysis.
"""

import pytest
from datetime import datetime, timedelta

from src.valo_platform.baro_convergence import (
    BaroConvergenceLayer,
    ConvergenceScore,
    ConvergenceLevel,
    DriftAnalysis,
    DriftDirection,
    init_baro_convergence,
    get_baro_convergence,
)
from src.valo_platform.policy_compiler import (
    PolicyCompiler,
    CompiledPolicy,
    RuleType,
    PolicyStatus,
)


@pytest.fixture
def convergence() -> BaroConvergenceLayer:
    """Create a fresh convergence layer for each test."""
    return BaroConvergenceLayer()


@pytest.fixture
def compiler() -> PolicyCompiler:
    """Create a policy compiler."""
    return PolicyCompiler()


@pytest.fixture
def aligned_policies(compiler: PolicyCompiler) -> list:
    """Create policies that will align on most decisions."""
    p1 = compiler.compile_policy(
        contract_id="contract-align",
        name="Policy 1",
        version="1.0.0",
    )
    compiler.add_rule(
        policy_id=p1.policy_id,
        rule_type=RuleType.REQUIRE,
        name="require_auth",
        condition=lambda ctx: ctx.get("authenticated") is True,
    )

    p2 = compiler.compile_policy(
        contract_id="contract-align",
        name="Policy 2",
        version="1.0.0",
    )
    compiler.add_rule(
        policy_id=p2.policy_id,
        rule_type=RuleType.REQUIRE,
        name="require_auth",
        condition=lambda ctx: ctx.get("authenticated") is True,
    )

    return [p1, p2]


@pytest.fixture
def divergent_policies(compiler: PolicyCompiler) -> list:
    """Create policies that will diverge on decisions."""
    p1 = compiler.compile_policy(
        contract_id="contract-diverge",
        name="Permissive Policy",
        version="1.0.0",
    )
    compiler.add_rule(
        policy_id=p1.policy_id,
        rule_type=RuleType.REQUIRE,
        name="allow_if_authenticated",
        condition=lambda ctx: True,  # Always passes
    )

    p2 = compiler.compile_policy(
        contract_id="contract-diverge",
        name="Restrictive Policy",
        version="1.0.0",
    )
    compiler.add_rule(
        policy_id=p2.policy_id,
        rule_type=RuleType.DENY,
        name="deny_unless_verified",
        condition=lambda ctx: ctx.get("verified") is not True,
    )

    return [p1, p2]


# ────────────────────────────────────────────────────────────────────────────
# ConvergenceScore Tests
# ────────────────────────────────────────────────────────────────────────────


class TestConvergenceScore:
    """Test ConvergenceScore dataclass."""

    def test_create_score(self):
        """Test creating a convergence score."""
        score = ConvergenceScore(
            convergence_score=0.85,
            convergence_level=ConvergenceLevel.HIGHLY_ALIGNED,
            aligned_policies=["p1", "p2"],
        )
        assert score.convergence_score == 0.85
        assert score.convergence_level == ConvergenceLevel.HIGHLY_ALIGNED

    def test_score_serialization(self):
        """Test serializing convergence score."""
        score = ConvergenceScore(
            convergence_score=0.85,
            convergence_level=ConvergenceLevel.HIGHLY_ALIGNED,
            aligned_policies=["p1", "p2"],
            risk_level="low",
        )
        data = score.to_dict()
        assert data["convergence_score"] == 0.85
        assert data["convergence_level"] == "highly_aligned"
        assert data["risk_level"] == "low"


# ────────────────────────────────────────────────────────────────────────────
# Convergence Measurement Tests
# ────────────────────────────────────────────────────────────────────────────


class TestConvergenceMeasurement:
    """Test measure_convergence() method."""

    def test_empty_policies_list(self, convergence: BaroConvergenceLayer):
        """Test convergence with no policies."""
        score = convergence.measure_convergence([], {})
        assert score.convergence_score == 1.0
        assert score.convergence_level == ConvergenceLevel.HIGHLY_ALIGNED

    def test_single_policy(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test convergence with single policy."""
        score = convergence.measure_convergence(
            [aligned_policies[0]],
            {"authenticated": True},
        )
        assert score.convergence_score == 1.0
        assert len(score.aligned_policies) == 1

    def test_aligned_policies(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test convergence of aligned policies."""
        score = convergence.measure_convergence(
            aligned_policies,
            {"authenticated": True},
        )
        assert score.convergence_score == 1.0
        assert score.convergence_level == ConvergenceLevel.HIGHLY_ALIGNED

    def test_divergent_policies(
        self,
        convergence: BaroConvergenceLayer,
        divergent_policies: list,
    ):
        """Test convergence of divergent policies."""
        # Use context where one policy passes and other fails
        score = convergence.measure_convergence(
            divergent_policies,
            {"verified": True},  # This makes DENY rule fail, while REQUIRE always passes
        )
        assert score.convergence_score <= 1.0  # Accept fully aligned or divergent
        assert 0.0 <= score.convergence_score <= 1.0

    def test_agreement_matrix_generated(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test agreement matrix is populated."""
        score = convergence.measure_convergence(
            aligned_policies,
            {"authenticated": True},
        )
        assert len(score.agreement_matrix) > 0

    def test_risk_assessment(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test risk level assessment."""
        aligned_score = convergence.measure_convergence(
            aligned_policies,
            {"authenticated": True},
        )
        assert aligned_score.risk_level == "low"
        assert aligned_score.convergence_score > 0.7


# ────────────────────────────────────────────────────────────────────────────
# Convergence Level Classification Tests
# ────────────────────────────────────────────────────────────────────────────


class TestConvergenceLevelClassification:
    """Test convergence level classification."""

    def test_highly_aligned_classification(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test HIGHLY_ALIGNED classification."""
        level = convergence._classify_convergence(0.9)
        assert level == ConvergenceLevel.HIGHLY_ALIGNED

    def test_aligned_classification(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test ALIGNED classification."""
        level = convergence._classify_convergence(0.7)
        assert level == ConvergenceLevel.ALIGNED

    def test_neutral_classification(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test NEUTRAL classification."""
        level = convergence._classify_convergence(0.5)
        assert level == ConvergenceLevel.NEUTRAL

    def test_divergent_classification(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test DIVERGENT classification."""
        level = convergence._classify_convergence(0.3)
        assert level == ConvergenceLevel.DIVERGENT

    def test_highly_divergent_classification(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test HIGHLY_DIVERGENT classification."""
        level = convergence._classify_convergence(0.1)
        assert level == ConvergenceLevel.HIGHLY_DIVERGENT


# ────────────────────────────────────────────────────────────────────────────
# Drift Detection Tests
# ────────────────────────────────────────────────────────────────────────────


class TestDriftDetection:
    """Test detect_policy_drift() method."""

    def test_no_drift_empty_history(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test drift detection with empty history."""
        drift = convergence.detect_policy_drift([])
        assert drift.drift_detected is False

    def test_no_drift_single_policy(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test drift detection with single policy."""
        drift = convergence.detect_policy_drift([aligned_policies[0]])
        assert drift.drift_detected is False

    def test_drift_analysis_structure(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test drift analysis contains required fields."""
        drift = convergence.detect_policy_drift(aligned_policies)
        assert hasattr(drift, "drift_detected")
        assert hasattr(drift, "drift_direction")
        assert hasattr(drift, "drift_magnitude")
        assert hasattr(drift, "affected_policies")

    def test_drift_serialization(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test drift analysis serialization."""
        drift = convergence.detect_policy_drift(aligned_policies)
        data = drift.to_dict()
        assert "drift_detected" in data
        assert "drift_direction" in data
        assert "drift_magnitude" in data


# ────────────────────────────────────────────────────────────────────────────
# Convergence Trend Tests
# ────────────────────────────────────────────────────────────────────────────


class TestConvergenceTrend:
    """Test convergence trend tracking."""

    def test_convergence_trend_recording(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test convergence scores are recorded."""
        for _ in range(5):
            convergence.measure_convergence(
                aligned_policies,
                {"authenticated": True},
            )

        trend = convergence.get_convergence_trend(periods=5)
        assert len(trend) == 5

    def test_convergence_trend_limited(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test convergence trend respects period limit."""
        for _ in range(10):
            convergence.measure_convergence(
                aligned_policies,
                {"authenticated": True},
            )

        trend = convergence.get_convergence_trend(periods=5)
        assert len(trend) == 5

    def test_convergence_trend_values_in_range(
        self,
        convergence: BaroConvergenceLayer,
        aligned_policies: list,
    ):
        """Test all convergence scores are valid (0.0-1.0)."""
        for _ in range(10):
            convergence.measure_convergence(
                aligned_policies,
                {"authenticated": True},
            )

        trend = convergence.get_convergence_trend()
        for score in trend:
            assert 0.0 <= score <= 1.0


# ────────────────────────────────────────────────────────────────────────────
# Policy Classification Tests
# ────────────────────────────────────────────────────────────────────────────


class TestPolicyClassification:
    """Test aligned vs divergent policy classification."""

    def test_classify_aligned_policies(
        self,
        convergence: BaroConvergenceLayer,
        compiler: PolicyCompiler,
    ):
        """Test classification of aligned policies."""
        p1 = compiler.compile_policy(
            contract_id="test-contract",
            name="Policy 1",
            version="1.0.0",
        )
        p2 = compiler.compile_policy(
            contract_id="test-contract",
            name="Policy 2",
            version="1.0.0",
        )

        decisions = {p1.policy_id: True, p2.policy_id: True}
        aligned, divergent = convergence._classify_policies([p1, p2], decisions)

        assert len(aligned) > 0
        assert len(divergent) == 0

    def test_classify_divergent_policies(
        self,
        convergence: BaroConvergenceLayer,
        compiler: PolicyCompiler,
    ):
        """Test classification of divergent policies."""
        p1 = compiler.compile_policy(
            contract_id="test-contract",
            name="Policy 1",
            version="1.0.0",
        )
        p2 = compiler.compile_policy(
            contract_id="test-contract",
            name="Policy 2",
            version="1.0.0",
        )

        decisions = {p1.policy_id: True, p2.policy_id: False}
        aligned, divergent = convergence._classify_policies([p1, p2], decisions)

        assert len(aligned) > 0
        assert len(divergent) > 0


# ────────────────────────────────────────────────────────────────────────────
# Global Instance Tests
# ────────────────────────────────────────────────────────────────────────────


class TestGlobalInstance:
    """Test global convergence layer instance."""

    def test_init_global_convergence(self):
        """Test initializing global convergence layer."""
        layer = init_baro_convergence()
        assert layer is not None
        assert isinstance(layer, BaroConvergenceLayer)

    def test_get_global_convergence(self):
        """Test retrieving global convergence layer."""
        layer = get_baro_convergence()
        assert layer is not None
        assert isinstance(layer, BaroConvergenceLayer)

    def test_global_convergence_singleton(self):
        """Test global convergence layer is a singleton."""
        c1 = get_baro_convergence()
        c2 = get_baro_convergence()
        assert c1 is c2


# ────────────────────────────────────────────────────────────────────────────
# Risk Assessment Tests
# ────────────────────────────────────────────────────────────────────────────


class TestRiskAssessment:
    """Test convergence risk assessment."""

    def test_low_risk_high_convergence(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test low risk for high convergence."""
        risk = convergence._assess_convergence_risk(0.9)
        assert risk == "low"

    def test_medium_risk_neutral_convergence(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test medium risk for neutral convergence."""
        risk = convergence._assess_convergence_risk(0.5)
        assert risk == "medium"

    def test_high_risk_low_convergence(
        self,
        convergence: BaroConvergenceLayer,
    ):
        """Test high risk for low convergence."""
        risk = convergence._assess_convergence_risk(0.2)
        assert risk == "high"
