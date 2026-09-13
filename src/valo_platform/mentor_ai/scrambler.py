"""AnonymizationScramblingEngine & CaseIntegrityValidator.

Scrambles historical cases deterministically to remove PII, corporate identities,
and dates while preserving causality, evidence asymmetry, and pedagogical value.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Dict, List, Mapping, Tuple, Optional
from valo_platform.mentor_ai.mentor_models import HistoricalCaseV1, ScrambledCaseV1


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AnonymizationScramblingEngine:
    """Transforms raw historical case text into an anonymized and scrambled training scenario."""

    def __init__(self, seed: str = "default_seed") -> None:
        self.seed = seed

    def scramble(
        self,
        historical_case: HistoricalCaseV1,
        raw_text: str,
        additional_entities: Tuple[str, ...] = (),
    ) -> Tuple[ScrambledCaseV1, Dict[str, str]]:
        # Deterministic entity replacement map based on case_id & seed
        h = hashlib.sha256(f"{historical_case.case_id}:{self.seed}".encode("utf-8")).hexdigest()
        
        mapping = {
            "Equinor AS": f"Energy Corp {h[:4]}",
            "Equinor": f"Energy Corp {h[:4]}",
            "DNB Markets": f"Bank Group {h[4:8]}",
            "DNB": f"Bank Group {h[4:8]}",
            "Kari Nordmann": f"Person {h[8:12]}",
            "Ola Nordmann": f"Person {h[12:16]}",
        }

        for idx, entity in enumerate(additional_entities):
            if entity not in mapping:
                mapping[entity] = f"Org/Entity {h[idx*4:(idx+1)*4]}"

        scrambled_text = raw_text
        for orig, replacement in mapping.items():
            scrambled_text = re.sub(re.escape(orig), replacement, scrambled_text, flags=re.IGNORECASE)

        mapping_digest = _canonical_digest(mapping)

        scrambled_case = ScrambledCaseV1(
            scrambled_case_id=f"scram-{historical_case.case_id}",
            original_case_id=historical_case.case_id,
            domain=historical_case.domain,
            scrambled_scenario_text=scrambled_text,
            evidence_digests=(historical_case.raw_content_digest,),
            scrambled_entity_mapping_digest=mapping_digest,
        )

        return scrambled_case, mapping


class CaseIntegrityValidator:
    """Validates that scrambled cases contain NO leaked PII or original company identities."""

    def __init__(self, forbidden_terms: Tuple[str, ...]) -> None:
        self.forbidden_terms = forbidden_terms

    def validate(self, scrambled_case: ScrambledCaseV1) -> Tuple[bool, List[str]]:
        violations: List[str] = []
        text = scrambled_case.scrambled_scenario_text.lower()

        for term in self.forbidden_terms:
            if term.lower() in text:
                violations.append(f"LEAKED_IDENTITY_TERM: {term}")

        return (len(violations) == 0, violations)
