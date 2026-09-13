# Ontology / conformance boundary work anchor

- Repository: `nsolland/valo-kernel`
- Canonical base: `42fcbcb62d512f43cc5fb5e75e1756c14299dfde`
- Branch: `feat/ontology-conformance-boundary`
- Owner: ChatGPT on behalf of Njål / VALO
- Active delivery: VALO-owned semantic contract bound into Governed Workspace and deterministically checked on candidate return
- Owned files: workspace semantic contracts, workspace compiler/conformance, focused tests, exports and architecture documentation
- Dependencies: authoritative Kernel entities/relationships, Governed Workspace v1, state admission, purpose, REHT boundary
- Non-goals: external ontology authority, named provider dependency, worker authorization, direct state mutation, external execution

Founder decision: ontology defines canonical meaning and identity binding; Kernel owns operative state; deterministic conformance rejects semantic drift before REHT. External systems may contribute mappings or assessments only through replaceable adapters.
