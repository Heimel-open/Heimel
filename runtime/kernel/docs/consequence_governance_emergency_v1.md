# Consequence Governance and Emergency Mandate v1

Actor Decision Standing closes the final-actor readiness gap. Consequence governance extends that rule across the full causal decision chain and across cases where inaction itself can create harm.

## Every consequence-bearing contribution has standing

Executor standing is not sufficient when an approval, assessment, recommendation, authority grant, risk acceptance or verification is imported from another actor.

Canonical rule:

```text
ExecutorStanding != ApproverStanding != AssessorStanding
                 != RiskOwnerStanding != GrantorStanding != VerifierStanding
```

Every consequence-bearing contribution must bind its own current `ActorDecisionStanding` for the exact action and the exact decision function.

`DecisionContributionChain` therefore binds one exact action, PASS executor standing, every required decision contribution, PASS actor standing for each contributor, contribution type to decision function, distinct-actor / anti-self-contribution rules where configured, and shortest dependency validity.

A downstream actor cannot launder an invalid upstream decision into a valid execution chain.

## Whose is not who bears the consequence

Represented principal / whose must remain separate from the entities that experience, benefit from or bear the action's consequences.

```text
RepresentedPrincipal != Beneficiary != AffectedParty != RiskBearer
                     != RightsHolder != LiabilityBearer
```

Additional relations include data subject and resource owner.

`ConsequencePartyBinding` and `ConsequenceProfile` bind these relations explicitly to the exact action, basis, evidence and time. They do not create authority.

## No execution effect is not no real-world consequence

`NULL_EFFECT_ON_DENY` remains an execution invariant: a denied action cannot be converted into an unauthorized effect.

It must not be interpreted as:

```text
DENY == no real-world consequence
```

Inaction can itself be consequence-bearing. Missing a tax deadline, failing to isolate a compromised network, failing to stop a machine, failing to administer a time-critical treatment or failing to file a required notice can create material harm without any execution effect being emitted by VALO.

`OmissionConsequenceAssessment` explicitly classifies the consequence of not completing the proposed action. Material or critical omission cannot be marked `safe_null_effect=true`.

Canonical distinction:

```text
FAIL_CLOSED = no unauthorized effect
FAIL_CLOSED != always do nothing
```

## Emergency authority is not an override

Emergency execution must never be implemented as a bypass around ordinary authority.

```text
EmergencyMandate != override
EmergencyMandate = pre-authorized narrower conditional authority
```

The executor cannot create, widen, delegate, chain or renew its own emergency mandate. The mandate is issued ex ante by an independent authority source and is bounded by explicit executors, capabilities, targets, effects, purposes, trigger references, validity, risk ceiling, evidence and revocation registry.

Wildcard scope is forbidden. Emergency mandates are single-use by contract, non-delegable, non-chainable and cannot expand scope.

## Normal DENY is never an emergency trigger

A normal-path rejection does not make an emergency.

```text
normal DENY -> emergency activation
```

is invalid.

`NormalPathAssessment` distinguishes availability from decision outcome. Emergency activation requires the ordinary path to be independently established as `UNAVAILABLE` or `INSUFFICIENT_TIME`, combined with a material/critical omission hazard and the mandate's external trigger conditions.

A governance denial therefore cannot be converted into a bypass merely by relabelling the request as urgent.

## Emergency readiness is separate from emergency authority

An emergency mandate supplies the exceptional authority source. It must not erase the other readiness requirements.

`EmergencyExecutorReadiness` proves, without importing normal-path authority:

```text
Right actor
x Right active role
x Right represented principal
x Right time
x Right attention
x Right calibrated competence
x Right eligibility
```

This separation is necessary because requiring normal `ActorDecisionStanding` would incorrectly require normal authority before emergency authority could be used, while omitting readiness would allow the emergency mandate to bypass competence and attention controls.

## Minimum sufficient safe action

Emergency mode narrows the action space; it does not enlarge it.

`MinimumSafeResponseAssessment` binds the exact candidate action and requires both that the action is sufficient to control the established hazard and that no lower-impact sufficient action is available under the policy's candidate set.

This operationalizes the least-irreversible / minimum-sufficient-safe-response rule.

## Emergency activation

`EmergencyActivation` is a digest-sealed, exact-action, short-lived artifact combining:

```text
pre-existing EmergencyMandate
+ PASS EmergencyExecutorReadiness
+ material/critical OmissionConsequenceAssessment
+ UNAVAILABLE or INSUFFICIENT_TIME normal path
+ MinimumSafeResponseAssessment
+ all required fresh external trigger evidence
-> EmergencyActivation PASS
-> fresh REHT
```

Activation creates no new authority, issues no clearance and cannot execute. It activates only the scope already committed in the emergency mandate and still requires fresh REHT authorization.

Canonical invariants:

```text
NO_EMERGENCY_SELF_ISSUANCE
NO_EMERGENCY_SCOPE_EXPANSION
NO_EMERGENCY_DELEGATION
NO_EMERGENCY_CHAINING
NO_EMERGENCY_SELF_RENEWAL
NO_DENIAL_AS_EMERGENCY_TRIGGER
EXTERNAL_TRIGGER_EVIDENCE_REQUIRED
MATERIAL_OMISSION_HAZARD_REQUIRED
MINIMUM_SUFFICIENT_SAFE_ACTION
SINGLE_USE_REQUIRED
FRESH_REHT_REQUIRED
```

The emergency rail is deliberately less permissive than normal authority. It may select only from precommitted actions and can never convert a failed governance decision into broader discretion. `EmergencyActivation PASS` is a pre-commit standing artifact only; REHT remains the consequence-bearing authorization boundary.

## State ownership

Constructing any of these contracts does not make their contents operative truth. Contributor standing, consequence relations, omission hazard, normal-path availability, minimum-safe-response assessment, emergency mandate and trigger evidence must be admitted/current governed state or be resolved through an equivalent authoritative state-resolution path.

Emergency activation is therefore a governed safety rail, not an alternate source of truth or authority.
