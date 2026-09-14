# HEIMEL Governance

Status: canonical repository governance, 2026-09-14

HEIMEL governs whether intent may become consequence. The mechanism therefore needs an explicit answer to a separate question: who may change HEIMEL itself?

## Current authority

Until an explicit transfer is recorded, Heimel-open/Heimel is the canonical repository for the HEIMEL open distribution. Repository maintainers are the current editors and release authorities.

Repository ownership is not permission to silently change normative execution semantics.

No customer, hosted Heimel service, model provider, adapter vendor, certification customer or Enterprise deployment becomes a trusted party merely by operating the software.

A self-hosted Open Heimel installation does not require Heimel or VALO Research to authorize, execute, replay or verify its local governed consequences.

## Normative surface

The normative execution properties are:

1. no direct effect path;
2. fresh authority at consequence time;
3. exact decision/effect binding;
4. fail closed on missing, stale or mismatched material state;
5. one-shot enforcement where a permit is used;
6. attributable consequence evidence;
7. evidence-backed state admission;
8. no mandatory phone-home for Open Heimel.

A component name, implementation language or deployment topology is not itself normative. The properties above are.

## Change control

A change is normative if a conforming implementation could behave differently because of it.

Every normative change must identify:

- the property or contract being changed;
- compatibility class: MAJOR, MINOR or PATCH;
- affected schemas, runtime behavior and integrations;
- security impact;
- conformance impact;
- required positive and negative cases;
- migration impact;
- decision provenance and target version.

A normative change is accepted only when the affected tests/conformance cases pass on the exact reviewed revision. Historical release tags must not be retargeted.

Editorial changes may fix wording, links and presentation without changing semantics.

## Compatibility

MAJOR changes may break an existing conforming implementation.

MINOR changes may add optional or new bounded capability without changing existing required behavior.

PATCH changes may clarify or correct implementation without changing the normative contract.

Compatibility claims must name the exact protocol/profile/version being claimed. "HEIMEL compatible" without a version/profile is not a conformance claim.

## Conformance and certification

The conformance material is open. Anyone may run it.

Passing the open suite means only that the tested implementation satisfied the named suite/profile/version under the recorded test conditions.

It does not mean:

- the implementation is officially certified by Heimel;
- the implementation is secure for every deployment;
- Heimel or VALO Research operated or approved the deployment;
- the implementation may use certification marks unless separately authorized.

Heimel Certified is a separate attestation service. A certification record must bind implementation identity, tested version/profile, suite version, result, issuance time, validity and attestation identity.

## Evidence and claims

Public maturity claims must point to reproducible evidence in `docs/EVIDENCE.yaml` or a versioned release receipt.

Every claim is classified as one of:

- measured: directly reproduced against named artifacts;
- claimed: asserted by a source but not independently reproduced here;
- synthetic: generated demonstration evidence;
- unknown: not established.

No score, test count or maturity statement may carry a stronger claim than its evidence supports.

## Transfer of governance

HEIMEL may later move normative stewardship to a standards body, foundation or consortium. Such a transfer must be explicit and versioned. It must identify the new canonical venue and effective version/date, freeze the last repository-owned normative release, and avoid simultaneous competing canonical sources.

## Security changes

Security fixes may be privately coordinated before disclosure. Urgency may shorten review time but does not remove versioning, provenance or later public change records.

## Separation from Enterprise

Heimel Enterprise may administer policies, identities, authority, tenancy, deployment and evidence operations for an organization. Enterprise does not own the meaning of the open execution standard and may not silently redefine the consequence boundary.

The trust rule is simple:

Open HEIMEL must remain independently inspectable, executable and verifiable. Enterprise may operate it at organizational scale; it does not become the source of truth for what the open mechanism means.
