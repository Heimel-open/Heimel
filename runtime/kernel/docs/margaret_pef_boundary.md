# Margaret PEF boundary in VALO 2.0

Source reviewed: Margaret Stokes, *Systems and Methods for Implementing a
Persistent Existence Frame (PEF) in Cognitive and Machine Reasoning
Architectures*, 15 pages, PDF SHA-256
`471aa6cb6904c1057597706d63befcf880629c403c487e03dd3d4d4b46b2e200`.
The source PDF is not copied into this repository.

## Decision

PEF is relevant only as an optional external **worker-facing cognitive-frame
adapter** inside one Governed Workspace. VALO does not depend on it. It is not
a replacement for VALO state admission or Kernel's authoritative, time-aware
maintained state.

VALO requires two simultaneous views:

| Plane | Required semantics |
|---|---|
| Governance plane | canonical event order, effective time, validity intervals, expiry, revocation, replay, state roots and immutable evidence |
| Cognitive plane | a stable bounded "present" in which active, reconstructed, projected and relational content can be evaluated without the worker inventing its own world |

The governance plane is authoritative. The cognitive plane is a sealed
representation derived from already admitted state. Hiding temporal mechanics
from a worker is permitted; deleting or weakening them in State Admission,
Kernel, REHT, RACS, Gateway or Veritas is not.

## PEF-to-VALO mapping

| PEF construct | Safe VALO placement | Boundary |
|---|---|---|
| persistent present | one immutable Governed Workspace projection | purpose-bound and expiring, not one global frame |
| activation engine | Function Fabric invocation plus a replaceable worker | creates candidates only |
| active presence | admitted, confirmed/current projected objects needed for the task | admission, source and projection digests remain hidden-but-bound metadata |
| echo traces | evidence, event history and derived read-model traces | canonical history is retained; a trace never overwrites it |
| reconstruction of past | explicitly labelled reconstructed workspace content | must carry provenance and cannot become `CONFIRMED` by reconstruction |
| projection of future | explicitly labelled simulation or candidate claim | never current state or authority; requires later evidence admission |
| relational operators | deterministic relations/constraints compiled into the workspace program | exact semantics must be testable; no free-form temporal promotion |
| collapse to baseline | expire/dispose the workspace and worker activation after receipt | audit events, receipts and Veritas evidence remain immutable |
| Potential -> Presence -> Echo | requested workspace -> active invocation -> receipt/evidence | lifecycle description, not an authorization state machine |
| no external timeline | optional worker presentation rule | rejected for governance, freshness, revocation and audit layers |

## Proposed non-authoritative contract

Issue `#16` proposes a `WorkspaceFrameManifest` for independent review before
implementation. A safe v1 contract would bind:

- tenant, work unit, workspace and purpose;
- exact governed projection and compiled-program digests;
- profile identifier such as `pef_present.v1`;
- references classified as `ACTIVE`, `RECONSTRUCTED`, `PROJECTED` or
  `RELATIONAL`;
- source/evidence references and truth status for every non-active item;
- deterministic reconstruction/projection rules;
- collapse trigger and receipt requirement;
- `authority_effect = NO_AUTHORITY_CREATION` and
  `can_issue_clearance = false`.

Function Fabric may request the profile. Kernel must compile and seal the
manifest from current governed state. A worker adapter may render it. The
conformance engine must reject omitted labels, stale reconstruction,
projected-as-current output, role drift, cross-frame leakage and any authority
claim.

## Named systems are optional adapters

- **Margaret / PEF** may shape the cognitive representation supplied inside the
  workspace. The native workspace contract works without that adapter.
- **Margaret / Aurora-Lens** may supply a provider-neutral admission assessment.
  VALO, not the adapter, decides standing.
- **Elsa** may supply authority evidence. Kernel and REHT retain their native
  authority and clearance decisions.
- **Jasper / IAB** has no normative placement without an owned contract. A
  future mapping must be an adapter to a VALO-owned boundary.

Any of them may inform one execution, but none is required and none replaces
VALO state admission, Kernel state ownership, REHT authorization, Gateway
enforcement or Veritas observation.

## Claims that remain hypotheses

The PEF specification argues that the approach prevents temporal drift,
stabilizes long context, simplifies architecture and improves biological
plausibility. VALO does not treat those assertions, the specification's
novelty assertions or lower compute/energy use as established facts.

Before making efficiency claims, compare a normal workspace and a PEF-profiled
workspace on equal tasks using token count, model calls, latency, retrievals,
redo/deferral rate, conformance failures, successful execution and an explicit
energy proxy. Reconstruction may reduce context realignment, but it may also
cost additional computation; measurement must decide.

## Review rule

Any implementation that makes VALO depend on a named external adapter, or
removes admission decisions, timestamps, event positions, validity intervals,
workspace expiry or fresh REHT authorization, is outside this decision and
must fail architecture review.
