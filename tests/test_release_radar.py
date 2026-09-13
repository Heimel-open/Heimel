import json
from pathlib import Path

import pytest

from src.valo_platform.speider_connectors.observation_graph import ObservationGraph
from src.valo_platform.speider_modules.release_radar import (
    MANIFEST_SCHEMA,
    ReleaseRadar,
    load_manifest,
    parse_manifest,
    parse_observations,
    version_delta,
)


def manifest_document():
    return {
        "schema": MANIFEST_SCHEMA,
        "subjects": [
            {
                "subject_id": "requests",
                "kind": "dependency",
                "ecosystem": "python",
                "current_version": "2.31.0",
                "release_source": "psf/requests",
                "manifest_path": "pyproject.toml",
                "exposure": "development",
                "consequence_class": "low",
                "owner": "platform",
                "ignored_versions": [],
            },
            {
                "subject_id": "pydantic",
                "kind": "dependency",
                "ecosystem": "python",
                "current_version": "1.10.14",
                "release_source": "pydantic/pydantic",
                "manifest_path": "pyproject.toml",
                "exposure": "production",
                "consequence_class": "critical",
                "owner": "governance-runtime",
                "ignored_versions": ["2.0.1"],
            },
            {
                "subject_id": "provider-api",
                "kind": "provider",
                "ecosystem": "api",
                "current_version": "2026.7.0",
                "release_source": "provider/changelog",
                "manifest_path": "configs/providers.json",
                "exposure": "production",
                "consequence_class": "high",
                "owner": "model-router",
                "ignored_versions": [],
            },
        ],
    }


def observation(subject_id, version, title, notes, record_id, **extra):
    return {
        "subject_id": subject_id,
        "release_version": version,
        "title": title,
        "notes": notes,
        "release_url": f"https://example.test/{record_id}",
        "published_at": "2026-08-01T10:00:00Z",
        "observed_at": "2026-08-02T08:00:00Z",
        "source": "fixture",
        "source_record_id": record_id,
        **extra,
    }


def test_manifest_is_strict_sorted_and_duplicate_safe(tmp_path: Path):
    document = manifest_document()
    manifest = parse_manifest(document)
    assert [subject.subject_id for subject in manifest.subjects] == [
        "provider-api",
        "pydantic",
        "requests",
    ]
    assert len(manifest.manifest_digest) == 64

    path = tmp_path / "release-radar.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_manifest(path).manifest_digest == manifest.manifest_digest

    duplicate = manifest_document()
    duplicate["subjects"].append(dict(duplicate["subjects"][0]))
    with pytest.raises(ValueError, match="duplicate subject_id"):
        parse_manifest(duplicate)

    unknown = manifest_document()
    unknown["subjects"][0]["auto_upgrade"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        parse_manifest(unknown)


def test_version_delta_is_deterministic():
    assert version_delta("1.2.3", "2.0.0") == "major"
    assert version_delta("1.2.3", "1.3.0") == "minor"
    assert version_delta("1.2.3", "1.2.4") == "patch"
    assert version_delta("1.2.3", "1.2.3") == "same"
    assert version_delta("2.0.0", "1.9.9") == "older"
    assert version_delta(None, "2.0.0") == "unknown"


def test_filters_draft_prerelease_same_ignored_and_routine():
    manifest = parse_manifest(manifest_document())
    records = parse_observations(
        [
            observation(
                "pydantic",
                "2.0.0-beta.1",
                "Beta",
                "breaking change",
                "beta",
                prerelease=True,
            ),
            observation(
                "pydantic",
                "2.0.0",
                "Draft",
                "breaking change",
                "draft",
                draft=True,
            ),
            observation("pydantic", "1.10.14", "Same", "security fix", "same"),
            observation("pydantic", "2.0.1", "Ignored", "security fix", "ignored"),
            observation(
                "requests",
                "2.32.0",
                "Routine",
                "documentation cleanup",
                "routine",
            ),
        ]
    )
    report = ReleaseRadar().analyze(manifest, records)
    assert not report.findings
    assert {item.reason for item in report.ignored} == {
        "prerelease",
        "draft",
        "same",
        "manifest_ignored_version",
        "routine_release",
    }


def test_security_always_outranks_routine_major_and_same_tier_uses_exposure():
    manifest = parse_manifest(manifest_document())
    records = parse_observations(
        [
            observation(
                "requests",
                "2.32.3",
                "Requests patch",
                "Security fix for vulnerability",
                "security",
            ),
            observation("pydantic", "2.0.0", "Pydantic 2", "New stable release", "major"),
            observation(
                "provider-api",
                "2026.8.0",
                "Provider change",
                "Breaking change migration required",
                "breaking-high",
            ),
            observation(
                "requests",
                "2.32.4",
                "Requests change",
                "Breaking change migration required",
                "breaking-low",
            ),
        ]
    )
    report = ReleaseRadar().analyze(manifest, records)
    assert report.findings[0].primary_reason == "security_fix"
    breaking = [
        finding
        for finding in report.findings
        if finding.primary_reason == "breaking_change"
    ]
    assert breaking[0].subject_id == "provider-api"
    assert breaking[0].priority_score > breaking[1].priority_score


def test_unknown_subject_is_explicit_not_passed():
    report = ReleaseRadar().analyze(
        parse_manifest(manifest_document()),
        [
            observation(
                "not-mapped",
                "1.0.0",
                "Unknown",
                "security fix",
                "unknown",
            )
        ],
    )
    assert not report.findings
    assert report.unknown[0].reason == "subject_not_in_manifest"
    assert len(report.unknown[0].observation_digest) == 64


def test_report_and_finding_digests_are_stable_across_input_order():
    manifest = parse_manifest(manifest_document())
    first = observation("requests", "2.32.3", "Requests", "security fix", "a")
    second = observation("pydantic", "2.0.0", "Pydantic", "breaking change", "b")
    radar = ReleaseRadar()
    report_a = radar.analyze(manifest, [first, second])
    report_b = radar.analyze(manifest, [second, first])
    assert report_a.to_json() == report_b.to_json()
    assert report_a.report_digest == report_b.report_digest
    assert [finding.finding_digest for finding in report_a.findings] == [
        finding.finding_digest for finding in report_b.findings
    ]


def test_signal_emission_preserves_non_authority_boundary():
    manifest = parse_manifest(manifest_document())
    report = ReleaseRadar().analyze(
        manifest,
        [
            observation(
                "requests",
                "2.32.3",
                "Requests",
                "security fix",
                "security",
            )
        ],
    )
    graph = ObservationGraph()
    signal_ids = ReleaseRadar().emit_signals(graph, report)
    assert len(signal_ids) == 1
    signal = graph.signals[signal_ids[0]]
    assert signal.signal_type == "release_risk_observation"
    assert signal.metadata["observation_only"] is True
    assert signal.metadata["authority_granted"] is False
    assert signal.metadata["clearance_granted"] is False
    assert signal.metadata["execution_granted"] is False
    assert signal.metadata["remediation_permitted"] is False
    assert signal.value["proposed_review_action"] == "review_exposure_and_patch"


def test_duplicate_observation_and_unknown_fields_fail_closed():
    record = observation(
        "requests",
        "2.32.3",
        "Requests",
        "security fix",
        "same-record",
    )
    with pytest.raises(ValueError, match="duplicate observation"):
        parse_observations([record, record])
    invalid = dict(record)
    invalid["install"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        parse_observations([invalid])
