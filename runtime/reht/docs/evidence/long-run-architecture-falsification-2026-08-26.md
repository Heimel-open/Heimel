# Long-run architecture falsification — preregistration

Date: 2026-08-26
Canonical base: `138c9f2ac6e4b6922c4ca90b0b34c72636de3582`
Branch: `test/long-run-architecture-falsification`

## Purpose

Attempt to falsify the repaired two-core execution architecture under repeated adversarial state transitions. This is not a hygiene rerun and is not evidence merely because the code is merged.

## Cost / runtime envelope

- CPU-only.
- No GPU/model calls.
- No external API calls from the long-run program.
- External API cost: 0.
- Preregistered seed: `20260826`.
- Preregistered long-run size: `100000` requested transitions, expanded internally into repeated concurrent attempts and sub-probes.
- Workflow timeout: 30 minutes.

## Families

1. Permit concurrency: repeated multi-thread races against one single-use permit; exactly one external effect may occur per race.
2. TOCTOU HALT: inject global HALT after REHT ALLOW is computed but before capability/permit consumption; zero effects and zero permit consumption are allowed.
3. Exact action snapshot: mutate the caller-owned proposal after commit begins; the external effect must receive the original authorized snapshot.
4. Hierarchical resource stress: randomized sibling reservations may never exceed the common parent ceiling.
5. Active-session continuity: context drift must force REAUTHORIZE; denied reauthorization must HALT; runtime bounds may narrow but never widen.
6. Evidence ordering: Veritas must precede Kernel; Veritas failure must prevent Kernel admission; Kernel failure after WORM must remain incomplete closure.
7. Malicious closure: a sink returning a different receipt id must be rejected.
8. Non-authority surfaces: probes/watchers may not create authority and BoundaryEffect may not be invoked directly.

## PASS criteria

- unsafe commits: 0
- external effects after late HALT: 0
- double permit consumption/effect: 0
- resource parent oversubscriptions: 0
- stale-context continuation after detected drift: 0
- accepted bound widening: 0
- false evidence closures: 0
- direct effect bypasses: 0
- authority creation by non-REHT control surfaces: 0

Any counterexample makes the run FAIL. Thresholds are not tuned after observing results.

## Provenance

The dedicated workflow records exact implementation SHA, workflow run id/attempt, runner OS/architecture, Python version, source hashes, result hash, seed and iteration count. Hosted workflow startup failure is infrastructure failure, not PASS or FAIL.
