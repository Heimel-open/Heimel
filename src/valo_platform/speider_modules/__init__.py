"""Speider Intelligence Modules.

Specialized observation and analysis modules built on SpeiderScanner.
Each module composes signals from multiple sources to answer domain questions.
"""

from .grant_speider import GrantSpeider, GrantOpportunity, GrantIntelligence
from .release_radar import (
    MANIFEST_SCHEMA as RELEASE_RADAR_MANIFEST_SCHEMA,
    REPORT_SCHEMA as RELEASE_RADAR_REPORT_SCHEMA,
    IgnoredRelease,
    ReleaseFinding,
    ReleaseManifest,
    ReleaseObservation,
    ReleaseRadar,
    ReleaseRadarReport,
    ReleaseSubject,
    UnknownRelease,
    load_manifest as load_release_manifest,
    parse_manifest as parse_release_manifest,
    parse_observations as parse_release_observations,
    version_delta as release_version_delta,
)

__all__ = [
    "GrantSpeider",
    "GrantOpportunity",
    "GrantIntelligence",
    "RELEASE_RADAR_MANIFEST_SCHEMA",
    "RELEASE_RADAR_REPORT_SCHEMA",
    "IgnoredRelease",
    "ReleaseFinding",
    "ReleaseManifest",
    "ReleaseObservation",
    "ReleaseRadar",
    "ReleaseRadarReport",
    "ReleaseSubject",
    "UnknownRelease",
    "load_release_manifest",
    "parse_release_manifest",
    "parse_release_observations",
    "release_version_delta",
]
