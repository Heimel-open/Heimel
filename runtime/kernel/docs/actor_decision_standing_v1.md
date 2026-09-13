# Actor Decision Standing v1

VALO must treat identity, role, represented principal, authority principal, credentials, calibrated competence, authority and decision function as separate governed concepts.

Canonical separation:

```text
Identity != Role != RepresentedPrincipal/Whose != AuthorityPrincipal
         != Credential != CalibratedCompetence != Authority
         != DecisionFunction != Approval != Consent != RiskAcceptance
```

No element silently creates another.

## Canonical chain

```text
identity
-> active role / capacity
-> represented principal / whose
-> decision function
-> calibrated competence
-> attention state when required
-> eligibility / independence
-> authority holder + authority origination + bounded delegation
-> approval / quorum / consent when required
-> risk acceptance when required
-> purpose + jurisdiction
-> exact action
-> ActorDecisionStanding
-> PrincipalAuthoritySemantics v2
-> fresh REHT authorization
```

`ActorDecisionStanding` creates no authority and cannot issue clearance.

## Whose is not the authority holder

`ActiveRoleBinding.principal_id` means the represented principal: whose behalf, interest or organizational capacity the actor is acting for.

Existing `Authority.principal` retains its existing meaning as the holder from which the authority chain originates. These values can be different. For example:

```text
actor                  = person:ceo
role                   = role:ceo
represented principal  = company:acme
authority principal    = office:ceo:acme
```

The CEO can therefore act for the company while exercising authority held by the CEO office. VALO must bind both and must never infer that they are the same entity merely because they often coincide in simpler cases.

## Active role

A role is temporal state, not a title. The same identity can act as CEO, board member, investor or private person without changing identity. `ActiveRoleBinding` binds actor, role, represented principal, decision functions, capability/resource scope, jurisdiction, basis, evidence, validity and revocation.

## Decision function

These functions are distinct:

```text
ASSESS
RECOMMEND
APPROVE
AUTHORIZE
EXECUTE
VERIFY
ACCEPT_RISK
```

A CEO can have mandate to APPROVE or ACCEPT_RISK without being competent to ASSESS cybersecurity risk. A CISO can assess without thereby acquiring CEO approval authority.

## Calibrated Competence

A credential is evidence, not current competence. A PhD, certification or prior title may support calibration but cannot directly establish current competence for a specific function.

`CalibratedCompetence` is bound to actor, role, decision function, capability, domain, system/context, risk, evidence and time. Dispositions are `CALIBRATED`, `CONDITIONAL`, `STEP_UP_REQUIRED`, `NOT_CALIBRATED` and `UNKNOWN`.

Competence freshness is independent of credential validity and authority freshness.

## Right attention

Human presence is not sufficient evidence of meaningful oversight. Where policy requires attention, VALO uses a short-lived `AttentionState` with evidence: `READY`, `DEGRADED`, `UNAVAILABLE`, `UNKNOWN`.

This connects directly to ACEI/ACEG:

```text
Right actor x Right role x Right represented principal x Right time
x Right attention x Right calibrated competence
```

## Eligibility and independence

Correct identity, role, competence and authority are still insufficient when the actor is conflicted, recused or disqualified. `EligibilityState` is separately bound to actor, role, represented principal and jurisdiction.

## Consent, approvals and risk acceptance

Consent, approval, quorum and risk acceptance are prerequisites, not authority substitutes. Approval does not create competence. Risk acceptance is a different function from risk assessment. Distinct approvers and anti-self-approval are explicit requirements when configured.

## Authority origination and delegation depth

The existing `Authority` and `Delegation` v1 contracts remain byte/wire compatible. Grantor standing and delegation-depth semantics are added through the separate versioned `AuthorityOriginationState` contract rather than by changing existing authority payloads.

`AuthorityOriginationState` binds the exact authority ID, authority principal, represented principal, grantor, grantor standing, evidence, validity, revocation-registry reference and maximum delegation depth. Missing origination data cannot produce PASS on the standing-bound path.

`PrincipalAuthoritySemanticsV2` requires the exact origination state used by `ActorDecisionStanding` and rejects a delegation chain that exceeds its maximum depth or breaks actor continuity.

## Authority conflict and jurisdiction

`AuthorityConflictAssessment` makes conflict state explicit as `CLEAR`, `CONFLICTED` or `UNKNOWN`; only CLEAR supports PASS. It is bound to the authority principal, capability and target. Jurisdiction is bound into role and eligibility rather than left as display metadata.

## Exact-action and freshness binding

Actor standing is sealed to the exact ProposedAction digest and relevant role, competence, attention, eligibility, authority origination, consent, approval, risk and conflict evidence. Its validity ends at the shortest-lived dependency.

`PrincipalAuthoritySemanticsV2` then binds that standing to executor, represented principal, authority principal, authority origination, delegation, purpose, exact action and fresh authority-state reference.

## Recursive consequence standing

Actor standing must not stop at the final executor. Any consequence-bearing assessment, recommendation, approval, authority grant, risk acceptance or verification introduced by another actor must carry that contributor's own fresh PASS standing for the exact action and decision function.

The companion `DecisionContributionChain` in `docs/consequence_governance_emergency_v1.md` makes this explicit and prevents invalid upstream decisions from being laundered into an otherwise valid downstream execution path.

## State-source boundary

Role, competence, attention, eligibility, origination and conflict objects are not made true merely by constructing these contracts. Their evidence and current standing must come from admitted/current governed state or an equivalent authoritative state-resolution path.

This contract closes the consequence-boundary composition problem. It does not create a second state owner or allow caller-supplied objects to bypass Kernel admission and freshness semantics.

## Compatibility

PrincipalAuthoritySemantics v1 remains for compatibility. New consequence-bearing integrations should use v2. V1 must not be interpreted as proof that role, represented-principal binding, calibrated competence, attention, eligibility, authority origination or authority-conflict checks occurred.

## Swarm finding

Most ingredients already existed in separate VALO layers: Kernel identity/authority/purpose, RACS role integrity and authority grants, Mandate OS delegation/risk ownership, MAL and Human Approval Workbench quorum controls, Public Pack legal competence/conflict checks, consent layers, and state-resolution freshness.

The missing piece was canonical composition at the consequence boundary. Actor Decision Standing v1 consolidates those concepts without allowing role, credentials, competence, consent, approval or risk state to become authority.
