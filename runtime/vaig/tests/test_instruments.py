"""Comprehensive instrument tests for VAIG.

Tests all 8 instruments with realistic inputs:
  1. length_anomaly     — output length detection
  2. format_check       — truncation/structure validation
  3. hedge_detector     — uncertainty language detection
  4. logprob_scorer     — native token surprisal
  5. activation_probe   — calibrated hidden-state geometric drift
  6. text_similarity    — semantic similarity via sampling/Jaccard
  7. semantic_entropy   — consistency via resampling
  8. cot_auditor        — chain-of-thought audit
"""

import pytest

from vaig.instruments import (
    length_anomaly,
    format_check,
    hedge_detector,
    logprob_scorer,
    activation_probe,
    text_similarity,
    semantic_entropy,
    cot_auditor,
)


class TestLengthAnomaly:
    def test_normal_length(self):
        inst = length_anomaly.ZScoreLengthAnomalyDetector(mean=6, std=20)
        score = inst.score("Hva er hovedstaden i Frankrike?", "Hovedstaden i Frankrike er Paris.")
        assert 0.0 <= score <= 0.3

    def test_truncated_short(self):
        inst = length_anomaly.ZScoreLengthAnomalyDetector(mean=180, std=80)
        score = inst.score("Forklar kvantemekanikk", "Kvante")
        assert score >= 0.5

    def test_very_long(self):
        inst = length_anomaly.ZScoreLengthAnomalyDetector(mean=6, std=20)
        long_response = "Paris. " * 100
        score = inst.score("Hva er hovedstaden i Frankrike?", long_response)
        assert score >= 0.5

    def test_sigmoid_normalization(self):
        inst = length_anomaly.ZScoreLengthAnomalyDetector()
        for length in [0, 10, 50, 100, 200, 500, 1000]:
            response = "A" * length
            score = inst.score("test", response)
            assert 0.0 <= score <= 1.0


class TestFormatCheck:
    def test_clean_json(self):
        inst = format_check.StructuralFormatChecker()
        score = inst.score("test", '{"key": "value", "number": 42}')
        assert score <= 0.7

    def test_truncated_json(self):
        inst = format_check.StructuralFormatChecker()
        score = inst.score("test", '{"key": "val')
        assert score >= 0.5

    def test_missing_sections(self):
        inst = format_check.StructuralFormatChecker()
        score = inst.score("test", "Seksjon 1\nInnhold\nSeksjon 3\nInnhold")
        assert score >= 0.5

    def test_empty_response(self):
        inst = format_check.StructuralFormatChecker()
        score = inst.score("test", "")
        assert score == 1.0


class TestHedgeDetector:
    def test_no_hedge(self):
        inst = hedge_detector.RegexHedgeDetector()
        score = inst.score("test", "Hovedstaden i Frankrike er Paris. Det er et faktum.")
        assert score <= 0.15

    def test_moderate_hedge(self):
        inst = hedge_detector.RegexHedgeDetector()
        score = inst.score("test", "Kanskje det er slik. Muligens er Paris hovedstaden.")
        assert score >= 0.3

    def test_high_hedge_density(self):
        inst = hedge_detector.RegexHedgeDetector()
        score = inst.score(
            "test",
            "Jeg tror kanskje at Paris muligens er hovedstaden. "
            "Det kan være sant. Jeg er ikke sikker. Det virker sannsynlig.",
        )
        assert score >= 0.5

    def test_danish_hedge(self):
        inst = hedge_detector.RegexHedgeDetector()
        score = inst.score("test", "Måske er dette korrekt. Det ser muligvis ud til at være rigtigt.")
        assert score == 0.0


class TestLogprobScorer:
    def test_with_native_logprobs(self):
        inst = logprob_scorer.TokenEntropyLogprobScorer()
        score = inst.score("test", "hello", logprobs=[-0.5, -1.2, -0.8, -2.1])
        assert 0.0 <= score <= 1.0

    def test_missing_logprobs_is_not_text_proxy(self):
        inst = logprob_scorer.TokenEntropyLogprobScorer()
        with pytest.raises(ValueError, match="native logprobs"):
            inst.score("test", "Confident-looking prose is not confidence evidence.")

    def test_empty_logprobs_rejected(self):
        inst = logprob_scorer.TokenEntropyLogprobScorer()
        with pytest.raises(ValueError, match="native logprobs"):
            inst.score("test", "response", logprobs=[])

    def test_invalid_positive_logprob_rejected(self):
        inst = logprob_scorer.TokenEntropyLogprobScorer()
        with pytest.raises(ValueError, match="<= 0"):
            inst.score("test", "response", logprobs=[-0.2, 0.1])


class TestActivationProbe:
    def test_null_probe_is_unavailable(self):
        inst = activation_probe.NullActivationProbe()
        with pytest.raises(ValueError, match="unavailable"):
            inst.score("test", "response")

    def test_geometric_drift_requires_calibration(self):
        inst = activation_probe.GeometricDriftProbe()
        assert inst.is_calibrated() is False
        with pytest.raises(ValueError, match="calibration"):
            inst.score("test", "response", hidden_states=[[0.2, 0.3, 0.4]])

    def test_geometric_drift_requires_hidden_states(self):
        inst = activation_probe.GeometricDriftProbe(
            reference_centroid=[0.1, 0.2, 0.3],
            calibration_profile="llama-domain-v1",
            normalization_scale=1.0,
        )
        with pytest.raises(ValueError, match="hidden states"):
            inst.score("test", "response")

    def test_geometric_drift_with_calibrated_data(self):
        inst = activation_probe.GeometricDriftProbe(
            reference_centroid=[0.1, 0.2, 0.3],
            calibration_profile="llama-domain-v1",
            normalization_scale=1.0,
        )
        assert inst.is_calibrated() is True
        assert inst.calibration_profile_id() == "llama-domain-v1"
        score = inst.score("test", "response", hidden_states=[[0.2, 0.3, 0.4]])
        assert 0.0 <= score <= 1.0

    def test_hidden_state_dimension_must_match_calibration(self):
        inst = activation_probe.GeometricDriftProbe(
            reference_centroid=[0.1, 0.2, 0.3],
            calibration_profile="llama-domain-v1",
            normalization_scale=1.0,
        )
        with pytest.raises(ValueError, match="dimension"):
            inst.score("test", "response", hidden_states=[[0.2, 0.3]])


class TestTextSimilarity:
    def test_consistent_samples_low_score(self):
        inst = text_similarity.StochasticSamplingConsistency(n_samples=3)
        samples = iter([
            "Hovedstaden i Frankrike er Paris.",
            "Frankrikes hovedstad er Paris.",
        ])
        score = inst.score(
            "Hva er hovedstaden i Frankrike?",
            "Hovedstaden i Frankrike er Paris.",
            generate_fn=lambda _prompt: next(samples),
        )
        assert score <= 0.7

    def test_different_samples_high_score(self):
        inst = text_similarity.StochasticSamplingConsistency(n_samples=3)
        samples = iter([
            "Kvantemekanikk er greit.",
            "Bananer er gule.",
        ])
        score = inst.score(
            "Hva er hovedstaden i Frankrike?",
            "Hovedstaden i Frankrike er Paris.",
            generate_fn=lambda _prompt: next(samples),
        )
        assert score >= 0.5

    def test_without_generate_fn_neutral(self):
        inst = text_similarity.StochasticSamplingConsistency()
        score = inst.score("test", "")
        assert score == 0.0

    def test_score_range(self):
        inst = text_similarity.StochasticSamplingConsistency(n_samples=3)
        samples = iter(["Paris er en by.", "Paris er hovedstaden."])
        score = inst.score("Paris", "Paris er hovedstaden", generate_fn=lambda _prompt: next(samples))
        assert 0.0 <= score <= 1.0


class TestSemanticEntropy:
    def test_consistent_texts_low_score(self):
        inst = semantic_entropy.JaccardSemanticEntropy(n_samples=3)
        samples = iter([
            "Hovedstaden i Frankrike er Paris.",
            "Frankrikes hovedstad er Paris.",
            "Hovedstaden i Frankrike er Paris.",
        ])
        score = inst.score(
            "test",
            "Paris er hovedstaden i Frankrike.",
            generate_fn=lambda _prompt: next(samples),
        )
        assert score <= 0.95

    def test_inconsistent_texts_high_score(self):
        inst = semantic_entropy.JaccardSemanticEntropy(n_samples=3)
        samples = iter([
            "Kvantemekanikk er komplisert.",
            "Bananer er gule.",
            "Månen er en satellitt.",
        ])
        score = inst.score(
            "test",
            "Paris er hovedstaden i Frankrike.",
            generate_fn=lambda _prompt: next(samples),
        )
        assert score >= 0.5

    def test_no_samples(self):
        inst = semantic_entropy.JaccardSemanticEntropy()
        score = inst.score("test", "Paris er hovedstaden i Frankrike.")
        assert score == 0.0


class TestCoTAuditor:
    def test_no_generate_fn(self):
        inst = cot_auditor.SelfAuditCoTAuditor()
        score = inst.score("test", "Paris er hovedstaden i Frankrike.")
        assert score == 0.0

    def test_score_range(self):
        inst = cot_auditor.SelfAuditCoTAuditor()
        for verdict in ["CONSISTENT", "INCONSISTENT", "UNSUPPORTED", "UNKNOWN"]:
            score = inst.score(
                "test",
                "La meg tenke... Kanskje Paris?",
                generate_fn=lambda _prompt, v=verdict: v,
            )
            assert 0.0 <= score <= 1.0

    def test_self_audit_instrument_declares_self_judging(self):
        # P0.5: a CoT auditor that reuses the same generate_fn as the ensemble
        # is self-judging; it must declare this so the report can flag the
        # limited independence of that measurement.
        inst = cot_auditor.SelfAuditCoTAuditor()
        assert inst.self_judging is True
