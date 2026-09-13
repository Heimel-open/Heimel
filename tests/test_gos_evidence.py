import unittest
from datetime import datetime, timedelta, timezone

from lib.gos_evidence import (
    AUTHORITY_EFFECT,
    AffectedPartyEvidenceLink,
    AssumptionNode,
    DatasetRecord,
    DatasetRegistry,
    EvidenceGraph,
    EvidenceNode,
    FreshnessPolicy,
    InvalidationTrigger,
    StakeholderGraph,
    StakeholderNode,
    TransformationStep,
    ValidityWindow,
    content_digest,
    deterministic_digest,
    evaluate_assumption_status,
    evaluate_freshness,
    evaluate_representation_quality,
    evaluate_semantic_integrity,
    evidence_from_mapping,
)


def _now() -> datetime:
    return datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def evidence(**overrides):
    data = {
        "evidence_id": "ev-1",
        "kind": "observation",
        "content": "observed migration flows",
        "original_language": "no",
        "language": "no",
        "source_ref": "fieldnotes/2026-07",
        "recorded_at": _now() - timedelta(days=1),
        "valid_until": _now() + timedelta(days=7),
        "provenance": ("reporter:anna",),
        "derived_from": (),
        "independence": "independent",
        "transformation_history": (),
    }
    data.update(overrides)
    return data


def assumption(**overrides):
    data = {
        "assumption_id": "as-1",
        "claim": "migration is seasonal",
        "owner": "founder@valo",
        "validity_window": ValidityWindow(
            starts_at=_now() - timedelta(days=30),
            valid_until=_now() + timedelta(days=30),
        ),
        "invalidation_triggers": (
            InvalidationTrigger(
                trigger_id="t-seasonal",
                condition="counter-evidence shows year-round migration",
                evidence_kinds=("observation",),
                matches_content_substring="year-round",
            ),
        ),
        "supporting_evidence_refs": ("ev-1",),
        "counter_evidence_refs": (),
    }
    data.update(overrides)
    return AssumptionNode(**data)


class EvidenceNotInstructionTests(unittest.TestCase):
    def test_evidence_has_no_decision_or_authority_field(self):
        node = EvidenceNode(**evidence())
        self.assertEqual(node.authority_effect, AUTHORITY_EFFECT)
        allowed = set(
            {
                "evidence_id",
                "kind",
                "content",
                "original_language",
                "language",
                "source_ref",
                "recorded_at",
                "valid_until",
                "provenance",
                "derived_from",
                "independence",
                "transformation_history",
            }
        )
        self.assertTrue(allowed.issuperset(vars(node)))

    def test_evidence_cannot_be_coerced_into_an_instruction(self):
        node = EvidenceNode(**evidence())
        with self.assertRaises(ValueError):
            node.to_instruction()

    def test_evidence_constructor_rejects_instruction_like_keywords(self):
        with self.assertRaises(TypeError):
            EvidenceNode(
                **{
                    **evidence(),
                    "approval": "grant",
                }
            )

    def test_evidence_mapping_rejects_authority_field_fail_closed(self):
        with self.assertRaises(ValueError):
            evidence_from_mapping({**evidence(), "clearance": "granted"})

    def test_evidence_mapping_rejects_unknown_field_fail_closed(self):
        with self.assertRaises(ValueError):
            evidence_from_mapping({**evidence(), "mystery": "x"})

    def test_assumption_has_no_authority_effect(self):
        node = assumption()
        self.assertEqual(node.authority_effect, AUTHORITY_EFFECT)


class DeterministicDigestTests(unittest.TestCase):
    def test_digest_is_deterministic_across_calls(self):
        a = evidence()
        b = evidence()
        self.assertEqual(
            EvidenceNode(**a).digest, EvidenceNode(**b).digest
        )

    def test_digest_changes_when_content_changes(self):
        a = EvidenceNode(**evidence()).digest
        b = EvidenceNode(**evidence(content="different")).digest
        self.assertNotEqual(a, b)

    def test_any_internal_ordering_produces_same_digest(self):
        first = {"b": 1, "a": 2, "c": [3, 1]}
        second = {"c": [3, 1], "a": 2, "b": 1}
        self.assertEqual(
            deterministic_digest(first), deterministic_digest(second)
        )

    def test_translation_changes_content_digest(self):
        no = content_digest(content="hei", language="no")
        en = content_digest(content="hei", language="en")
        self.assertNotEqual(no, en)


class AssumptionInvalidationTests(unittest.TestCase):
    def test_assumption_invalidated_by_trigger(self):
        counter = EvidenceNode(
            **evidence(
                evidence_id="ev-counter",
                kind="observation",
                content="year-round migration observed",
            )
        )
        status = evaluate_assumption_status(
            assumption(**{"counter_evidence_refs": ("ev-counter",)}),
            {"ev-counter": counter},
            now=_now(),
        )
        self.assertEqual(status.state, "invalidated")
        self.assertFalse(status.valid)
        self.assertTrue(any("t-seasonal" in r for r in status.reasons))

    def test_assumption_valid_when_no_trigger_fires(self):
        node = EvidenceNode(**evidence())
        status = evaluate_assumption_status(
            assumption(), {"ev-1": node}, now=_now()
        )
        self.assertEqual(status.state, "valid")
        self.assertTrue(status.valid)

    def test_assumption_not_active_before_window(self):
        node = EvidenceNode(**evidence())
        late_window = assumption(
            validity_window=ValidityWindow(
                starts_at=_now() + timedelta(days=1),
                valid_until=_now() + timedelta(days=30),
            )
        )
        status = evaluate_assumption_status(
            late_window, {"ev-1": node}, now=_now()
        )
        self.assertEqual(status.state, "not_active")

    def test_assumption_expires_after_validity_window(self):
        node = EvidenceNode(**evidence())
        expired = assumption(
            validity_window=ValidityWindow(
                starts_at=_now() - timedelta(days=30),
                valid_until=_now() - timedelta(days=1),
            )
        )
        status = evaluate_assumption_status(
            expired, {"ev-1": node}, now=_now()
        )
        self.assertEqual(status.state, "expired")

    def test_assumption_becomes_stale_without_recent_support(self):
        node = EvidenceNode(
            **evidence(
                recorded_at=_now() - timedelta(days=10),
                valid_until=_now() - timedelta(days=1),
            )
        )
        stale = assumption(
            validity_window=ValidityWindow(
                starts_at=_now() - timedelta(days=30),
                valid_until=_now() + timedelta(days=30),
            ),
            next_review_at=_now() - timedelta(days=1),
        )
        status = evaluate_assumption_status(
            stale, {"ev-1": node}, now=_now()
        )
        self.assertEqual(status.state, "stale")

    def test_trigger_kind_mismatch_does_not_invalidate(self):
        counter = EvidenceNode(
            **evidence(
                evidence_id="ev-counter",
                kind="report",
                content="year-round migration observed",
            )
        )
        status = evaluate_assumption_status(
            assumption(**{"counter_evidence_refs": ("ev-counter",)}),
            {"ev-counter": counter},
            now=_now(),
        )
        self.assertEqual(status.state, "valid")


class DatasetPurposeBindingTests(unittest.TestCase):
    def test_dataset_binds_purpose_and_permitted_use(self):
        registry = DatasetRegistry(
            (
                DatasetRecord(
                    dataset_id="ds-1",
                    name="migration survey",
                    purpose_ref="pr-migration",
                    permitted_use=("research", "impact_assessment"),
                    owner="foundation@valo",
                ),
            )
        )
        dataset = registry.get("ds-1")
        self.assertIsNotNone(dataset)
        self.assertEqual(dataset.purpose_ref, "pr-migration")
        self.assertTrue(dataset.permits("research"))
        self.assertFalse(dataset.permits("marketing"))

    def test_dataset_registry_groups_by_purpose(self):
        registry = DatasetRegistry(
            (
                DatasetRecord(
                    dataset_id="ds-1",
                    name="a",
                    purpose_ref="pr-migration",
                    permitted_use=("research",),
                    owner="o",
                ),
                DatasetRecord(
                    dataset_id="ds-2",
                    name="b",
                    purpose_ref="pr-migration",
                    permitted_use=("research",),
                    owner="o",
                ),
                DatasetRecord(
                    dataset_id="ds-3",
                    name="c",
                    purpose_ref="pr-other",
                    permitted_use=("research",),
                    owner="o",
                ),
            )
        )
        self.assertEqual(
            [d.dataset_id for d in registry.datasets_for_purpose("pr-migration")],
            ["ds-1", "ds-2"],
        )

    def test_dataset_requires_explicit_permitted_use(self):
        with self.assertRaises(ValueError):
            DatasetRecord(
                dataset_id="ds-x",
                name="x",
                purpose_ref="pr-x",
                permitted_use=(),
                owner="o",
            )

    def test_duplicate_dataset_id_is_rejected(self):
        record = DatasetRecord(
            dataset_id="ds-1",
            name="a",
            purpose_ref="pr",
            permitted_use=("research",),
            owner="o",
        )
        registry = DatasetRegistry((record,))
        with self.assertRaises(ValueError):
            registry.register(record)


class MinorityRetentionTests(unittest.TestCase):
    def test_minority_affected_party_evidence_is_retained(self):
        graph = StakeholderGraph(
            stakeholders=(
                StakeholderNode(
                    stakeholder_id="st-majority",
                    name="majority",
                    group="majority",
                    affected_party=True,
                ),
                StakeholderNode(
                    stakeholder_id="st-minority",
                    name="minority",
                    group="minority-group",
                    affected_party=True,
                    minority=True,
                ),
            ),
            evidence_links=(
                AffectedPartyEvidenceLink(
                    link_id="lk-1",
                    stakeholder_id="st-majority",
                    evidence_id="ev-majority",
                    impact_class="positive",
                    representation="majority statement",
                ),
                AffectedPartyEvidenceLink(
                    link_id="lk-2",
                    stakeholder_id="st-minority",
                    evidence_id="ev-minority",
                    impact_class="negative",
                    representation="minority statement",
                ),
            ),
        )
        enumerated = graph.affected_party_evidence()
        self.assertEqual(len(enumerated), 2)
        self.assertEqual(
            {link.stakeholder_id for _, link in enumerated},
            {"st-majority", "st-minority"},
        )
        minority = graph.stakeholders["st-minority"]
        self.assertTrue(minority.minority)
        self.assertTrue(minority.affected_party)

    def test_coverage_counts_minority_parties(self):
        graph = StakeholderGraph(
            stakeholders=(
                StakeholderNode(
                    stakeholder_id="st-a",
                    name="a",
                    group="g1",
                    affected_party=True,
                    minority=True,
                ),
                StakeholderNode(
                    stakeholder_id="st-b",
                    name="b",
                    group="g1",
                    affected_party=True,
                ),
                StakeholderNode(
                    stakeholder_id="st-c",
                    name="c",
                    group="g2",
                    affected_party=True,
                ),
            ),
            evidence_links=(
                AffectedPartyEvidenceLink(
                    link_id="lk-1",
                    stakeholder_id="st-a",
                    evidence_id="ev-a",
                    impact_class="negative",
                    representation="a",
                ),
                AffectedPartyEvidenceLink(
                    link_id="lk-2",
                    stakeholder_id="st-b",
                    evidence_id="ev-b",
                    impact_class="negative",
                    representation="b",
                ),
                AffectedPartyEvidenceLink(
                    link_id="lk-3",
                    stakeholder_id="st-c",
                    evidence_id="ev-c",
                    impact_class="negative",
                    representation="c",
                ),
            ),
        )
        self.assertEqual(graph.coverage(), {"g1": 2, "g2": 1})

    def test_affected_party_without_evidence_is_surfaced(self):
        graph = StakeholderGraph(
            stakeholders=(
                StakeholderNode(
                    stakeholder_id="st-unrepresented",
                    name="u",
                    group="g",
                    affected_party=True,
                ),
            )
        )
        self.assertEqual(
            graph.affected_party_ids_without_evidence(),
            ("st-unrepresented",),
        )

    def test_representation_quality_flags_missing_voice(self):
        graph = StakeholderGraph(
            stakeholders=(
                StakeholderNode(
                    stakeholder_id="st-v",
                    name="v",
                    group="g",
                    affected_party=True,
                    vulnerable=True,
                    has_direct_voice=False,
                ),
            ),
            evidence_links=(
                AffectedPartyEvidenceLink(
                    link_id="lk-1",
                    stakeholder_id="st-v",
                    evidence_id="ev-v",
                    impact_class="negative",
                    representation="proxy statement",
                ),
            ),
        )
        reports = evaluate_representation_quality(graph)
        report = reports[0]
        self.assertFalse(report.adequate)
        self.assertIn("proxy_only_voice", report.reasons)


class StaleCircularContaminatedSurfacingTests(unittest.TestCase):
    def test_stale_evidence_is_surfaced(self):
        old = EvidenceNode(
            **evidence(
                evidence_id="ev-old",
                recorded_at=_now() - timedelta(days=10),
                valid_until=_now() - timedelta(days=1),
            )
        )
        fresh = EvidenceNode(**evidence(evidence_id="ev-fresh"))
        graph = EvidenceGraph(evidence=(old, fresh))
        self.assertEqual(graph.stale_evidence(now=_now()), ("ev-old",))

    def test_circular_evidence_is_detected(self):
        a = EvidenceNode(
            **evidence(evidence_id="ev-a", derived_from=("ev-b",))
        )
        b = EvidenceNode(
            **evidence(evidence_id="ev-b", derived_from=("ev-a",))
        )
        graph = EvidenceGraph(evidence=(a, b))
        cycles = graph.circular_evidence()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0]), 2)

    def test_contaminated_evidence_is_surfaced(self):
        a = EvidenceNode(**evidence(evidence_id="ev-a"))
        b = EvidenceNode(**evidence(evidence_id="ev-b"))
        graph = EvidenceGraph(evidence=(a, b))
        self.assertEqual(graph.contamination_flag("ev-a"), "contaminated")
        self.assertEqual(graph.contamination_flag("ev-b"), "contaminated")
        self.assertEqual(
            set(graph.contaminated_evidence()), {"ev-a", "ev-b"}
        )

    def test_derived_from_contaminated_evidence_is_flagged(self):
        a = EvidenceNode(**evidence(evidence_id="ev-a"))
        b = EvidenceNode(**evidence(evidence_id="ev-b"))
        c = EvidenceNode(
            **evidence(evidence_id="ev-c", derived_from=("ev-b",))
        )
        graph = EvidenceGraph(evidence=(a, b, c))
        self.assertEqual(
            set(graph.contaminated_evidence()), {"ev-a", "ev-b", "ev-c"}
        )

    def test_semantically_degraded_evidence_is_surfaced(self):
        node = EvidenceNode(
            **evidence(
                evidence_id="ev-translated",
                original_language="no",
                language="en",
                transformation_history=(
                    TransformationStep(
                        from_language="no",
                        to_language="en",
                        method="machine-translate",
                        performed_by="worker:1",
                        performed_at=_now(),
                        source_digest=content_digest(
                            content="observed migration flows", language="no"
                        ),
                        content_digest=content_digest(
                            content="observed migration flows", language="en"
                        ),
                    ),
                ),
            )
        )
        graph = EvidenceGraph(evidence=(node,))
        self.assertEqual(graph.semantically_degraded_evidence(), ())
        languages, flags = evaluate_semantic_integrity(node)
        self.assertEqual(languages, ("no", "en"))
        self.assertEqual(flags, ())

    def test_lossy_transformation_is_semantically_degraded(self):
        original = content_digest(
            content="observed migration flows", language="no"
        )
        compressed = content_digest(
            content="observed migration flows", language="en"
        )
        node = EvidenceNode(
            **evidence(
                evidence_id="ev-lossy",
                original_language="no",
                language="en",
                transformation_history=(
                    TransformationStep(
                        from_language="no",
                        to_language="en",
                        method="lossy-compress",
                        performed_by="worker:1",
                        performed_at=_now(),
                        source_digest=original,
                        content_digest=compressed,
                    ),
                ),
            )
        )
        graph = EvidenceGraph(evidence=(node,))
        self.assertEqual(graph.semantically_degraded_evidence(), ("ev-lossy",))

    def test_all_issues_surfaces_everything(self):
        a = EvidenceNode(**evidence(evidence_id="ev-a"))
        old = EvidenceNode(
            **evidence(
                evidence_id="ev-old",
                recorded_at=_now() - timedelta(days=10),
                valid_until=_now() - timedelta(days=1),
            )
        )
        cycle_x = EvidenceNode(
            **evidence(evidence_id="ev-x", derived_from=("ev-y",))
        )
        cycle_y = EvidenceNode(
            **evidence(evidence_id="ev-y", derived_from=("ev-x",))
        )
        graph = EvidenceGraph(evidence=(a, old, cycle_x, cycle_y))
        issues = graph.all_issues(now=_now())
        self.assertIn("ev-old", issues["stale_evidence"])
        self.assertEqual(len(issues["circular_chains"]), 1)
        self.assertIn("ev-a", issues["contaminated_evidence"])
        self.assertEqual(issues["semantically_degraded_evidence"], ())


class FreshnessAndFailClosedTests(unittest.TestCase):
    def test_freshness_ok(self):
        node = EvidenceNode(**evidence())
        ok, reasons = evaluate_freshness(node, now=_now())
        self.assertTrue(ok)
        self.assertEqual(reasons, ())

    def test_max_age_policy_flags_old_evidence(self):
        node = EvidenceNode(**evidence())
        ok, reasons = evaluate_freshness(
            node,
            now=_now(),
            policy=FreshnessPolicy(max_age=timedelta(hours=1)),
        )
        self.assertFalse(ok)
        self.assertIn("max_age_exceeded", reasons)

    def test_malformed_evidence_mapping_fails_closed(self):
        with self.assertRaises(ValueError):
            evidence_from_mapping({})
        with self.assertRaises(ValueError):
            evidence_from_mapping(
                {**evidence(), "transformation_history": ({"wrong": 1},)}
            )

    def test_malformed_assumption_fails_closed(self):
        with self.assertRaises(ValueError):
            AssumptionNode(
                assumption_id="as-x",
                claim="x",
                owner="o",
                validity_window=ValidityWindow(starts_at=_now()),
                invalidation_triggers=(),
            )

    def test_naive_datetime_is_rejected(self):
        naive = datetime(2026, 8, 1, 12, 0)
        with self.assertRaises(ValueError):
            EvidenceNode(**evidence(recorded_at=naive))

    def test_transformation_step_requires_different_languages(self):
        with self.assertRaises(ValueError):
            TransformationStep(
                from_language="no",
                to_language="no",
                method="translate",
                performed_by="worker:1",
                performed_at=_now(),
            )


if __name__ == "__main__":
    unittest.main()
