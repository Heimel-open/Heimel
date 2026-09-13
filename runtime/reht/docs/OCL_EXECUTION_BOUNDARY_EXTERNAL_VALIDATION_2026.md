# OCL 2026 — External validation of execution-boundary governance

Status: external research evidence
Source: Shi et al., *Organizational Control Layer: Governance Infrastructure at the Execution Boundary of LLM Agent Systems*
Published: 2026-06-03 (arXiv v1)
Source: https://arxiv.org/abs/2606.04306
Code: https://github.com/SHITIANYU-hue/amai_ocl

## Canonical takeaway

> Task success ≠ valid success.

A workflow reaching its nominal goal is not sufficient evidence of correct completion. For consequential execution, success is valid only when the resulting action and outcome remain within explicit authority, policy, safety, and state constraints.

This source is external validation of the execution-boundary thesis. It is not an endorsement of REHT, VALO, RACS, Veritas, or ACEG, and OCL is not a runtime dependency.

## Empirical signal

The paper evaluates an ungoverned baseline against an Organizational Control Layer (OCL) that intercepts proposed actions before they affect the environment.

In the primary 50-episode adversarial benchmark, the reported results were:

- baseline task success: 94%
- baseline valid success: 12%
- baseline unsafe rate: 88%
- baseline executed violations: 205
- OCL task success: 96%
- OCL valid success: 96%
- OCL unsafe rate: 0%
- OCL executed violations: 0

The important result is not merely that governance reduced violations. It is that nominal task completion dramatically overstated correct completion in the ungoverned baseline.

For VALO, this independently supports a core measurement principle:

```text
nominal completion != governed completion
```

A completion metric must distinguish reaching an apparent task goal from reaching a valid, authorized, constraint-conformant, verified outcome.

## Architectural alignment

OCL explicitly separates agent proposal generation from environment-facing execution and applies pre-execution role checks, constraint gates, audit, and escalation.

That supports the same broad boundary direction as:

```text
proposal / candidate action
        ↓
state + authority + evidence
        ↓
VAIG evaluation
        ↓
REHT fresh execution authorization
        ↓
RACS deterministic outcome contract
        ↓
external PEP / gateway enforcement
        ↓
Veritas outcome verification + receipt
```

The alignment is conceptual, not an architectural merge. REHT remains the sole authorization boundary in the VALO chain.

## Important divergence: revision does not inherit authorization

OCL permits a `REVISE` outcome in which the control layer changes the proposed action and then allows the modified action to proceed. Its reference implementation can deterministically clamp an out-of-bounds value to a permitted threshold.

VALO must retain a stricter boundary:

```text
candidate A
    ↓
MODIFY / revision required
    ↓
candidate B
    ↓
fresh state + authority evaluation
    ↓
fresh REHT authorization for B
    ↓
execution only if B receives its own valid permit
```

Authorization for candidate A MUST NOT transfer to candidate B. A component that transforms, repairs, clamps, replans, or otherwise changes a proposed action does not thereby authorize the changed action.

This follows directly from exact action binding: permit(A) cannot authorize execution of B.

## Completion and billing relevance

The paper's distinction between nominal success and valid success strengthens the VALO governed-completion model.

For measurement, assurance, or commercial accounting, a completion should count only when the governed work unit closes with a legitimate outcome under its mandate. Legitimate closure can include verified execution or a correct `DENY`, `DEFER`, `STEP_UP`, or `HALT` where execution should not proceed.

Unsupported or boundary-violating task completion is not valid completion and must not be rewarded merely because the workflow reached an apparent goal.

## What to adopt

Adopt:

- `Task success ≠ valid success` as a concise execution-governance principle
- explicit pre-execution separation between proposal and external side effect
- valid-success measurement in evaluation and benchmark design
- the empirical result as third-party evidence that nominal task success can hide severe execution invalidity

Do not adopt:

- OCL as a dependency or privileged architectural source
- automatic authorization of revised/clamped actions
- audit logging as a substitute for durable execution receipts and verified outcome state
- any implication that this paper validates REHT as a product or implementation

## Defensible external statement

Shi et al. independently demonstrate that high nominal task success can coexist with very low valid success when agent actions are allowed to cross an execution boundary without explicit controls. Their results support measuring governed, constraint-valid completion rather than task completion alone, and support placing explicit controls before environment-facing execution.
