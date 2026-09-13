# Inference Execution Substrate v1

Status: architecture boundary / adapter candidate

## Decision

VALO does not own model-serving infrastructure. Inference execution is a commodity substrate below VALO governance.

Superlinked SIE (`superlinked/sie`) is a current reference candidate for this substrate because it provides a unified serving layer across embedding, reranking, extraction, OCR and small-language-model workloads, including dynamic model loading and pooled accelerator capacity.

This is an adapter decision, not a trust decision. SIE or any equivalent provider may execute an admitted capability, but it cannot create authority, standing, policy, clearance, operative state or permission to cause an external effect.

## Boundary

```text
mandate / purpose
      |
      v
capability request
      |
      v
MAL / admissibility
      |
      v
VALO-governed workspace
      |
      v
inference adapter
      |
      v
SIE / equivalent model-serving substrate
      |
      v
candidate output
      |
      v
deterministic conformance
      |
      v
fresh Kernel context -> REHT -> RACS -> Gateway
      |
      v
external effect
      |
      v
Veritas evidence
```

The substrate answers: which admissible model/runtime can perform this computation efficiently?

VALO answers: what may be known, used, proposed and ultimately caused, under which authority and with which evidence?

These responsibilities must not collapse into one another.

## Required invariants

1. Model selection is non-authoritative. Routing, batching, fallback, model replacement, eviction or autoscaling cannot widen a capability or mandate.
2. Provider success is not authorization. A successful inference response never authorizes an external effect.
3. Provider output is candidate material. It must pass the same governed-workspace and execution checks as output from any other worker/model.
4. Model identity remains evidentiary. The exact provider/model/version/configuration used for material inference should be capturable in provenance and receipts where required by policy.
5. Hot-swappability is intentional. VALO contracts bind to capabilities and admissibility constraints, not to a single serving implementation unless policy explicitly requires one.
6. Failure remains fail-closed where model/provider properties are material to admissibility. Unknown or unverifiable required model attributes cannot silently fall back to a weaker model.
7. `NO_DIRECT_EFFECT_PATH` remains absolute. The inference substrate receives no independent route to tools, actuators or external systems outside the governed execution path.

## Adapter contract

A VALO inference adapter should minimally expose:

- capability class, e.g. `EMBED`, `RERANK`, `EXTRACT`, `OCR`, `GENERATE`
- requested admissibility constraints
- selected provider/model identifier and version where available
- execution configuration relevant to reproducibility or policy
- bounded input reference/provenance
- output reference/provenance
- execution status and failure class
- timing/resource metadata when material

The adapter must not expose an API that semantically means `authorize`, `approve`, `commit`, `execute_effect` or equivalent.

## SIE-specific position

SIE is currently treated as a reference implementation candidate for commodity inference execution, not as a VALO dependency and not as a governance component.

Useful properties include:

- one serving surface across heterogeneous model classes
- dynamic model loading/unloading
- shared accelerator utilization
- pooled/batched execution
- deployment as an infrastructure layer independent of VALO policy semantics

Those properties strengthen the existing VALO position that models, routing and compute are replaceable infrastructure. The durable boundary is the authoritative state, admissibility, governed workspace, fresh consequence-time authorization and verifiable effect evidence around the computation.

## Architectural consequence

VALO should integrate inference systems through provider-neutral adapters. SIE can be one adapter target. Replacing SIE with another compatible runtime must not require changing Kernel authority semantics, REHT/RACS contracts or the governed execution path.

Reference: https://github.com/superlinked/sie
