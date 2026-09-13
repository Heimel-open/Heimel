# Completion-first execution profile routing

VALO Factory may select among replaceable execution profiles without owning or hard-coding the underlying hardware.

An execution profile binds the software/runtime dimensions that materially change task performance:

- handler / worker
- provider
- harness
- inference runtime
- model
- quantization
- cache strategy
- sandbox
- declared capabilities

Hardware remains behind provider/compute adapters. GPU model, accelerator vendor and physical node identity are not part of the Factory routing contract.

## Objective

The selector optimizes for verified correct completion, not token throughput or raw process success.

Ranking order is deterministic:

1. completion score derived only from independently verified outcomes
2. depth of verified evidence
3. verified latency
4. verified cost
5. stable profile ID tie-break

The completion score uses Laplace smoothing `(verified_completions + 1) / (verified_attempts + 2)`. An unseen profile starts neutral at 0.5. A verified failure moves it below neutral; a verified completion moves it above neutral.

`UNVERIFIED` execution observations do not improve completion score and do not contribute latency/cost ranking evidence. Provider exit code, CLI success or worker self-report therefore cannot manufacture a correctness signal.

## Hard filters

Before ranking, the selector filters profiles by:

- required capabilities
- allowed provider set when supplied
- allowed harness set when supplied
- allowed runtime set when supplied

Selection is advisory only. A selected profile receives no execution authority.

## Evidence boundary

A `VERIFIED_COMPLETE` or `VERIFIED_INCOMPLETE` observation must contain:

- execution receipt reference
- independent verifier reference
- exact task class
- exact execution profile reference

Observations are isolated by task class so evidence from one workload class cannot silently tune another.

The routing request and verified evidence set are deterministically hashed into the receipt. Replaying the same pinned request produces the same selection receipt.

## Authority boundary

Canonical separation remains:

`task/work intent -> profile suggestion -> governed execution path -> execution receipt -> independent verification -> future routing evidence`

The profile selector:

- does not execute
- does not hold credentials
- does not authorize
- does not change REHT or RACS semantics
- does not bypass global HALT or scoped-delivery controls
- does not treat performance evidence as authority

REHT remains the fresh execution authorization boundary. Verification evidence may improve future routing, but it cannot retroactively authorize an execution.

## What is adopted from heterogeneous local AI stacks

The useful pattern is not owning the workstation or GPU. It is measuring the complete execution configuration as one profile and learning which profile correctly completes each task class.

VALO keeps that learning surface while treating compute as replaceable capacity.
