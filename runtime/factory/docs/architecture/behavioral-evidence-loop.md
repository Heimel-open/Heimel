# Behavioral Evidence Loop

## Why this exists

Human Behavior, PostHog Replay Vision, Fullstory StoryAI, LogRocket Galileo and Sentry Seer show the same market direction:

```text
observe production behavior
  -> find friction, defects or anomalies
  -> generate an explanation or repair candidate
  -> hand work to a coding agent
  -> create a pull request
  -> observe production again
```

VALO already had strong Factory gates and provider-specific adapters. The missing shared core was the binding between:

1. provider-neutral evidence;
2. an exact proposed action;
3. commit-time authorization for that exact action;
4. an execution receipt;
5. post-execution outcome evidence;
6. controlled learning.

Without that binding, a product can show a persuasive closed loop while still confusing observation, explanation, permission, execution and outcome.

## Delivered contract

`lib/behavioral_evidence_loop.py` adds a provider-neutral contract for:

- `PrivacyEnvelopeV1`
- `EvidenceRefV1`
- `BehavioralObservationV1`
- `BehaviorTraceV1`
- `BehaviorFindingV1`
- `ImprovementCandidateV1`
- `AuthorizationBindingV1`
- `ExecutionReceiptV1`
- `OutcomeEvidenceV1`
- `LearningProposalV1`

## Canonical flow

```text
Human Behavior / PostHog / Fullstory / LogRocket / Sentry / OTel / workflow / edge
  -> EvidenceRefV1
  -> BehavioralObservationV1
  -> BehaviorTraceV1
  -> BehaviorFindingV1
  -> ImprovementCandidateV1
  -> Factory evaluation
  -> AuthorizationBindingV1 from reht for the exact action digest
  -> external execution
  -> ExecutionReceiptV1 + Veritas reference
  -> OutcomeEvidenceV1
  -> optional LearningProposalV1
```

No behavioral source becomes an authority source.

## Enforced invariants

### Evidence and privacy

- Evidence carries tenant, scope, purpose, retention, residency, rights basis and redaction state.
- One observation cannot mix tenants or scopes.
- The contract stores payload references and SHA-256 digests, not raw session payloads.
- Live, shadow and replay observations remain explicit.
- Complete traces cannot hide unresolved gaps.
- Findings must resolve to source evidence or traces.
- Model explanations remain a distinct claim type rather than observed fact.

### Authority

- Sensor adapters can analyze, propose build orders, propose datasets and open PRs.
- Sensor adapters cannot merge, deploy, mutate production, train models or promote models.
- Consequential candidates resolve to `REHT_REQUIRED`.
- Authorization binds the exact `candidate_id`, action payload digest, principal, mandate, decision and authorized state.
- Expired or not-yet-active authorization fails closed.
- A different payload cannot reuse an earlier authorization.

### Execution and outcome

- Execution must bind the exact authorization and action digest.
- A Veritas receipt reference is mandatory.
- Outcome evidence must bind the same candidate, authorization, receipt and action digest.
- Expected and observed outcomes are separate fields.
- Verified outcomes require pre- and post-evidence plus comparable metric values.
- Missing evidence produces `INSUFFICIENT_EVIDENCE`, never success.
- Causal caveats remain explicit.

### Learning

- Insufficient outcomes cannot enter learning.
- Learning proposals have `authority_effect = none`.
- Model training requires explicit dataset admission.
- Observed customer behavior is not automatically reusable training data.

## Integration with existing work

The existing Sentry adapter remains an incident and repair sensor. The open LogRocket Galileo adapter remains a funnel and session-behavior sensor. Both should normalize into this shared contract rather than own separate definitions of evidence, candidates and outcomes.

The existing `factory_evidence_loop.py` continues to govern Factory work items, independent testing, review, merge candidates and landing. This module does not replace it. It closes the external observation-to-authorized-execution-to-outcome seam around it.

The platform build order in `valo-platform#1737` remains the broader architecture statement. This implementation is the first concrete Factory slice.

## Not copied from the market

VALO does not copy provider-specific session replay storage, proprietary agent runtimes or a model-dependent diagnosis layer.

Providers remain replaceable sensors and repair workers. The durable VALO layer is:

```text
evidence grammar
  + exact authority binding
  + execution receipts
  + outcome verification
  + sovereign privacy and admission controls
```

## Next adapter work

After this core merges:

1. rebase the LogRocket Galileo adapter onto the shared contract;
2. map Sentry incident, trace and post-deploy evidence into the same types;
3. add PostHog, Fullstory and Human Behavior adapters only when a real customer/source integration requires them.

Provider count is not the acceptance gate. The acceptance gate is that no provider can turn its own interpretation into authority or claim success without receipt-bound outcome evidence.
