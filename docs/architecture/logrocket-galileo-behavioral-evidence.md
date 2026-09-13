# LogRocket Galileo as a Behavioral Evidence Sensor

LogRocket Galileo is integrated as a replaceable behavioral sensor over the shared `lib.behavioral_evidence_loop` contract.

It does not define its own evidence, candidate, authorization or outcome types.

## Flow

```text
LogRocket Galileo Funnel Insight
  -> EvidenceRefV1
  -> BehavioralObservationV1
  -> BehaviorFindingV1
  -> ImprovementCandidateV1
  -> Factory evaluation
  -> reht authorization for the exact action digest
  -> external execution
  -> ExecutionReceiptV1 + Veritas receipt
  -> post-deploy behavioral evidence
  -> OutcomeEvidenceV1
```

## What Galileo contributes

The adapter accepts:

- a Galileo insight id;
- supporting session references;
- a digest of the source payload;
- observed and captured timestamps;
- tenant/scope/privacy/rights metadata through `PrivacyEnvelopeV1`;
- provenance;
- optional funnel and step references.

The resulting observation uses the fixed source type `logrocket_galileo`.

Galileo's generated explanation is represented as `ClaimKind.MODEL_EXPLANATION`, not as an observed fact. The underlying evidence reference remains attached.

## Authority boundary

The adapter may request only:

- `ANALYZE`
- `PROPOSE_BUILD_ORDER`

It may not request:

- `MERGE`
- `DEPLOY`
- `MUTATE_PRODUCTION`
- model training or model promotion

An externally constructed consequential candidate still resolves through the shared `authority_boundary()` to `REHT_REQUIRED`.

The adapter never turns Galileo confidence, session evidence or a generated hypothesis into authority.

## Outcome boundary

A post-deploy Galileo observation is not enough to claim success by itself.

`build_outcome_evidence()` requires:

- the exact `ImprovementCandidateV1`;
- a matching `AuthorizationBindingV1` from reht;
- the matching `ExecutionReceiptV1` with a Veritas reference;
- pre- and post-evidence references;
- an explicit comparison method and time window;
- baseline and observed metric values when claiming a verified result;
- causal caveats when relevant.

The shared loop verifies that candidate, action digest, authorization and receipt all match.

Missing pre/post evidence produces `INSUFFICIENT_EVIDENCE`, never a success claim.

## Privacy and sovereignty

Raw session payloads are not copied into the shared contract. The adapter binds source references and payload digests.

Tenant, scope, collection purpose, retention, residency, rights basis and redaction state are carried through `PrivacyEnvelopeV1`.

Behavioral data does not become training data automatically. Any later model-training use remains subject to the shared dataset-admission boundary.

## Relationship to other adapters

Sentry contributes incident, trace and repair evidence. Galileo contributes product/session behavior evidence. PostHog, Fullstory and Human Behavior can be added through the same sensor contract when required.

None of these providers owns the execution boundary or outcome truth.
