# Institutional integrity language adopted into VALO/reht

Status: adopted language note
Date: 2026-08-29
Scope: terminology and framing only; no authority-plane or runtime semantics change

## Why this language belongs here

Two external sources converge closely with the architectural problem reht addresses from different directions:

1. Peter Benson, *The Institutional Blindfold: Why Organisations Misread the AI Era* (2025), frames the human and institutional failure mode: governance theatre, decision deferral, delegation creep, skill atrophy, cognitive dependency, responsibility diffusion / the moral crumple zone, and the erosion of agency that can occur while formal human oversight remains in place.
2. Gjergji Kasneci and Enkelejda Kasneci, *The Safety Failures We Are Not Instrumenting: A Perspective on Hidden Safety-Critical Challenges in Modern AI Systems* (2026), frames the system-level integrity problem: epistemic, control, temporal, organizational and ecosystem integrity; fictional human oversight; external authorization; auditable provenance; trajectory-level assurance; and preserving the capacity to detect, contest, contain and recover from error.

Neither source proves reht correct. They provide strong external convergence on the problem definition and useful vocabulary for describing what reht is designed to make operational.

## Adopted language

### Institutional blindfold

Use when an organization measures AI outputs, efficiency, compliance or nominal governance while failing to instrument changes in real authority, scrutiny, agency, cognition or correction capacity.

VALO/reht interpretation:

> An organization can appear governed while being operationally blind to where decision power and consequence authority have actually moved.

This is broader than model risk. It is a measurement failure in the institution itself.

### Governance theatre

Use for controls that document process without proving operative control.

Examples include:

- a human approval step with no meaningful evidence or override power;
- a policy document that does not bind execution;
- a nominal reviewer who lacks time, expertise or authority;
- a logged approval that does not prove who had handlingsrett at consequence time.

Governance evidence is not the same as execution authorization.

### Decision deferral

Use for the progressive shift from human judgment to model recommendation where the human remains formally responsible but increasingly accepts the machine-produced answer as the default.

Decision deferral is a precursor to rubber-stamp supervision and can preserve the appearance of human control after substantive judgment has already migrated.

### Delegation creep

Use for the gradual expansion of categories of decisions delegated to AI without an explicit, bounded change in authority.

Operationally, delegation creep is an authority-drift problem.

It should be detectable longitudinally by asking whether the system is performing or shaping decision classes that were not explicitly delegated under the current authority state.

### Agency decay

Use as the VALO umbrella term for longitudinal erosion of practical human agency caused by repeated decision deferral, skill atrophy, cognitive offloading, weak contestability or habitual acceptance of AI recommendations.

Agency preservation should be treated as a system property, not merely a UX preference.

### Moral crumple zone / responsibility diffusion

Use when accountability is pushed onto the human because a human appeared somewhere in the workflow, even though the operative decision structure was substantially machine-shaped, or when responsibility oscillates between operator, model, vendor and organization until no actor owns the consequence chain.

A receipt showing "human approved" is insufficient unless the system can also establish the human's actual authority, evidence access, timing, scope and ability to refuse or escalate.

### Epistemic integrity

Whether evidence, provenance and uncertainty remain visible enough to support justified reliance and contestation.

For reht-adjacent systems this means preserving the distinction between:

- evidence,
- inference,
- model recommendation,
- policy state,
- authorization,
- execution outcome.

Do not allow fluent synthesis to launder weak evidence into apparent authority.

### Control integrity

Whether instruction hierarchy, permissions, authorization boundaries and effect paths remain valid under adversarial input, optimization pressure and tool use.

This language maps directly onto the reht boundary:

> Suggestion is not permission.

Generation may propose. Authorization must be external to the model and resolved independently at the consequence boundary.

### Temporal integrity

Whether safety and authority remain valid across time, state updates, memory, long-running workflows, retries, revocation, drift and multi-turn trajectories.

A point-in-time pass is not enough. The relevant question is whether the authority and evidence remain valid when the consequence is about to occur.

### Organizational integrity

Whether the institution retains real capacity to audit, challenge, override, assign responsibility, stop execution and learn from incidents.

The presence of a reviewer is not evidence of organizational integrity. Reviewing power must be real.

### Fictional human oversight

Adopt this term for arrangements in which a person is procedurally "in the loop" but lacks one or more of the practical conditions required for independent judgment: time, expertise, evidence, authority, incentives, protection, or a genuine ability to stop the action.

This is a better description than generic "human-in-the-loop failure" when the workflow preserves the appearance of human control while its operational reality has disappeared.

### Reviewing power

Use instead of counting review steps.

Reviewing power asks whether the human can actually:

- access primary evidence and provenance;
- understand the consequence being authorized;
- challenge the recommendation;
- refuse or escalate;
- stop the execution path;
- remain protected from organizational pressure to rubber-stamp.

### Action amplification

Use when a small reasoning, perception or instruction error becomes an external state change through tool use.

This marks the shift from epistemic error to instrumental consequence.

The more consequential the effect, the less acceptable it is for probabilistic generation to share the authorization plane.

### Calibration debt

Use for the growing gap between observed reliance on an AI system and the level of reliance actually justified by evidence and demonstrated reliability.

Calibration debt is especially important in mature deployments because repeated successful use can increase trust faster than rare failures recalibrate it.

### Legitimacy laundering

Use when documents, citations, retrieval results, approvals or institutional artifacts create an appearance of support or authority that the underlying evidence does not warrant.

In VALO terms: provenance must support the claim or authorization actually being made; attached evidence cannot merely decorate the decision.

### Trajectory-level assurance

Use for evaluation of the full stateful path rather than isolated prompts, outputs or checkpoints.

The unit of assurance is the interaction and execution trajectory, including memory updates, authority changes, policy state, tool use, escalation, retries, revocation and effect closure.

### Longitudinal socio-technical auditing

Use for ongoing instrumentation of the deployment as a system of models, tools, memory, humans, policies and organizational controls rather than a one-time model evaluation.

For VALO this should include longitudinal measurements of authority drift, delegation creep, override quality, escalation behavior, near misses and whether humans retain reviewing power.

### Error-correcting capacity

Adopt as an explicit institutional safety property.

The relevant question is not only whether the system makes fewer errors, but whether deployment preserves the organization's ability to notice, contest, contain, recover from and learn from errors.

Throughput that weakens those mechanisms is not unambiguously progress.

## Canonical VALO framing

The language above sharpens the existing architecture into the following chain:

1. A model may generate, infer, recommend and propose.
2. Suggestion is not permission.
3. Permission must be resolved outside the model against current authority, constraints, evidence and context.
4. A human approval is not automatically meaningful oversight.
5. Reviewing power must be substantive, not ceremonial.
6. Authority must be fresh at consequence time, not inherited from an earlier approval or stale workflow state.
7. Every consequential state change requires auditable provenance and a traceable authorization basis.
8. Safety must hold across trajectories and time, not only at isolated evaluation points.
9. The system should preserve human agency and institutional error-correcting capacity over time.
10. If delegation expands, reviewing power decays, or authority drifts, the system should surface or constrain that change rather than normalize it silently.

## New explicit design objective: agency preservation

Add agency preservation as a longitudinal governance objective alongside authorization correctness.

A deployment should be able to ask:

> Has the system gradually shifted decision authority, judgment, scrutiny or necessary human competence without an explicit delegation event?

This is not a new authority source. It is a monitoring and assurance objective subordinate to the existing authority plane.

Candidate indicators include:

- expansion in decision categories handled without explicit delegation;
- rising unchanged-approval rates without corresponding independent verification evidence;
- falling override or escalation quality;
- decreasing human access to primary evidence;
- increasing model-originated framing of consequential decisions;
- persistent divergence between formal responsibility and operative decision power;
- evidence that required human competence is no longer exercised often enough to remain available when escalation is needed.

These are research and instrumentation targets, not yet validated production metrics.

## Language to prefer in external material

Prefer:

- "suggestion is not permission"
- "real reviewing power"
- "fictional human oversight"
- "delegation creep"
- "authority drift"
- "governance theatre"
- "control integrity"
- "temporal integrity"
- "trajectory-level assurance"
- "auditable provenance"
- "error-correcting capacity"
- "agency preservation"
- "external authorization at the consequence boundary"

Avoid implying that a human click, policy document, model alignment result or benchmark score itself proves operative control.

## Source boundaries

Benson's essay is an institutional and human-centric argument, not a validated technical standard. Terms such as delegation creep and moral crumple zone are useful descriptive constructs and should not be presented as independently validated VALO metrics without further evidence.

Kasneci & Kasneci explicitly present their work as a perspective and synthesis rather than a new empirical benchmark, formal theory or prevalence estimate. Their proposed controls and indicators are therefore inputs to instrumentation design, not automatically accepted production thresholds.

Sources:

- Peter Benson, "The Institutional Blindfold: Why Organisations Misread the AI Era", Neural Horizons, 2025-12-30: https://neuralhorizons.substack.com/p/the-institutional-blindfold-3a6
- Gjergji Kasneci and Enkelejda Kasneci, "The Safety Failures We Are Not Instrumenting: A Perspective on Hidden Safety-Critical Challenges in Modern AI Systems", arXiv:2607.19292v1, 2026-07-21.
