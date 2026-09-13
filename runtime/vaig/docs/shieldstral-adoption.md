# Shieldstral Pattern Adoption

Status: implemented
Source signal: Shieldstral, policy-adaptive multimodal safety classification
Source: https://arxiv.org/abs/2607.25857

## What VAIG adopts

VAIG adopts a provider-neutral policy-safety measurement slot. A specialized classifier may evaluate text, images or other upstream representations against a bound policy and return an unsafe probability.

Shieldstral is one possible provider. It is not a required dependency and does not become a VALO authority layer.

## Contract

`policy_safety_classifier` consumes four explicit native inputs:

- `unsafe_probability` in `[0, 1]`;
- `classifier_id` identifying the exact classifier implementation/model;
- `policy_id` identifying the policy used for classification;
- `observation_digest` binding the external observation to evidence.

The slot produces one VAIG risk measurement. It has no positive-clearance or execution API.

## Fail-closed semantics

A missing classifier result, policy binding, classifier identity or observation digest is not safety evidence. When the slot is required, missing inputs remain `UNAVAILABLE` and the Ensemble halts/abstains rather than converting unknown state to risk `0.0`.

Malformed or out-of-range classifier output becomes an instrument error and also fails closed.

## Boundary

Classifier output may contribute to distrust, veto or aggregation according to VAIG policy. It never grants authority, issues REHT clearance, creates an execution permit or enforces an action.

The canonical path remains:

`classifier observation -> VAIG measurement -> REHT authorization decision -> gateway enforcement -> Veritas evidence`

## Conformance

`tests/test_policy_safety_classifier.py` proves registration, bounded scoring, required policy/classifier/evidence bindings, Ensemble integration and fail-closed behavior when a measurement is missing.
