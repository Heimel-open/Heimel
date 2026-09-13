# Work anchor — Uniform + Whisker contract

Date: 2026-08-22

Owner: nsolland / current ChatGPT execution

Canonical base: `9532aaad342657375b4191c49b51f9bfaac7e99e`

Branch: `feat/uniform-whisker-contract`

Owned files:
- `src/valo_kernel/contracts/uniform_whisker.py`
- `src/valo_kernel/kernel/uniform.py`
- `tests/test_uniform_whisker.py`
- `tests/test_uniform_bridge.py`
- this work anchor

Dependency: existing Kernel execution-context, authority, state and canonical-digest semantics.

Active delivery: consolidate the already-existing portable governed execution context and distributed local checks into two explicit reusable abstractions without moving authorization into Kernel.

Invariant boundary:
- `GovernedUniform` carries/binds governed context; it never creates authority or clearance.
- `build_governed_uniform` projects the existing execution context into the portable uniform; it resolves no new authority.
- `WhiskerResult` is local evidence/control output; PASS is not execution authorization.
- shadow whiskers observe only and cannot block.
- enforce whiskers may stop a transition locally with BLOCK or STEP_UP.
- deterministic/cheap probes execute before more expensive probabilistic probes.
- REHT remains the execution-authorization boundary.
- this implementation does not promote the L4 governed consequence cut-set research candidate to a production invariant.

No files owned by open PR #51 are modified.