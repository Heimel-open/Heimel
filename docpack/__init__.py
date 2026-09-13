"""docpack: canonical document packages for Tofoo reasoning (#77).

Strict separation between source, extraction, interpretation and
conclusion, with versioned frozen contracts and deterministic digests.
"""

from .digest import canonical_digest, digest_of_bytes
from .mineru import (
    build_package_from_mineru,
    mineru_block_to_observation,
    mineru_pages_to_observations,
)
from .models import (
    STAGE_ORDER,
    ChainRecord,
    CanonicalDocumentPackage,
    Contract,
    ExtractedObservation,
    ExtractionProvenance,
    InterpretationCandidate,
    ParseConfidenceEvidence,
    ReasoningStage,
    ReasoningStatement,
    SourceConflict,
    SourceIdentity,
    SourceLocationRef,
    UnresolvedDocumentQuestion,
)
from .pipeline import DocumentPipeline

__all__ = [
    "STAGE_ORDER",
    "CanonicalDocumentPackage",
    "ChainRecord",
    "Contract",
    "DocumentPipeline",
    "ExtractedObservation",
    "ExtractionProvenance",
    "InterpretationCandidate",
    "ParseConfidenceEvidence",
    "ReasoningStage",
    "ReasoningStatement",
    "SourceConflict",
    "SourceIdentity",
    "SourceLocationRef",
    "UnresolvedDocumentQuestion",
    "build_package_from_mineru",
    "canonical_digest",
    "digest_of_bytes",
    "mineru_block_to_observation",
    "mineru_pages_to_observations",
]
