# PEACE Person-Model Sovereignty Profile v0

Status: draft normative profile for PEACE v0.

This profile defines observable governance semantics for models inferred about a human or protected actor. It deliberately does not standardize inference methods, embeddings, latent-state representations, mesh topology or model internals.

Normative words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are requirements of this profile.

## 1. Scope

A `person_model` is any subject-linked representation materially used to predict, simulate, classify, rank, personalize or optimize decisions about a person, including inferred cognitive signatures, behavioural models, preference models, persistent embeddings, response predictors and functional digital twins.

A generic population model is outside this profile until it is bound to, adapted to or used as a materially person-specific representation.

## 2. Constitutional invariants

A conformant implementation MUST preserve these semantics:

1. **DERIVATION_NE_AUTHORITY** — technical ability to infer a person_model MUST NOT create authority to retain, share, sell, activate or use it.
2. **INFERRED_PREFERENCE_NE_CONSENT** — a predicted preference, intention, likely response or simulated choice MUST NOT be treated as consent, delegation or authority from the person.
3. **PERSON_MODEL_IS_SUBJECT_LINKED_GOVERNED_STATE** — a person_model and materially equivalent descendants MUST remain attributable to the protected subject and governed by purpose, scope, retention, disclosure and use constraints.
4. **MODEL_USE_REQUIRES_CURRENT_AUTHORITY** — consequential use of a person_model MUST be authorized for the exact purpose and use class against current relevant authority before use.
5. **REVOCATION_PROPAGATES_TO_USE** — revocation or expiry of authority MUST prevent further governed use and MUST propagate to materially equivalent descendants and replicas within the governed domain.
6. **NO_UNDECLARED_INFLUENCE_OPTIMIZATION** — a person_model MUST NOT be used to select or sequence information, arguments, timing, channels or context for the purpose of changing that person's judgement or behaviour unless that exact influence purpose is explicitly authorized and permitted by governing policy.
7. **POLITICAL_COGNITIVE_TARGETING_PROHIBITED** — a conformant human-sovereignty profile MUST NOT use a person_model to optimize individualized political persuasion, political demobilization, political trust manipulation or voting behaviour.
8. **DISCLOSURE_RESTRICTIONS_FOLLOW_DERIVATIVES** — sharing a derived representation MUST NOT strip the subject-linked restrictions attached to its source lineage.
9. **MODEL_NE_PERSON** — a person_model is a representation of a subject, not the subject, and MUST NOT become an authority root, substitute principal or source of delegation merely because it predicts the subject accurately.
10. **CAPABILITY_NE_ENTITLEMENT** — higher predictive accuracy or greater model capability MUST NOT widen the permitted purposes or authority associated with the person_model.

## 3. Required person-model manifest

Where a person_model is retained or made operational, the governed system MUST be able to express a manifest equivalent to:

- subject / protected actor reference;
- model or representation reference;
- derivation provenance sufficient to identify the governed source lineage without requiring disclosure of proprietary implementation internals;
- declared purpose and permitted use classes;
- prohibited use classes;
- authorized recipients / domains;
- retention or validity conditions;
- current authority / consent / legal-basis reference where applicable;
- revocation state;
- descendant / replica lineage sufficient to enforce inherited restrictions.

The manifest MAY reference opaque commitments or digests instead of exposing proprietary model weights, embeddings or internal topology.

## 4. Use classes

Implementations MAY define finer-grained classes, but MUST distinguish at least:

- `assist_subject` — use primarily for the subject's requested benefit;
- `predict_subject` — prediction or simulation about the subject;
- `personalize_content` — content/ranking adaptation to the subject;
- `influence_subject` — optimization intended to alter judgement or behaviour;
- `political_influence` — individualized political persuasion or demobilization;
- `share_person_model` — disclosure or transfer of the model or materially equivalent representation.

Authority for one class MUST NOT imply authority for another.

## 5. Human-AI boundary

An agent MAY infer candidate preferences or predictions to perform permitted work, but those inferences remain candidate material.

A statement equivalent to `the model predicts the person would approve` MUST NOT satisfy a consent, delegation, authorization or standing requirement.

Where the exact use requires the person's current authority, the system MUST obtain or verify that authority independently of the person_model being governed.

## 6. Revocation and deletion semantics

Where policy or law requires deletion, deletion SHOULD remove or render unusable retained person-specific artifacts and governed descendants to the extent technically possible.

Irrespective of physical deletion feasibility, revoked material MUST become non-operative for governed use. A provider MUST NOT claim continued authority merely because technical copies, weights, logs or replicas remain.

## 7. Evidence

Governed use of a person_model SHOULD produce evidence sufficient to identify:

- the person_model manifest/reference used;
- the declared use class and purpose;
- the current authority/policy decision;
- destination or acting capability;
- outcome or effect class;
- relevant descendant/replica lineage when restrictions propagate.

Evidence of inference quality does not create authority.

## 8. Relationship to PEACE core

This profile extends PEACE v0 without changing the core rule that capability, inference and evidence do not create authority.

A person_model is governed subject-linked state for the purposes of disclosure, routing, authorization, replication and recovery. Internal inference algorithms and mesh implementation remain outside the public protocol surface.
