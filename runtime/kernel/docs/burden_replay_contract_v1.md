# Burden + Replay Contract v1

Status: adopted Kernel contract
Layer: governed state / evidence semantics
Authorization effect: none
Execution effect: none

## Purpose

VALO needs a domain-neutral way to make consequence exposure and decision reconstruction explicit without turning Kernel into an authorization or execution engine.

This contract adds two primitives:

1. Burden records: a consequence is bound to a measurement unit and period, quantified value/range, responsible bearer, evidence, assumptions/sources, and an enforcement/control reference.
2. Replay records: a governed boundary/object decision is reconstructable from pinned state, version, evidence, assumptions, requirement outcomes, burden references, failures, and change history.

A material change can invalidate an earlier replay record. Hard requirements are non-compensatory: a failed, held, or missing hard requirement blocks replay completeness regardless of other passing requirements.

## Boundary

Kernel records and evaluates replay completeness only. It does not:

- decide whether an action is authorized;
- convert a complete replay into execution clearance;
- execute an effect;
- infer external truth from a document merely because the document exists;
- treat a weighted score as a cure for a failed hard requirement.

Fresh REHT authorization, deterministic RACS outcome, PEP enforcement, and Veritas effect/outcome evidence remain separate boundaries.

## BurdenRecord

Minimum semantic binding:

`subject -> consequence -> quantity/range + unit + period -> responsible bearer -> evidence -> enforcement/control`

The record is sealed by a canonical digest. It explicitly carries `NO_AUTHORITY_CREATION`, `can_issue_clearance=False`, and `can_execute=False`.

The burden primitive is intentionally domain-neutral. A vertical pack can define burden types and units for finance, safety, operational risk, resource consumption, public cost, latency, environmental impact, legal exposure, or other consequence classes without changing Kernel authority semantics.

## ReplayRequirement

Each requirement has one status:

- `PASS`
- `FAIL`
- `HOLD`
- `MISSING`

`PASS` requires evidence. Every non-pass result requires a reason code. A requirement can be hard or advisory.

Hard requirements are non-compensatory. There is no aggregate score that can turn a failed hard requirement into a pass.

## ReplayRecord

A replay record binds:

- subject and version;
- boundary-state digest;
- explicit requirement results;
- evidence references;
- burden references;
- declared assumptions, including an explicit empty set;
- declared failure list, including an explicit empty set;
- declared change log, including an explicit empty set;
- creation time;
- canonical replay digest.

Replay means deterministic reconstruction from pinned inputs, state, evidence, assumptions, and requirement results. It does not mean token-by-token LLM replay.

A replay is `COMPLETE` only when:

- every hard requirement is `PASS`;
- assumptions are explicitly declared;
- failures are explicitly declared;
- change history is explicitly declared;
- no matching material change trigger has invalidated the replay.

## ChangeTrigger

A change trigger binds a prior replay digest and prior/new state digests to evidence of change. A material trigger must identify affected requirements.

For a matching subject/tenant, a material trigger observed at or after replay creation invalidates the prior replay until the affected scope is evaluated again and a new replay record is sealed.

This is the Kernel-side expression of fresh-state discipline: a previously reconstructable decision is not assumed to remain valid after material state change.

## Operational invariants

- Every burden has a measurable unit and period.
- Every burden identifies who bears it.
- Every burden carries evidence and an enforcement/control reference.
- Every replay is tied to an exact state digest and version.
- A hard failure cannot be averaged away.
- Missing declarations are incomplete, not implicitly empty.
- Material state change invalidates prior replay completeness.
- Replay completeness does not create authority.
- No direct effect path is introduced.

## External convergence note

The general operational pattern was independently reinforced by Garlando McCord Sr.'s public Data Center Placement Control Layer — Final Operational Completeness Addendum: explicit evidence minimums, burden-ledger fields, public replay, hard gates, version/change triggers, anti-drift and anti-gaming controls.

VALO adopts the general operational pattern only. The implementation remains domain-neutral and preserves VALO's existing architecture: governed state and evidence in Kernel, fresh authorization in REHT, deterministic disposition in RACS, enforcement at PEP/Gateway, and effect evidence in Veritas.
