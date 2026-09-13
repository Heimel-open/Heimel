# Semantic Identity Integrity

Kernel rule:

> Pattern equivalence must never silently become identity equivalence.

The governed world keeps these dimensions separate:

1. **Entity identity** — what thing is being referred to.
2. **State** — the current condition of that entity.
3. **Representation** — how the entity or state is observed, encoded, named, or rendered.
4. **Relations** — how entities are connected.
5. **Semantics** — what those relations mean in the active world/context.
6. **Provenance/evidence** — why a claim is believed.
7. **Standing** — whether the claim remains valid now.

Similarity, correlation, shared statistical structure, embedding proximity, model inference, or matching representations may support a candidate identity claim. They do not establish identity by themselves.

Identity equivalence must therefore be represented as an explicit fact (`same_as`, `same_entity_as`, or `identity_equivalent`) and must:

- refer to known canonical entities;
- carry explicit evidence references;
- remain subject to normal truth status, provenance, freshness, conflict, and standing rules.

The World Kernel fail-closes when an identity-equivalence fact lacks either canonical endpoints or evidence. This preserves the distinction between recognizing a pattern and asserting that two references denote the same governed entity.

Montgomery–Dyson is a useful intuition: the same statistical structure can appear in very different domains. Shared structure is evidence of a possible connection, not proof that the underlying objects are identical.
