# Ontology / Conformance Boundary v1

VALO separates meaning, operative state and authorization.

```text
candidate information
  -> state admission
  -> Kernel authoritative state
  -> purpose-bounded projection
  -> semantic contract
  -> Governed Semantic Workspace
  -> any worker
  -> deterministic state + semantic conformance
  -> execution binding
  -> VAIG evaluation
  -> fresh REHT authorization
  -> RACS decision expression
  -> external PEP enforcement
  -> execution
  -> Veritas
```

## Boundary

The ontology contract answers only: what canonical entity types, relationship types and predicates mean inside this workspace, and which alternate surface terms resolve to the same canonical term.

It does not decide whether a claim is true, whether information has standing, whether an actor has authority, or whether an action may execute.

Kernel remains the owner of operative state. REHT remains the authorization boundary. RACS expresses the downstream decision. A conforming external PEP performs enforcement.

## Deterministic guarantees

A semantic workspace is sealed over both the original governed workspace digest and the semantic contract digest. Changing projected state, ontology version, term definition, aliases or canonical values therefore changes the workspace digest.

Compilation fails closed if a projected Kernel entity or relationship type is not represented by the semantic contract.

Candidate return is checked for:

- canonical subject identity inside the projected workspace;
- provenance bound to that same canonical subject;
- predicate resolution to exactly one semantic term;
- explicit object references remaining inside the workspace;
- the ordinary Governed Workspace constraints for purpose, state drift, output kind, capability, target, effects and parameters.

Unknown predicate meaning returns `REDO`. Identity escape, ambiguous identity and explicit object escape return `DENY`. Tampered or wrongly bound workspace/candidate state returns `HALT`.

These are semantic/workspace conformance outcomes, not RACS execution outcomes. Conformance cannot issue or pre-issue a downstream execution decision.

A successful semantic conformance report records the exact canonical predicate term resolved for each claim. The execution binding carries the ontology id, ontology version and semantic contract digest forward to REHT context lineage.

## External systems

External ontologies, knowledge graphs, Lens-style standing systems or provider-specific semantic mappers may supply candidate mappings through adapters. They do not become Kernel dependencies and cannot create authoritative state, authority, clearance or execution permission.

The VALO invariant is:

> Same thing, same canonical identity. Same meaning, same sealed semantic term. Operative truth still belongs to Kernel state. Authorization still belongs to REHT.
