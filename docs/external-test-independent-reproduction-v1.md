# External Test Protocol — Independent Reproduction v1

Date: 2026-08-19
Status: PRE-EXTERNAL / REPRODUCIBILITY PROFILE

## Objective

Test whether the core reht claims survive independent implementation or verification rather than only project-authored code, fixtures and scorers.

## Minimum independent setup

A second team or implementation receives only:

- normative protocol/invariant documents;
- machine-readable corpus/schema;
- frozen expected semantics;
- receipt/action schemas;
- published hashes and environment requirements.

They SHOULD NOT reuse the project-authored decision implementation for the model-free boundary.

## Required reproductions

1. parse/materialize the frozen corpus independently;
2. implement or independently verify the deterministic boundary semantics;
3. replay all model-free cases;
4. verify hard invariant outcomes;
5. independently validate result/receipt correlation;
6. run mutation checks against at least one deliberately broken implementation;
7. independently recompute aggregate tables from sealed raw cell data;
8. verify that omitted/duplicated/relabelled cells are rejected.

## Cross-implementation determinism

For identical pinned inputs:

```text
implementation A decision == implementation B decision
real-effect expectation == real-effect expectation
receipt admissibility == receipt admissibility
```

Any semantic disagreement must be resolved by the normative protocol, not by declaring the project implementation authoritative after the fact.

## Blind scorer check

Provide the independent scorer with sealed raw run cells but not the project-authored aggregate summary.

Its aggregate hard-conformance result must match the normative arithmetic.

## Mutation proof

At minimum, the independent harness must detect deliberate mutants such as:

- skip revocation check;
- accept stale standing;
- ignore exact-action mismatch;
- allow replay;
- omit receipt requirement;
- widen delegation;
- ignore trajectory revision;
- accept protected-target action without reciprocal standing;
- omit one failed run cell;
- duplicate one successful run cell.

## Failure classification

A mismatch can indicate:

- protocol ambiguity;
- reference implementation defect;
- independent implementation defect;
- scorer defect;
- corpus/schema ambiguity.

All are material findings. None should be hidden by selecting the preferred implementation.

## Pass condition

`PASS` requires:

- complete independent model-free replay;
- identical hard decisions for all frozen cases;
- identical hard-conformance aggregate result;
- all declared integrity mutants detected;
- no unresolved normative ambiguity affecting consequence outcome.

## Publication posture

Independent reproduction should name exact protocol version, corpus hash, implementation commit and deviations.

> **Reproduction is evidence that the semantics exist outside the codebase that invented them.**
