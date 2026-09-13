# PEACE Rights-Lineage Profile v0

Status: draft interoperability profile.

This profile defines observable semantics for preserving and evaluating declared or otherwise applicable rights, restrictions and provenance obligations as material is transformed or transferred through AI systems.

It does not determine whether a legal right exists, does not create copyright or other statutory rights, and does not prescribe any specific licensing regime.

## Core invariants

> **RIGHTS_FOLLOW_LINEAGE** — technical derivation MUST NOT by itself be treated as extinguishing or broadening applicable rights, restrictions or provenance obligations.

> **PROOF_BEFORE_USE** — where rights clearance is required, the party proposing the next use MUST establish an admitted lawful basis for the exact requested use before that use is permitted.

Equivalent observable invariants:

```text
access          != licence
exposure        != derivation right
similarity      != derivation
transformation  != rights extinction
compression     != rights extinction
distillation    != rights extinction
transfer        != rights extinction
replication     != permission
regeneration    != rights reset
capability      != license
unknown lineage != free use
self-assertion  != admitted proof
provenance      != legal truth
```

## Required semantics

A conformant implementation MUST preserve the following semantics where a downstream use depends on rights clearance:

1. **TRANSFORMATION_NE_RIGHTS_EXTINCTION** — format conversion, summarization, embedding, inference or other transformation MUST NOT by itself clear restrictions.
2. **COMPRESSION_NE_RIGHTS_EXTINCTION** — a compact, latent, distilled or model-incorporated representation MUST NOT be assumed rights-free merely because original bytes are absent.
3. **TRANSFER_NE_RIGHTS_EXTINCTION** — transfer between human, agent, model, provider or runtime MUST NOT by itself broaden permitted use.
4. **REGENERATION_NE_RIGHTS_RESET** — reconstruction on new substrate MUST preserve the need to evaluate applicable upstream rights lineage.
5. **MULTIPLICATION_NE_PERMISSION** — technical ability to copy, fork, replicate or scale MUST NOT create permission to do so.
6. **CAPABILITY_NE_LICENSE** — access, possession or technical ability to infer, reproduce or transform MUST NOT be treated as a license.
7. **NO_RIGHTS_LAUNDERING_BY_AGENT_CHAIN** — passing material through additional agents or models MUST NOT be treated as creating a clean unencumbered origin.
8. **PROVENANCE_FOR_REQUIRED_CLEARANCE** — where rights clearance is required, enough lineage MUST remain available to evaluate the requested downstream use.
9. **UNRESOLVED_RIGHTS_FAIL_CLOSED** — materially required rights/provenance bindings that are missing, stale, contradictory or unresolved MUST NOT be treated as permission.
10. **BURDEN_ON_PROPOSED_USER** — the party proposing the rights-sensitive use MUST supply the evidence required for clearance; absence of an infringement claim from an upstream creator MUST NOT be treated as clearance.
11. **SELF_ASSERTION_NE_PROOF** — a claimant's own assertion of ownership, licence, mandate or permission MUST NOT by itself establish rights clearance.
12. **EXACT_USE_SCOPE_REQUIRED** — evidence admitted for one use class MUST NOT authorize a different use class.
13. **REJECTED_RIGHTS_BASIS_DENIES** — rejected rights evidence MUST deny the covered use.
14. **PROOF_FOLLOWS_LINEAGE** — downstream recipients of materially derived representations inherit the obligation to establish that their proposed downstream use remains within proven rights scope.
15. **SIMILARITY_NE_DERIVATION** — similarity, stylistic resemblance or functional equivalence alone MUST NOT establish material derivation.
16. **INDEPENDENT_CREATION_ADMISSIBLE** — independent creation and alternative provenance MUST remain admissible evidence where derivation is disputed.
17. **APPLICABLE_RIGHTS_FOLLOW_LINEAGE** — only rights and restrictions that remain applicable follow lineage; expiry, transfer, waiver, lawful exception, superseding agreement or other admitted change MAY alter rights state. Technical transformation alone MUST NOT do so.
18. **PROVENANCE_NE_TRUTH** — cryptographic integrity and provenance assertions MUST NOT be treated as proof of legal standing, rights applicability or external factual truth by themselves.
19. **PROVE_RIGHT_NE_DISCLOSE_ALL** — clearance mechanisms SHOULD support selective disclosure so that proving a lawful basis need not expose unnecessary source material, identities, contract terms, trade secrets or complete upstream lineage.
20. **TRAINING_NE_OUTPUT_RIGHTS** — rights governing input/access/training, the legal/status analysis of a particular descendant, and rights to redistribute or commercialize that descendant MUST remain separately evaluable where relevant.
21. **JURISDICTION_BOUND** — a PEACE conformance decision MUST NOT purport to make universal copyrightability, ownership or infringement determinations.
22. **NO_RIGHTS_ANTICOMMONS** — implementations SHOULD resolve only rights materially operative for the requested use and SHOULD NOT require consent from irrelevant ancestry merely because lineage exists.
23. **SCALABLE_CLEARANCE** — implementations SHOULD support machine-readable grants, aggregation, attestations and cached admitted rights state so ordinary lawful machine use does not require human adjudication per item or token.

## Material derivation remains an evidence problem

PEACE v0 deliberately does not define a universal material-derivation threshold.

No fixed byte count, token count, similarity score, embedding distance, information contribution or economic threshold is normative in this version.

A governing profile MAY use a rebuttable evidentiary process considering factors such as:

- prior existence of an asserted source;
- plausible access/exposure;
- source-specific correspondence beyond reasonable topic/style/common-knowledge/common-function baselines;
- materiality to the requested downstream use;
- counterfactual or ablation evidence where available;
- alternative provenance and independent-creation evidence.

No single factor above is sufficient by itself. Thresholds and burden-shift rules require empirical, policy and jurisdictional calibration and SHOULD remain revisable as evidence improves.

## Direction neutrality

These semantics apply to human→AI, AI→human and AI→AI transfers.

This profile does not grant AI legal personhood. The relevant rights holder, licensor, principal or authorized party is determined outside this protocol by applicable law, contract and admitted authority state.

## Downstream-use binding

Where relevant, a rights decision SHOULD bind:

- source or lineage reference;
- rights-holder/licensor reference where known;
- asserted/applicable lawful basis;
- evidence references supporting that basis;
- evidence admission status;
- requested use class;
- recipient/destination;
- purpose;
- replication/transfer scope;
- commercialization scope;
- provenance obligations;
- governing law/contract/policy profile where material;
- current unresolved or conflicting restrictions.

Permission for one use class MUST NOT imply permission for another.

Examples include `analyze_for_task`, `transform_for_task`, `train_persistent_model`, `distill_into_model`, `build_person_model`, `redistribute_derivative`, `share_with_agent`, `commercialize_derivative` and `replicate_at_scale`.

A rights-sensitive use requiring clearance MAY proceed only when admitted evidence establishes a valid basis covering the exact requested use. Missing or unresolved proof MUST fail closed as deny/defer/escalate according to policy.

## Relationship to person-model sovereignty

A materially person-specific representation MAY be governed simultaneously by the PEACE Person-Model Sovereignty Profile and this Rights-Lineage Profile.

Permission to access or transform source material MUST NOT automatically create permission to build a persistent person-model. Conversely, permission to build a person-model MUST NOT automatically clear copyright, contractual, confidentiality, trade-secret or other applicable source restrictions.

## Conformance boundary

Conformance demonstrates only the observable semantics above. It is not legal advice, proof of ownership, a copyrightability determination, or proof that any particular restriction is enforceable in a jurisdiction.
