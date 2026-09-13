# ISO/IEC 42001 Runtime Conformance Mapping

Status: initial conformance-pack definition

## Position

ISO/IEC 42001 defines management-system controls covering AI lifecycle governance, verification and validation, deployment, operation and monitoring, event logging, intended use, responsibilities, suppliers, data provenance, impact assessment, and related evidence.

VALO does not claim that deploying VALO makes an organization ISO/IEC 42001 compliant.

The narrower claim is:

> VALO produces machine-verifiable execution evidence for specific ISO/IEC 42001 controls.

This pack maps applicable ISO/IEC 42001 controls to runtime constraints, consequence-time decisions, effect evidence, receipts, and deterministic replay. Controls that cannot be established by VALO runtime evidence remain explicitly outside or partially outside the pack.

## Evidence transformation

Traditional audit evidence commonly establishes that a policy, process, approval, plan, assessment, log, or responsibility record exists.

VALO adds an execution-evidence path:

`policy/control -> executable constraint -> consequence-time decision -> effect/no-effect -> immutable receipt -> deterministic replay -> audit evidence`

Documentation remains necessary where the standard requires it. Runtime evidence does not replace organizational, legal, human, supplier, impact-assessment, or management-system obligations that cannot be proven by execution traces.

## Initial control mapping

### A.6.2.4 — AI system verification and validation

ISO intent: verification and validation measures and criteria are defined and documented.

VALO evidence contribution:
- executable admissibility and validation criteria where criteria can be represented as machine-enforceable constraints;
- deterministic decision outcomes;
- receipts showing which criteria were evaluated and the resulting disposition;
- replay evidence demonstrating reproducibility of the governed decision.

Coverage: partial. VALO cannot by itself prove that the organization's complete V&V framework is adequate or management-approved.

### A.6.2.5 — AI system deployment

ISO intent: deployment is planned and appropriate requirements are met before deployment.

VALO evidence contribution:
- pre-effect gates for enforceable deployment requirements;
- fail-closed denial when required authority, constraints, provenance, evidence, or admissibility conditions are absent;
- receipts for deployment-related governed decisions.

Coverage: partial. Deployment planning and organizational approval remain external obligations unless separately represented and evidenced.

### A.6.2.6 — AI system operation and monitoring

ISO intent: necessary elements for ongoing operation, system/performance monitoring, repairs, updates, and support are defined and documented.

VALO evidence contribution:
- governed effect-path instrumentation;
- consequence-time evaluation;
- observable ALLOW / DENY / ESCALATE outcomes;
- evidence of blocked effects when runtime conditions fail.

Coverage: partial. VALO execution evidence does not establish the completeness of maintenance, support, or performance-monitoring processes.

### A.6.2.8 — AI system recording of event logs

ISO intent: event logging is enabled at appropriate lifecycle phases and at minimum while the AI system is in use.

VALO evidence contribution:
- verifiable decision and effect receipts;
- authoritative state references used at consequence time;
- outcome, constraint, authority, and provenance evidence;
- replayable records of governed execution;
- evidence for both permitted and precluded effects.

Coverage: strong for governed execution events, subject to system integration and retention requirements. It is not a claim that VALO automatically captures every event category required by an organization's ISO scope.

### A.7.5 — Data provenance

ISO intent: provenance of data used by AI systems is recorded throughout relevant lifecycles.

VALO evidence contribution:
- provenance as a first-class execution contract;
- provenance requirements can participate in admissibility decisions;
- receipts can bind execution outcomes to the provenance evidence evaluated.

Coverage: partial. VALO can enforce and evidence supplied provenance; it cannot establish missing upstream provenance merely from runtime observation.

### A.9.4 — Intended use of the AI system

ISO intent: AI systems are used according to intended uses and accompanying documentation.

VALO evidence contribution:
- intended purpose can be represented as governed purpose/constraint state;
- attempts outside admissible purpose can be denied before effect;
- successful and unsuccessful attempts produce evidence;
- deterministic replay can show why an action was admitted or precluded.

Coverage: strong where intended-use boundaries are expressible as executable constraints. Narrative or organizational intended-use obligations that are not machine-representable remain external.

### A.10.2 — Allocating responsibilities

ISO intent: AI lifecycle responsibilities are allocated among the organization and relevant external parties.

VALO evidence contribution:
- identity, authority, delegation, rights, and purpose contracts can make responsibility boundaries operational at execution time;
- stale, absent, or invalid authority can preclude effects;
- receipts provide evidence of the authority state actually evaluated for an attempted effect.

Coverage: partial. Contractual allocation, organizational agreement, and legal accountability remain external to the runtime unless authoritative representations are integrated.

## Core conformance principle

A documented control is not the same thing as an enforced control.

An enforced control is not the same thing as evidence that it operated correctly at a particular consequence boundary.

The VALO contribution is the third layer: evidence that the relevant executable governance condition was evaluated at consequence time and that the resulting effect or non-effect followed the governed path.

## Non-claims

This pack must not state or imply:
- that VALO is ISO/IEC 42001 certified;
- that VALO deployment makes a customer ISO/IEC 42001 compliant;
- that runtime receipts replace the complete AIMS or required organizational documentation;
- that every ISO/IEC 42001 control is executable;
- that evidence of enforcement proves the substantive adequacy of the underlying policy.

## Pack direction

The executable pack should ultimately represent each applicable control as:

`ISO control -> evidence objective -> VALO invariant/gate -> required runtime inputs -> expected receipt fields -> replay assertion -> coverage classification -> residual organizational evidence`

Coverage classifications:
- `RUNTIME_STRONG`
- `RUNTIME_PARTIAL`
- `OUTSIDE_RUNTIME`

The pack should fail closed on unsupported claims: absence of sufficient runtime evidence must never be converted into a conformance assertion.
