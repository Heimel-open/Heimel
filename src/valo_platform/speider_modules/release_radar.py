"""Governed Release Radar for Speider.

Deterministic, offline release-risk observation adapted from
Shubhamsaboo/awesome-llm-apps at
804dee009f71503cd0bbb6d7338f2978790666ea (Apache-2.0).

Speider observes. This module never fetches, upgrades, remediates, clears or
executes. See RELEASE_RADAR_NOTICE.md.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from ..speider_connectors.observation_graph import ObservationGraph, Signal

MANIFEST_SCHEMA = "valo.speider.release_radar.manifest.v1"
REPORT_SCHEMA = "valo.speider.release_radar.report.v1"
SOURCE_SHA = "804dee009f71503cd0bbb6d7338f2978790666ea"

_ALLOWED_KINDS = {"dependency", "model", "provider"}
_ALLOWED_EXPOSURES = {"development": 0, "test": 5, "staging": 10, "production": 15}
_ALLOWED_CONSEQUENCES = {"low": 0, "moderate": 5, "high": 10, "critical": 15}
_ALLOWED_SUBJECT_KEYS = {
    "subject_id",
    "kind",
    "ecosystem",
    "current_version",
    "release_source",
    "manifest_path",
    "exposure",
    "consequence_class",
    "owner",
    "ignored_versions",
}
_ALLOWED_OBSERVATION_KEYS = {
    "subject_id",
    "release_version",
    "title",
    "notes",
    "release_url",
    "published_at",
    "observed_at",
    "source",
    "source_record_id",
    "draft",
    "prerelease",
}
_VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+){0,3})(?:[-+][0-9A-Za-z.-]+)?")

_SIGNAL_TERMS = {
    "security_fix": (
        "security fix",
        "security vulnerability",
        "vulnerability",
        "cve-",
        "security advisory",
        "remote code execution",
    ),
    "breaking_change": (
        "breaking change",
        "breaking:",
        "not backward compatible",
        "migration required",
        "removed support",
    ),
    "yanked_release": ("yanked", "withdrawn release", "do not use this release"),
    "deprecation": ("deprecated", "deprecation", "will be removed"),
}
_SIGNAL_ORDER = (
    "security_fix",
    "breaking_change",
    "yanked_release",
    "major_version",
    "deprecation",
)
_SIGNAL_BASE_SCORE = {
    "security_fix": 100,
    "breaking_change": 90,
    "yanked_release": 85,
    "major_version": 70,
    "deprecation": 60,
}
_SIGNAL_TIER = {
    "security_fix": 5,
    "breaking_change": 4,
    "yanked_release": 4,
    "major_version": 3,
    "deprecation": 2,
}
_REVIEW_ACTION = {
    "security_fix": "review_exposure_and_patch",
    "breaking_change": "assess_migration",
    "yanked_release": "verify_lock_and_avoid_release",
    "major_version": "plan_major_upgrade",
    "deprecation": "plan_deprecation_removal",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, field_name: str) -> Optional[str]:
    if value is None:
        return None
    return _require_text(value, field_name)


def _parse_iso(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ReleaseSubject:
    subject_id: str
    kind: str
    ecosystem: str
    current_version: Optional[str]
    release_source: str
    manifest_path: str
    exposure: str
    consequence_class: str
    owner: str
    ignored_versions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["ignored_versions"] = list(self.ignored_versions)
        return value


@dataclass(frozen=True)
class ReleaseObservation:
    subject_id: str
    release_version: str
    title: str
    notes: str
    release_url: str
    published_at: str
    observed_at: str
    source: str
    source_record_id: str
    draft: bool = False
    prerelease: bool = False

    def evidence_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def evidence_digest(self) -> str:
        return _digest(self.evidence_dict())


@dataclass(frozen=True)
class ReleaseFinding:
    subject_id: str
    kind: str
    ecosystem: str
    owner: str
    manifest_path: str
    release_source: str
    current_version: Optional[str]
    release_version: str
    version_delta: str
    title: str
    notes: str
    release_url: str
    published_at: str
    observed_at: str
    observation_source: str
    source_record_id: str
    reasons: tuple[str, ...]
    primary_reason: str
    priority_tier: int
    priority_score: int
    exposure: str
    consequence_class: str
    proposed_review_action: str
    observation_digest: str
    finding_digest: str
    observation_only: bool = True
    authority_granted: bool = False
    clearance_granted: bool = False
    execution_granted: bool = False
    remediation_permitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


@dataclass(frozen=True)
class IgnoredRelease:
    subject_id: str
    source_record_id: str
    reason: str
    observation_digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class UnknownRelease:
    subject_id: str
    source_record_id: str
    reason: str
    observation_digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ReleaseRadarReport:
    manifest_digest: str
    findings: tuple[ReleaseFinding, ...]
    ignored: tuple[IgnoredRelease, ...]
    unknown: tuple[UnknownRelease, ...]
    report_digest: str
    schema: str = REPORT_SCHEMA
    mode: str = "observation_only"
    offline: bool = True
    read_only: bool = True
    independent_verification: bool = False
    grants_clearance: bool = False
    grants_execution_authority: bool = False
    permits_remediation: bool = False

    def to_dict(self, *, include_report_digest: bool = True) -> dict[str, Any]:
        value = {
            "schema": self.schema,
            "mode": self.mode,
            "offline": self.offline,
            "read_only": self.read_only,
            "independent_verification": self.independent_verification,
            "grants_clearance": self.grants_clearance,
            "grants_execution_authority": self.grants_execution_authority,
            "permits_remediation": self.permits_remediation,
            "manifest_digest": self.manifest_digest,
            "findings": [finding.to_dict() for finding in self.findings],
            "ignored": [item.to_dict() for item in self.ignored],
            "unknown": [item.to_dict() for item in self.unknown],
        }
        if include_report_digest:
            value["report_digest"] = self.report_digest
        return value

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True)
class ReleaseManifest:
    subjects: tuple[ReleaseSubject, ...]
    schema: str = MANIFEST_SCHEMA
    manifest_digest: str = field(init=False)

    def __post_init__(self) -> None:
        body = {
            "schema": self.schema,
            "subjects": [subject.to_dict() for subject in self.subjects],
        }
        object.__setattr__(self, "manifest_digest", _digest(body))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "subjects": [subject.to_dict() for subject in self.subjects],
        }


def parse_manifest(document: Mapping[str, Any]) -> ReleaseManifest:
    if not isinstance(document, Mapping):
        raise ValueError("manifest must be a JSON object")
    unknown_top = set(document) - {"schema", "subjects"}
    if unknown_top:
        raise ValueError(f"unknown manifest fields: {sorted(unknown_top)}")
    if document.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"manifest schema must be {MANIFEST_SCHEMA}")
    raw_subjects = document.get("subjects")
    if not isinstance(raw_subjects, list) or not raw_subjects:
        raise ValueError("manifest subjects must be a non-empty list")

    subjects: list[ReleaseSubject] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_subjects):
        if not isinstance(raw, Mapping):
            raise ValueError(f"subjects[{index}] must be an object")
        unknown = set(raw) - _ALLOWED_SUBJECT_KEYS
        if unknown:
            raise ValueError(f"subjects[{index}] has unknown fields: {sorted(unknown)}")
        subject_id = _require_text(raw.get("subject_id"), f"subjects[{index}].subject_id")
        if subject_id in seen:
            raise ValueError(f"duplicate subject_id: {subject_id}")
        seen.add(subject_id)
        kind = _require_text(raw.get("kind"), f"subjects[{index}].kind")
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"unsupported kind: {kind}")
        exposure = _require_text(raw.get("exposure"), f"subjects[{index}].exposure")
        if exposure not in _ALLOWED_EXPOSURES:
            raise ValueError(f"unsupported exposure: {exposure}")
        consequence = _require_text(raw.get("consequence_class"), f"subjects[{index}].consequence_class")
        if consequence not in _ALLOWED_CONSEQUENCES:
            raise ValueError(f"unsupported consequence_class: {consequence}")
        ignored_raw = raw.get("ignored_versions", [])
        if not isinstance(ignored_raw, list) or any(
            not isinstance(item, str) or not item.strip() for item in ignored_raw
        ):
            raise ValueError(f"subjects[{index}].ignored_versions must be a list of strings")
        ignored = tuple(sorted({item.strip() for item in ignored_raw}))
        subjects.append(
            ReleaseSubject(
                subject_id=subject_id,
                kind=kind,
                ecosystem=_require_text(raw.get("ecosystem"), f"subjects[{index}].ecosystem"),
                current_version=_optional_text(raw.get("current_version"), f"subjects[{index}].current_version"),
                release_source=_require_text(raw.get("release_source"), f"subjects[{index}].release_source"),
                manifest_path=_require_text(raw.get("manifest_path"), f"subjects[{index}].manifest_path"),
                exposure=exposure,
                consequence_class=consequence,
                owner=_require_text(raw.get("owner"), f"subjects[{index}].owner"),
                ignored_versions=ignored,
            )
        )
    return ReleaseManifest(subjects=tuple(sorted(subjects, key=lambda item: item.subject_id)))


def load_manifest(path: Union[str, Path]) -> ReleaseManifest:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"release radar manifest not found: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid release radar manifest JSON: {exc}") from exc
    return parse_manifest(document)


def parse_observations(records: Iterable[Mapping[str, Any]]) -> tuple[ReleaseObservation, ...]:
    observations: list[ReleaseObservation] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise ValueError(f"observations[{index}] must be an object")
        unknown = set(raw) - _ALLOWED_OBSERVATION_KEYS
        if unknown:
            raise ValueError(f"observations[{index}] has unknown fields: {sorted(unknown)}")
        published = _require_text(raw.get("published_at"), f"observations[{index}].published_at")
        observed = _require_text(raw.get("observed_at", published), f"observations[{index}].observed_at")
        _parse_iso(published)
        _parse_iso(observed)
        notes = raw.get("notes", "")
        if not isinstance(notes, str):
            raise ValueError(f"observations[{index}].notes must be a string")
        draft = raw.get("draft", False)
        prerelease = raw.get("prerelease", False)
        if not isinstance(draft, bool) or not isinstance(prerelease, bool):
            raise ValueError(f"observations[{index}] draft and prerelease must be booleans")
        observation = ReleaseObservation(
            subject_id=_require_text(raw.get("subject_id"), f"observations[{index}].subject_id"),
            release_version=_require_text(raw.get("release_version"), f"observations[{index}].release_version"),
            title=_require_text(raw.get("title"), f"observations[{index}].title"),
            notes=notes,
            release_url=_require_text(raw.get("release_url"), f"observations[{index}].release_url"),
            published_at=published,
            observed_at=observed,
            source=_require_text(raw.get("source"), f"observations[{index}].source"),
            source_record_id=_require_text(raw.get("source_record_id"), f"observations[{index}].source_record_id"),
            draft=draft,
            prerelease=prerelease,
        )
        key = (observation.subject_id, observation.source, observation.source_record_id)
        if key in seen:
            raise ValueError(f"duplicate observation: {key}")
        seen.add(key)
        observations.append(observation)
    return tuple(
        sorted(
            observations,
            key=lambda item: (item.subject_id, item.published_at, item.source_record_id),
        )
    )


def _version_tuple(version: Optional[str]) -> Optional[tuple[int, int, int, int]]:
    if not version:
        return None
    match = _VERSION_RE.search(version)
    if not match:
        return None
    parts = [int(part) for part in match.group(1).split(".")[:4]]
    parts.extend([0] * (4 - len(parts)))
    return tuple(parts)  # type: ignore[return-value]


def version_delta(current: Optional[str], released: Optional[str]) -> str:
    current_tuple = _version_tuple(current)
    released_tuple = _version_tuple(released)
    if current_tuple is None or released_tuple is None:
        return "unknown"
    if released_tuple == current_tuple:
        return "same"
    if released_tuple < current_tuple:
        return "older"
    if released_tuple[0] != current_tuple[0]:
        return "major"
    if released_tuple[1] != current_tuple[1]:
        return "minor"
    if released_tuple[2] != current_tuple[2]:
        return "patch"
    return "revision"


def _reasons(observation: ReleaseObservation, delta: str) -> tuple[str, ...]:
    searchable = f"{observation.title}\n{observation.notes}".lower()
    found = {
        reason
        for reason, terms in _SIGNAL_TERMS.items()
        if any(term in searchable for term in terms)
    }
    if delta == "major":
        found.add("major_version")
    return tuple(reason for reason in _SIGNAL_ORDER if reason in found)


def _build_finding(
    subject: ReleaseSubject,
    observation: ReleaseObservation,
) -> Optional[ReleaseFinding]:
    delta = version_delta(subject.current_version, observation.release_version)
    if delta in {"same", "older"} or observation.release_version in subject.ignored_versions:
        return None
    reasons = _reasons(observation, delta)
    if not reasons:
        return None
    primary = reasons[0]
    score = (
        _SIGNAL_BASE_SCORE[primary]
        + _ALLOWED_EXPOSURES[subject.exposure]
        + _ALLOWED_CONSEQUENCES[subject.consequence_class]
        + max(0, len(reasons) - 1) * 3
    )
    body = {
        "subject": subject.to_dict(),
        "observation": observation.evidence_dict(),
        "version_delta": delta,
        "reasons": list(reasons),
        "primary_reason": primary,
        "priority_tier": _SIGNAL_TIER[primary],
        "priority_score": score,
        "proposed_review_action": _REVIEW_ACTION[primary],
        "observation_only": True,
        "authority_granted": False,
        "clearance_granted": False,
        "execution_granted": False,
        "remediation_permitted": False,
    }
    finding_digest = _digest(body)
    return ReleaseFinding(
        subject_id=subject.subject_id,
        kind=subject.kind,
        ecosystem=subject.ecosystem,
        owner=subject.owner,
        manifest_path=subject.manifest_path,
        release_source=subject.release_source,
        current_version=subject.current_version,
        release_version=observation.release_version,
        version_delta=delta,
        title=observation.title,
        notes=observation.notes,
        release_url=observation.release_url,
        published_at=observation.published_at,
        observed_at=observation.observed_at,
        observation_source=observation.source,
        source_record_id=observation.source_record_id,
        reasons=reasons,
        primary_reason=primary,
        priority_tier=_SIGNAL_TIER[primary],
        priority_score=score,
        exposure=subject.exposure,
        consequence_class=subject.consequence_class,
        proposed_review_action=_REVIEW_ACTION[primary],
        observation_digest=observation.evidence_digest,
        finding_digest=finding_digest,
    )


class ReleaseRadar:
    """Classify supplied release records and emit non-authoritative Speider evidence."""

    def analyze(
        self,
        manifest: ReleaseManifest,
        observations: Union[
            Sequence[ReleaseObservation],
            Iterable[Mapping[str, Any]],
        ],
    ) -> ReleaseRadarReport:
        if isinstance(observations, Sequence) and all(
            isinstance(item, ReleaseObservation) for item in observations
        ):
            parsed = tuple(observations)
            seen_observations: set[tuple[str, str, str]] = set()
            for observation in parsed:
                key = (
                    observation.subject_id,
                    observation.source,
                    observation.source_record_id,
                )
                if key in seen_observations:
                    raise ValueError(f"duplicate observation: {key}")
                seen_observations.add(key)
            parsed = tuple(
                sorted(
                    parsed,
                    key=lambda item: (
                        item.subject_id,
                        item.published_at,
                        item.source_record_id,
                    ),
                )
            )
        else:
            parsed = parse_observations(observations)  # type: ignore[arg-type]
        subjects = {subject.subject_id: subject for subject in manifest.subjects}
        findings: list[ReleaseFinding] = []
        ignored: list[IgnoredRelease] = []
        unknown: list[UnknownRelease] = []

        for observation in parsed:  # type: ignore[assignment]
            subject = subjects.get(observation.subject_id)
            if subject is None:
                unknown.append(
                    UnknownRelease(
                        subject_id=observation.subject_id,
                        source_record_id=observation.source_record_id,
                        reason="subject_not_in_manifest",
                        observation_digest=observation.evidence_digest,
                    )
                )
                continue
            if observation.draft:
                ignored.append(
                    IgnoredRelease(
                        observation.subject_id,
                        observation.source_record_id,
                        "draft",
                        observation.evidence_digest,
                    )
                )
                continue
            if observation.prerelease:
                ignored.append(
                    IgnoredRelease(
                        observation.subject_id,
                        observation.source_record_id,
                        "prerelease",
                        observation.evidence_digest,
                    )
                )
                continue
            delta = version_delta(subject.current_version, observation.release_version)
            if observation.release_version in subject.ignored_versions:
                ignored.append(
                    IgnoredRelease(
                        observation.subject_id,
                        observation.source_record_id,
                        "manifest_ignored_version",
                        observation.evidence_digest,
                    )
                )
                continue
            if delta in {"same", "older"}:
                ignored.append(
                    IgnoredRelease(
                        observation.subject_id,
                        observation.source_record_id,
                        delta,
                        observation.evidence_digest,
                    )
                )
                continue
            finding = _build_finding(subject, observation)
            if finding is None:
                ignored.append(
                    IgnoredRelease(
                        observation.subject_id,
                        observation.source_record_id,
                        "routine_release",
                        observation.evidence_digest,
                    )
                )
                continue
            findings.append(finding)

        findings.sort(
            key=lambda item: (
                -item.priority_tier,
                -item.priority_score,
                item.subject_id,
                -_parse_iso(item.published_at).timestamp(),
                item.release_version,
                item.source_record_id,
            )
        )
        ignored.sort(key=lambda item: (item.subject_id, item.reason, item.source_record_id))
        unknown.sort(key=lambda item: (item.subject_id, item.source_record_id))

        body = {
            "schema": REPORT_SCHEMA,
            "mode": "observation_only",
            "offline": True,
            "read_only": True,
            "independent_verification": False,
            "grants_clearance": False,
            "grants_execution_authority": False,
            "permits_remediation": False,
            "manifest_digest": manifest.manifest_digest,
            "findings": [item.to_dict() for item in findings],
            "ignored": [item.to_dict() for item in ignored],
            "unknown": [item.to_dict() for item in unknown],
        }
        return ReleaseRadarReport(
            manifest_digest=manifest.manifest_digest,
            findings=tuple(findings),
            ignored=tuple(ignored),
            unknown=tuple(unknown),
            report_digest=_digest(body),
        )

    def emit_signals(
        self,
        graph: ObservationGraph,
        report: ReleaseRadarReport,
    ) -> tuple[str, ...]:
        signal_ids: list[str] = []
        for finding in report.findings:
            timestamp = _parse_iso(finding.observed_at).replace(tzinfo=None)
            signal = Signal(
                signal_id=f"SIG-RELEASE-{finding.finding_digest[:20].upper()}",
                signal_type="release_risk_observation",
                entity_id=finding.subject_id,
                source=f"Speider Release Radar/{finding.observation_source}",
                value=finding.to_dict(),
                confidence=0.80,
                timestamp=timestamp,
                metadata={
                    "schema": REPORT_SCHEMA,
                    "manifest_digest": report.manifest_digest,
                    "report_digest": report.report_digest,
                    "finding_digest": finding.finding_digest,
                    "confidence_basis": (
                        "record completeness and deterministic classification only"
                    ),
                    "observation_only": True,
                    "independent_verification": False,
                    "authority_granted": False,
                    "clearance_granted": False,
                    "execution_granted": False,
                    "remediation_permitted": False,
                    "proposed_review_action": finding.proposed_review_action,
                },
            )
            signal_ids.append(graph.add_signal(signal))
        return tuple(signal_ids)
