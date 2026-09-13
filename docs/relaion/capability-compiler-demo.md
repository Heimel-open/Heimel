# Capability Compiler demonstrator

Purpose: turn a requested outcome into the smallest tested composition of resources that can realize it, then produce evidence showing which dependencies are necessary.

This is a product demonstrator, not a claim that all capability emergence follows the TADA-BIRTH-01 mechanism.

## Flow

`outcome -> candidate resources -> composition search -> realization test -> minimal composition -> ablation -> capability certificate`

The compiler distinguishes:

- resource availability from realized capability;
- a declared resource capability from capability of the composition;
- realization from governance/authority;
- a working composition from a minimal working composition.

A certificate records the outcome, chosen resource IDs, aggregate cost, whether the outcome was realized, whether the composition is minimal, and whether removing each resource destroys realization.

## Finance-ops demo

Outcome: `invoice-ready-to-post`.

Candidate resources:

| resource | function | unit cost |
| --- | --- | ---: |
| ocr-premium | extract | 0.18 |
| ocr-local | extract | 0.03 |
| policy-agent | validate | 0.08 |
| erp-connector | post | 0.04 |
| human-reviewer | validate | 1.20 |

The deterministic demo requires extraction + validation + posting. No individual resource realizes the outcome. The compiler therefore searches compositions and returns the smallest working set; among equal-cardinality sets it selects the lowest-cost composition.

Expected certificate:

- `ocr-local`
- `policy-agent`
- `erp-connector`
- total cost: `0.15`
- minimal: `true`
- removing any member: capability no longer realized

## Commercial translation

The product question is not "which agent is best?" It is:

> What is the smallest governed composition of humans, models, tools and services that can actually deliver this outcome?

A production implementation can replace the deterministic evaluator with replay, shadow execution, sandbox tests, historical evidence or governed live evaluation. The compiler itself never grants authority. Any external effect remains subject to the canonical governed effect path at consequence time.
