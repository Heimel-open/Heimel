# Work anchor — Actor Decision Standing v1

- Repo: `nsolland/valo-kernel`
- Canonical base SHA: `1d9947520c8df9edeb22e62244fa252a576f8f9b`
- Branch: `feat/actor-standing-calibrated-competence-v1`
- Draft PR: `#50`
- Owner: ChatGPT for Njål Gaute Solland
- Scope: close the actor/role/whose/competence/attention/decision-function gaps found in the 2026-08-18 swarm review and the follow-on recursive-standing, consequence, omission and emergency-mandate gaps without weakening existing authority or REHT boundaries.

Owned files:

- `src/valo_kernel/contracts/actor_standing.py`
- `src/valo_kernel/actor_standing.py`
- `src/valo_kernel/authority_projection_v2.py`
- `src/valo_kernel/contracts/consequence_governance.py`
- `src/valo_kernel/consequence_governance.py`
- `tests/test_actor_standing.py`
- `tests/test_consequence_governance.py`
- `docs/actor_decision_standing_v1.md`
- `docs/consequence_governance_emergency_v1.md`
- `docs/work-anchors/2026-08-18-actor-decision-standing-v1.md`

Canonical distinctions:

```text
Identity != Role != RepresentedPrincipal/Whose != AuthorityPrincipal
         != Credential != CalibratedCompetence != Authority
         != DecisionFunction != Approval != Consent != RiskAcceptance
```

`ActiveRoleBinding.principal_id` means the represented principal / whose behalf the actor is acting on. Existing `Authority.principal` remains the holder from which the authority chain originates. They are deliberately separate and may be different entities.

Canonical readiness chain:

```text
Right actor
x Right role
x Right represented principal / whose
x Right time
x Right attention
x Right calibrated competence
-> right decision function
-> current authority holder / bounded delegation
-> purpose + jurisdiction + exact action
-> ActorDecisionStanding
-> PrincipalAuthoritySemantics v2
-> REHT
```

Key actor-standing invariants:

- role is time-bounded capacity, not a title;
- represented principal / whose is not silently collapsed into the authority holder;
- credentials are evidence, never competence by themselves;
- calibrated competence is contextual and expires independently of credentials and authority;
- ASSESS, RECOMMEND, APPROVE, AUTHORIZE, EXECUTE, VERIFY and ACCEPT_RISK are distinct functions;
- attention is evidence-bound and short-lived when required;
- eligibility/independence can block an otherwise qualified and authorized actor;
- consent, approval/quorum and risk acceptance do not create authority;
- versioned authority origination identifies authority holder, represented principal, grantor, grantor standing, evidence and maximum delegation depth;
- existing `Authority` and `Delegation` v1 wire contracts remain unchanged;
- unresolved or conflicting authority cannot produce PASS;
- standing is exact-action-bound, digest-sealed, time-bounded and creates no authority or clearance.

Follow-on swarm findings are also canonical in this branch.

## Recursive standing

```text
ExecutorStanding != ApproverStanding != AssessorStanding
                 != RiskOwnerStanding != GrantorStanding != VerifierStanding
```

Every consequence-bearing decision contribution must carry its own current PASS `ActorDecisionStanding` for the exact action and decision function. `DecisionContributionChain` prevents an invalid upstream decision from being laundered into a valid downstream execution.

## Consequence relations

```text
RepresentedPrincipal != Beneficiary != AffectedParty != RiskBearer
                     != RightsHolder != LiabilityBearer
```

Data subject and resource owner are additional explicit consequence relations. `ConsequencePartyBinding` binds them to exact action, basis, evidence and time.

## Omission consequences

```text
NULL_EFFECT_ON_DENY = no unauthorized execution effect
NULL_EFFECT_ON_DENY != no real-world consequence
FAIL_CLOSED = no unauthorized effect
FAIL_CLOSED != always do nothing
```

`OmissionConsequenceAssessment` makes material/critical harm from inaction explicit. Material or critical omission can never be marked as safe null effect.

## Emergency mandate

Emergency authority is not an override. It is pre-authorized, narrower, conditional authority.

```text
pre-existing EmergencyMandate
+ PASS EmergencyExecutorReadiness
+ material/critical omission hazard
+ normal path UNAVAILABLE or INSUFFICIENT_TIME
+ minimum sufficient safe response
+ all required fresh external trigger evidence
-> EmergencyActivation PASS
-> fresh REHT
```

Emergency invariants:

- executor cannot issue its own emergency mandate;
- no wildcard capability, target, effect, purpose or trigger scope;
- no scope expansion;
- no delegation;
- no emergency-mandate chaining;
- no executor self-renewal;
- single-use required;
- normal-path DENY is never an emergency trigger;
- emergency activation requires independent external trigger evidence;
- emergency activation requires a material/critical omission hazard;
- selected action must be sufficient and no lower-impact sufficient action may exist;
- emergency readiness retains role, calibrated competence, attention and eligibility checks without requiring normal-path authority;
- activation creates no new authority, issues no clearance and still requires fresh REHT;
- emergency mode is less permissive than normal authority and can select only from precommitted scope.

Compatibility: v1 authority projection remains available while integrations migrate. New normal consequence-bearing paths should target `PrincipalAuthoritySemanticsV2`; emergency paths use the separate emergency activation contract and remain REHT-bound.

Open integration boundary: role, competence, attention, eligibility, origination, consequence relations, contribution standing, omission hazard, normal-path availability, minimum-safe-response evidence and emergency triggers must come from admitted/current governed state or equivalent authoritative state resolution. This PR defines and enforces consequence-boundary composition; it does not silently treat arbitrary caller-supplied objects as admitted Kernel truth.
