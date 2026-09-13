from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vaig_filter import evaluate_case


def load_case(name: str):
    return json.loads((ROOT / "cases" / name).read_text(encoding="utf-8"))


def test_anchorage_steps_up():
    result = evaluate_case(load_case("anchorage.json"))
    assert result.decision == "STEP_UP"
    assert result.mode == "SAFE_MODE"
    assert result.autonomous_recommendation_allowed is False
    assert result.primary_failure == "predictive incoherence"


def test_chemical_plant_steps_up():
    result = evaluate_case(load_case("chemical_plant.json"))
    assert result.decision == "STEP_UP"
    assert result.mode == "SAFE_MODE"
    assert result.autonomous_recommendation_allowed is False
    assert result.primary_failure == "causal incoherence"


def test_validated_low_risk_allows_normal_generation():
    case = {
        "case_name": "Low Risk Validated Case",
        "domain": "generic",
        "consequence_severity": "low",
        "evidence_condition": "validated",
        "human_authority_required": False,
    }
    result = evaluate_case(case)
    assert result.decision == "ALLOW"
    assert result.mode == "NORMAL"
    assert result.autonomous_recommendation_allowed is True
