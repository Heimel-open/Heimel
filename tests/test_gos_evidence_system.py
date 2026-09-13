import unittest
from datetime import datetime, timedelta, timezone

from lib.gos_evidence_system import (
    AUTHORITY_EFFECT,
    AffectedPartyEvidenceLink,
    Assumption,
    AssumptionStatus,
    DatasetRecord,
    DatasetRegistry,
    DecisionRecord,
    EvidenceAssumptionGraph,
    EvidenceRecord,
    FreshnessPolicy,
    InvalidationTrigger,
    Stakeholder,
    StakeholderGraph,
    TransformationStep,
    ValidityWindow,
    content_digest,
    deterministic_digest,
    evaluate_assumption_status,
    evaluate_assumptions,
    evaluate_freshness,
    evaluate_representation_quality,
    evaluate_semantic_integrity,
    evidence_from_mapping,
    find_circular_evidence,
    mechanical_no_instruction_surface,
    surface_contaminated_evidence,
    surface_evidence_issues,
    surface_semantically_degraded_evidence,
    surface_stale_evidence,
)


def _now():
    return datetime.now(timezone.utc)


def _evidence(evidence_id="e1", content="observed output rose 4%", **kwargs):
    now = _now()
    defaults = dict(
        evidence_id=evidence_id,
        kind="observation",
        content=content,
        original_language="no",
        language="no",
        source_ref="src:1",
        recorded_at=now,
        valid_until=now + timedelta(days=30),
    )
    defaults.update(kwargs)
    return EvidenceRecord(**defaults)


class EvidenceNeverInstructionTests(unittest.TestCase):
    def test_evidence_has_no_instruction_fields_and_cannot_be_coerced(self):
        now = _now()
        with self.assertRaises(TypeError):
            EvidenceRecord(
                evidence_id="e1",
                kind="observation",
                content="x",
                original_language="no",
                language="no",
                source_ref="src:1",
                recorded_at=now,
                execute=True,
            )
        with self.assertRaises(TypeError):
            _evidence(authority="root")
        with self.assertRaises(TypeError):
            _evidence(clearance="full")
        with self.assertRaises(TypeError):
            _evidence(permit=True)
        record = _evidence()
        self.assertEqual(record.authority_effect, AUTHORITY_EFFECT)
        with self.assertRaisesRegex(ValueError, "never instruction"):
            record.to_instruction()

    def test_evidence_from_mapping_rejects_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "unknown evidence fields"):
            evidence_from_mapping(
                {
                    "evidence_id": "e1",
                    "kind": "observation",
                    "content": "x",
                    "original_language": "no",
                    "language": "no",
                    "source_ref": "src:1",
                    "recorded_at": _now(),
                    "mystery_field": True,
                }
            )

    def test_mechanical_invariant_has_no_clearance_permit_execute_surface(self):
        self.assertEqual(mechanical_no_instruction_surface(), ())


class AssumptionTests(unittest.TestCase):
    def _assumption(self, **kwargs):
        now = _now()
        defaults = dict(
            assumption_id="a1",
            claim="market growth exceeds 5% this year",
            owner="p&l-owner:1",
            validity_window=ValidityWindow(
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=180),
            ),
            invalidation_triggers=(
                InvalidationTrigger(
                    trigger_id="t1",
                    condition="reported growth falls below 5%",
                    evidence_kinds=("measurement",),
                    matches_content_substring="growth below 5%",
                ),
            ),
            supporting_evidence_refs=("e1",),
        )
        defaults.update(kwargs)
        return Assumption(**defaults)

    def test_assumption_has_validity_window(self):
        assumption = self._assumption()
        self.assertTrue(assumption.validity_window.active())
        self.assertIsNotNone(assumption.validity_window.valid_until)

    def test_assumption_has_invalidation_trigger(self):
        assumption = self._assumption()
        self.assertTrue(assumption.invalidation_triggers)
        trigger = assumption.invalidation_triggers[0]
        self.assertTrue(trigger.automatic)

    def test_assumption_invalidated_by_firing_trigger(self):
        now = _now()
        assumption = self._assumption(counter_evidence_refs=("e2",))
        counter = _evidence(
            evidence_id="e2",
            kind="measurement",
            content="Q3 reported growth below 5%",
            source_ref="src:measure",
            recorded_at=now - timedelta(days=1),
        )
        status = evaluate_assumption_status(
            assumption, {"e2": counter}, now=now
        )
        self.assertEqual(status.state, "invalidated")
        self.assertTrue(status.reasons)

    def test_assumption_expired_when_validity_window_passes(self):
        now = _now()
        assumption = self._assumption(
            validity_window=ValidityWindow(
                starts_at=now - timedelta(days=10),
                valid_until=now - timedelta(days=1),
            )
        )
        status = evaluate_assumption_status(
            assumption, {"e1": _evidence()}, now=now
        )
        self.assertEqual(status.state, "expired")


class EvidenceAssumptionGraphTests(unittest.TestCase):
    def test_graph_connects_evidence_assumptions_and_decisions(self):
        now = _now()
        e1 = _evidence("e1")
        e2 = _evidence("e2", content="independent sales report", source_ref="src:2")
        a1 = Assumption(
            assumption_id="a1",
            claim="market growth exceeds 5%",
            owner="owner:1",
            validity_window=ValidityWindow(
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
            invalidation_triggers=(
                InvalidationTrigger(
                    trigger_id="t1",
                    condition="growth misses threshold",
                    matches_content_substring="below 5%",
                ),
            ),
            supporting_evidence_refs=("e1",),
            counter_evidence_refs=("e2",),
        )
        d1 = DecisionRecord(
            decision_id="d1",
            decision_ref="decision:1",
            rationale="evidence supports continued investment",
            evidence_refs=("e1", "e2"),
            assumption_refs=("a1",),
            decided_at=now,
            outcome="adopt",
        )
        graph = EvidenceAssumptionGraph(
            evidence=(e1, e2), assumptions=(a1,), decisions=(d1,)
        )

        self.assertEqual(
            {r.evidence_id for r in graph.evidence_for_assumption("a1")},
            {"e1", "e2"},
        )
        self.assertEqual(graph.assumptions_for_evidence("e1"), ("a1",))
        self.assertEqual(
            {r.evidence_id for r in graph.evidence_for_decision("d1")},
            {"e1", "e2"},
        )
        self.assertEqual(graph.assumptions_for_decision("d1"), ("a1",))
        self.assertEqual(graph.decisions_for_assumption("a1"), ("d1",))


class DatasetRegistryTests(unittest.TestCase):
    def _dataset(self):
        return DatasetRecord(
            dataset_id="ds:1",
            name="customer impact panel",
            purpose_ref="purpose:financial-inclusion",
            permitted_use=("impact-measurement", "reporting"),
            owner="data-owner:1",
            prohibited_use=("advertising", "insurance-pricing"),
        )

    def test_dataset_links_to_purpose(self):
        dataset = self._dataset()
        self.assertEqual(dataset.purpose_ref, "purpose:financial-inclusion")

    def test_dataset_has_permitted_use(self):
        dataset = self._dataset()
        self.assertIn("impact-measurement", dataset.permitted_use)
        self.assertTrue(dataset.permits("reporting"))
        self.assertFalse(dataset.permits("advertising"))

    def test_registry_indexes_by_purpose(self):
        registry = DatasetRegistry([self._dataset()])
        matched = registry.datasets_for_purpose("purpose:financial-inclusion")
        self.assertEqual([d.dataset_id for d in matched], ["ds:1"])
        self.assertEqual(
            registry.datasets_for_purpose("purpose:unrelated"), ()
        )


class FreshnessAndQualityTests(unittest.TestCase):
    def test_stale_evidence_surfaces(self):
        now = _now()
        fresh = _evidence(
            "e-fresh", valid_until=now + timedelta(days=5)
        )
        stale = _evidence(
            "e-stale",
            recorded_at=now - timedelta(days=5),
            valid_until=now - timedelta(days=1),
        )
        graph = EvidenceAssumptionGraph(evidence=(fresh, stale))
        surfaced = surface_stale_evidence(graph, now=now)
        self.assertEqual(surfaced, ("e-stale",))

    def test_circular_evidence_detection(self):
        now = _now()
        e_a = _evidence("e-a", derived_from=("e-b",))
        e_b = _evidence("e-b", derived_from=("e-a",), source_ref="src:2")
        graph = EvidenceAssumptionGraph(evidence=(e_a, e_b))
        cycles = find_circular_evidence(graph)
        self.assertTrue(cycles)
        ids = set(cycles[0])
        self.assertTrue({"e-a", "e-b"}.issubset(ids))

    def test_contaminated_evidence_surfaces(self):
        now = _now()
        text = "identical passage reused as independent proof"
        e_orig = _evidence("e-1", content=text, source_ref="src:a")
        e_copy = _evidence(
            "e-2", content=text, source_ref="src:b", independence="independent"
        )
        graph = EvidenceAssumptionGraph(evidence=(e_orig, e_copy))
        contaminated = surface_contaminated_evidence(graph)
        self.assertIn("e-1", contaminated)
        self.assertIn("e-2", contaminated)

    def test_semantically_degraded_evidence_surfaces(self):
        now = _now()
        original = _evidence(
            "e-good",
            content="reguleringsdata for kundeutfall",
            original_language="no",
            language="en",
            transformation_history=(
                TransformationStep(
                    from_language="no",
                    to_language="en",
                    method="human-translation",
                    performed_by="translator:1",
                    performed_at=now - timedelta(days=2),
                    source_digest=content_digest(
                        content="reguleringsdata for kundeutfall", language="no"
                    ),
                    content_digest=content_digest(
                        content="regulatory customer outcome data", language="en"
                    ),
                ),
            ),
        )
        broken = _evidence(
            "e-broken",
            content="translated but the chain has a gap",
            original_language="no",
            language="en",
            transformation_history=(
                TransformationStep(
                    from_language="no",
                    to_language="en",
                    method="human-translation",
                    performed_by="translator:1",
                    performed_at=now - timedelta(days=2),
                    source_digest=None,
                    content_digest=None,
                ),
            ),
        )
        graph = EvidenceAssumptionGraph(evidence=(original, broken))
        degraded = surface_semantically_degraded_evidence(graph)
        self.assertNotIn("e-good", degraded)
        self.assertIn("e-broken", degraded)

    def test_surface_evidence_issues_aggregates_all(self):
        now = _now()
        stale = _evidence(
            "e-stale",
            recorded_at=now - timedelta(days=5),
            valid_until=now - timedelta(days=1),
        )
        e_a = _evidence("e-a", derived_from=("e-b",))
        e_b = _evidence("e-b", derived_from=("e-a",), source_ref="src:2")
        dup = _evidence("e-dup", content="shared content proof")
        dup2 = _evidence("e-dup2", content="shared content proof", source_ref="src:3")
        graph = EvidenceAssumptionGraph(
            evidence=(stale, e_a, e_b, dup, dup2)
        )
        issues = surface_evidence_issues(graph, now=now)
        self.assertTrue(issues.any)
        self.assertIn("e-stale", issues.stale_evidence)
        self.assertTrue(issues.circular_chains)
        self.assertIn("e-dup", issues.contaminated_evidence)


class StakeholderTests(unittest.TestCase):
    def _graph_with_minority_evidence(self):
        now = _now()
        minority = Stakeholder(
            stakeholder_id="st:minority",
            name="migrant workers",
            group="workers-minority",
            affected_party=True,
            vulnerable=True,
            has_direct_voice=True,
            consent_status="consented",
        )
        majority = Stakeholder(
            stakeholder_id="st:majority",
            name="full-time staff",
            group="workers",
            affected_party=True,
            consent_status="consented",
        )
        evidence = _evidence("e-minority", content="shift scheduling impact")
        graph = StakeholderGraph(
            stakeholders=(minority, majority),
            evidence_links=(
                AffectedPartyEvidenceLink(
                    link_id="l1",
                    stakeholder_id="st:minority",
                    evidence_id="e-minority",
                    impact_class="exposure",
                    representation="direct interview record",
                ),
                AffectedPartyEvidenceLink(
                    link_id="l2",
                    stakeholder_id="st:majority",
                    evidence_id="e-minority",
                    impact_class="benefit",
                    representation="survey aggregate",
                ),
            ),
        )
        return graph, evidence

    def test_minority_affected_party_evidence_is_retained(self):
        graph, evidence = self._graph_with_minority_evidence()
        party_evidence = graph.affected_party_evidence()
        ids = {link.stakeholder_id for _, link in party_evidence}
        self.assertIn("st:minority", ids)
        self.assertIn("st:majority", ids)
        self.assertEqual(
            {link.evidence_id for _, link in party_evidence},
            {"e-minority"},
        )

    def test_coverage_counts_minority_group(self):
        graph, _ = self._graph_with_minority_evidence()
        coverage = graph.coverage()
        self.assertIn("workers-minority", coverage)
        self.assertEqual(coverage["workers-minority"], 1)

    def test_representation_quality_check(self):
        now = _now()
        unrepresented = Stakeholder(
            stakeholder_id="st:no-evidence",
            name="future residents",
            group="ecosystem",
            affected_party=True,
            vulnerable=True,
        )
        graph = StakeholderGraph(stakeholders=(unrepresented,))
        reports = evaluate_representation_quality(graph)
        report = reports[0]
        self.assertFalse(report.adequate)
        self.assertIn("no_affected_party_evidence", report.reasons)

        graph, _ = self._graph_with_minority_evidence()
        minority_report = evaluate_representation_quality(
            graph, stakeholder_ids=("st:minority",)
        )[0]
        self.assertTrue(minority_report.adequate)


class MultilingualIntegrityTests(unittest.TestCase):
    def _translated_evidence(self):
        now = _now()
        return _evidence(
            "e-multi",
            content="regulatory customer outcome data",
            original_language="no",
            language="en",
            transformation_history=(
                TransformationStep(
                    from_language="no",
                    to_language="en",
                    method="human-translation",
                    performed_by="translator:1",
                    performed_at=now - timedelta(days=2),
                    source_digest=content_digest(
                        content="regulatory customer outcome data",
                        language="no",
                    ),
                    content_digest=content_digest(
                        content="regulatory customer outcome data",
                        language="en",
                    ),
                ),
            ),
        )

    def test_multilingual_semantic_integrity_evaluation(self):
        evidence = self._translated_evidence()
        result = evaluate_semantic_integrity(evidence)
        self.assertEqual(result.languages, ("no", "en"))
        self.assertFalse(result.degraded)
        self.assertEqual(result.integrity_score, 1.0)

    def test_broken_chain_is_semantically_degraded(self):
        now = _now()
        evidence = _evidence(
            "e-gap",
            content="translated text",
            original_language="no",
            language="en",
            transformation_history=(
                TransformationStep(
                    from_language="no",
                    to_language="en",
                    method="lossy-compress",
                    performed_by="model:1",
                    performed_at=now - timedelta(days=1),
                    source_digest=None,
                    content_digest=None,
                ),
            ),
        )
        result = evaluate_semantic_integrity(evidence)
        self.assertTrue(result.degraded)
        self.assertLess(result.integrity_score, 1.0)

    def test_original_language_remains_available(self):
        evidence = self._translated_evidence()
        self.assertEqual(evidence.original_language, "no")
        self.assertEqual(evidence.language, "en")

    def test_transformation_history_remains_available(self):
        evidence = self._translated_evidence()
        self.assertEqual(len(evidence.transformation_history), 1)
        step = evidence.transformation_history[0]
        self.assertEqual(step.from_language, "no")
        self.assertEqual(step.to_language, "en")
        self.assertEqual(step.method, "human-translation")


class DigestTests(unittest.TestCase):
    def test_deterministic_digests(self):
        first = deterministic_digest({"b": 2, "a": 1, "nested": {"y": True, "x": "z"}})
        second = deterministic_digest({"a": 1, "b": 2, "nested": {"x": "z", "y": True}})
        self.assertEqual(first, second)
        different = deterministic_digest({"a": 1, "b": 2, "nested": {"x": "z"}})
        self.assertNotEqual(first, different)

    def test_content_digest_is_deterministic_and_language_sensitive(self):
        same = content_digest(content="hei", language="no")
        self.assertEqual(same, content_digest(content="hei", language="no"))
        translated = content_digest(content="hei", language="en")
        self.assertNotEqual(same, translated)


class AssumptionLifecycleAggregateTests(unittest.TestCase):
    def test_evaluate_assumptions_aggregate(self):
        now = _now()
        a_valid = Assumption(
            assumption_id="a-valid",
            claim="supply stable",
            owner="owner:1",
            validity_window=ValidityWindow(
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
            invalidation_triggers=(
                InvalidationTrigger(
                    trigger_id="t1", condition="supply drops", automatic=True
                ),
            ),
            supporting_evidence_refs=("e1",),
        )
        a_invalid = Assumption(
            assumption_id="a-invalid",
            claim="pricing holds",
            owner="owner:2",
            validity_window=ValidityWindow(
                starts_at=now - timedelta(days=1),
                valid_until=now + timedelta(days=30),
            ),
            invalidation_triggers=(
                InvalidationTrigger(
                    trigger_id="t2",
                    condition="price floor breached",
                    matches_content_substring="price floor breached",
                ),
            ),
            counter_evidence_refs=("e-bad",),
        )
        evidence = _evidence("e1")
        counter = _evidence(
            "e-bad",
            content="price floor breached in q2",
            source_ref="src:market",
        )
        graph = EvidenceAssumptionGraph(
            evidence=(evidence, counter),
            assumptions=(a_valid, a_invalid),
        )
        statuses = {s.assumption_id: s for s in evaluate_assumptions(graph, now=now)}
        self.assertEqual(statuses["a-valid"].state, "valid")
        self.assertEqual(statuses["a-invalid"].state, "invalidated")


if __name__ == "__main__":
    unittest.main()
