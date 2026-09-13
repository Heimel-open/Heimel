# Persistent State Admission Boundary v1

## Normative rule

Persistence does not confer standing, trust, authority or clearance.

Any material that survives a worker, session or context boundary and is made available to another governed worker must be treated as a fresh persistent-state input. A file, memory entry, configuration fragment, instruction, handoff or cached artifact cannot become operative merely because it already exists in the workspace.

The required path is:

```text
persistent material
  -> evidence receive
  -> VALO state admission
  -> maintained Kernel state
  -> purpose-bounded governed projection
  -> PersistentStateBinding
  -> worker read-only input
```

A worker-produced artifact is therefore not eligible to become the next worker's persistent input directly. It must first cross the normal evidence/admission boundary.

## Executable contract

`PersistentStateBinding` binds the exact persistent bytes to:

- an admitted evidence object and its projected object digest;
- the exact Kernel state root;
- the exact governed workspace and workspace digest;
- the registered purpose;
- a persistent surface reference and kind.

The binding is read-only, cannot self-propagate, cannot create authority and cannot issue clearance.

`seal_persistent_state_binding()` fails closed unless the source is admitted evidence inside the governed projection and its `integrity_hash` equals the actual content digest.

`verify_persistent_state_binding()` must be called before persisted material is exposed to a worker. It fails closed on content mutation, workspace reuse, state-root mismatch, purpose drift, source-object change or loss of admitted standing.

Worker writes remain candidate artifacts. Existing artifact-context binding rules apply to those outputs, but artifact integrity or provenance alone does not make them eligible persistent input for a later worker.

## Re-evaluation against existing VALO boundaries

The August 2026 finding does not require moving authorization into the worker or adding model-specific prompt defenses to the trusted core. The existing architecture already contains most of the required containment:

- Kernel owns authoritative state;
- governed workspaces are non-authoritative projections;
- candidate artifacts do not create authority;
- conformance and fresh REHT authorization remain downstream;
- external PEP enforcement and Veritas remain unchanged.

The missing executable boundary was the input side of persistence: a durable file or memory surface could otherwise be treated as ambient worker context without proving that the exact bytes had passed admission and were bound to the current workspace. This contract closes that gap.

Prompt warnings may be useful defense in depth, but they are not an authorization or state-admission primitive.

## Research trigger

This invariant was made explicit after Papadopoulos, Shah, Zimmerman and Lindsey, “Mind Viruses: Self-Propagating Ideas in Multi-Agent LLM Systems,” arXiv:2608.10218 (2026). Their coding-agent experiments show propagation through shared files, memory and configuration across context wipes. VALO adopts the architectural lesson, not the paper's terminology or any model-specific mitigation.
