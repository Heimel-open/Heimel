# Context Guidance Is Not Evidence

Status: adopted engineering and evaluation requirement
Source: https://arxiv.org/abs/2607.27250
Owner: Factory OS

## Decision

Instruction files, prompt context, repository guidance, retrieved memories, and agent-readable conventions SHALL be treated as workflow guidance only.

They are not correctness evidence, implementation attestation, promotion authority, or execution authority.

A worker claiming that it read or followed `AGENTS.md`, `CLAUDE.md`, a system prompt, a runbook, or equivalent context SHALL NOT increase the evidentiary status of its implementation by itself.

## Correctness evidence

Implementation correctness SHALL be established through evidence appropriate to the change, including:

- executable contracts and invariants
- deterministic tests and regression fixtures
- static or formal checks where applicable
- integration and boundary tests
- CI results bound to the exact commit under evaluation
- independent review or verification for promotion-sensitive changes
- observed postconditions where the work crosses into consequential execution

Narrative compliance reports MAY explain intent or workflow, but SHALL NOT substitute for these checks.

## Factory binding

Factory OS:
- may use instruction files to constrain workflow, file ownership, commands, test selection, cost, and provider behavior
- SHALL keep guidance separate from evidence in work and development receipts
- SHALL require exact commit/test bindings before promotion

Workers:
- MAY report which guidance they consumed
- SHALL NOT self-attest correctness from instruction compliance
- SHALL surface unknowns, skipped checks, failed checks, and unavailable evidence explicitly

Evaluators and reviewers:
- SHALL score the artifact and executable evidence rather than declared instruction compliance
- SHALL treat worker self-assessment as evidence of process state only
- SHOULD qualify coding agents separately by task class instead of assuming context quality transfers capability between agents

CI and verification:
- SHALL bind results to the evaluated SHA
- SHALL distinguish test execution from test adequacy
- SHALL not treat a green check as proof outside the scope actually exercised

REHT and execution governance:
- SHALL NOT consume instruction compliance as execution authority
- MAY consume verified technical evidence as one input to a broader authorization decision

## Invariants

- Context is guidance, not proof.
- Instruction compliance is not implementation correctness.
- A worker cannot independently attest its own consequential implementation.
- Current executable evidence overrides stale narrative context when they conflict.
- Passing tests are evidence only for the contracts and behaviors they actually exercise.
- Correctness evidence does not itself grant execution authority.
- Provider or model identity does not transfer correctness between task classes.

## Required receipt separation

Development and work receipts SHOULD represent at least:

- `guidance_refs`: instruction files, prompts, runbooks, retrieved context, and conventions consumed
- `evidence_refs`: tests, contracts, CI runs, formal checks, independent reviews, and observed outcomes
- `verification_status`: what was actually verified
- `verification_gaps`: what remains unverified or unknown

`guidance_refs` SHALL NOT satisfy a requirement for `evidence_refs`.

## Validation requirement

Conformance tests SHALL prove that:

1. declaring instruction compliance cannot mark an untested implementation verified;
2. a worker self-assessment cannot satisfy an independent-verification requirement;
3. evidence from another SHA cannot verify the current change;
4. missing executable evidence remains missing even when context is complete;
5. a green but out-of-scope test cannot attest an unexercised contract;
6. verified technical correctness cannot bypass REHT for consequence-bearing execution.
