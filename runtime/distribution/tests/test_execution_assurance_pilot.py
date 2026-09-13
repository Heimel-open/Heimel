#!/usr/bin/env python3
import copy
import json
import os
import subprocess
import sys
import tempfile

import jsonschema
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.join(ROOT, "pilots", "execution-assurance-v1", "pilot.yaml")
SCHEMA = os.path.join(ROOT, "schemas", "execution-assurance-pilot-v1.schema.json")
VALIDATOR = os.path.join(ROOT, "scripts", "validate-execution-assurance-pilot")


def load():
    return yaml.safe_load(open(PILOT, encoding="utf-8"))


def run_validator(path, *extra):
    return subprocess.run(
        [sys.executable, VALIDATOR, "--pilot", path, *extra],
        capture_output=True,
        text=True,
    )


def temp_yaml(payload):
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    yaml.safe_dump(payload, handle, sort_keys=False)
    handle.close()
    return handle.name


def test_schema():
    pilot = load()
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    jsonschema.validate(pilot, schema)
    print("TEST execution_assurance_schema: PASS")


def test_candidate_validates():
    result = run_validator(PILOT)
    assert result.returncode == 0, result.stderr
    assert "CANDIDATE_VALID" in result.stdout
    print("TEST execution_assurance_candidate: PASS")


def test_generic_template_is_not_deployable_without_pins():
    result = run_validator(PILOT, "--deployable")
    assert result.returncode != 0
    assert "immutable artifact_ref" in result.stderr
    print("TEST execution_assurance_unpinned_not_deployable: PASS")


def test_exact_pins_make_package_deployable():
    pilot = load()
    for index, component in enumerate(pilot["runtime_components"]):
        component["artifact_ref"] = f"{component['canonical_repo']}@{index + 1:040x}"
    path = temp_yaml(pilot)
    try:
        result = run_validator(path, "--deployable")
        assert result.returncode == 0, result.stderr
        assert "DEPLOYABLE" in result.stdout
    finally:
        os.unlink(path)
    print("TEST execution_assurance_pinned_deployable: PASS")


def test_shadow_cannot_become_authoritative_by_configuration():
    pilot = load()
    pilot["deployment"]["shadow_invariants"]["can_issue_clearance"] = True
    path = temp_yaml(pilot)
    try:
        result = run_validator(path)
        assert result.returncode != 0
    finally:
        os.unlink(path)
    print("TEST execution_assurance_shadow_no_clearance: PASS")


def test_canonical_runtime_ownership_cannot_be_redirected():
    pilot = load()
    for component in pilot["runtime_components"]:
        if component["component"] == "reht":
            component["canonical_repo"] = "nsolland/valo-distribution"
    path = temp_yaml(pilot)
    try:
        result = run_validator(path)
        assert result.returncode != 0
        assert "canonical_repo must be nsolland/valo-reht" in result.stderr
    finally:
        os.unlink(path)
    print("TEST execution_assurance_canonical_owner: PASS")


def test_auto_promotion_is_forbidden():
    pilot = load()
    pilot["deployment"]["enforce_gate"]["automatic_promotion"] = True
    path = temp_yaml(pilot)
    try:
        result = run_validator(path)
        assert result.returncode != 0
    finally:
        os.unlink(path)
    print("TEST execution_assurance_no_auto_promotion: PASS")


def test_product_state_boundaries_are_fixed():
    pilot = load()
    pilot["commercial_boundaries"]["reht_is_product"] = True
    path = temp_yaml(pilot)
    try:
        result = run_validator(path)
        assert result.returncode != 0
    finally:
        os.unlink(path)
    print("TEST execution_assurance_product_boundary: PASS")


if __name__ == "__main__":
    test_schema()
    test_candidate_validates()
    test_generic_template_is_not_deployable_without_pins()
    test_exact_pins_make_package_deployable()
    test_shadow_cannot_become_authoritative_by_configuration()
    test_canonical_runtime_ownership_cannot_be_redirected()
    test_auto_promotion_is_forbidden()
    test_product_state_boundaries_are_fixed()
    print("ALL_EXECUTION_ASSURANCE_PILOT_TESTS_PASS")
