# Google Long Horizon harness adoption — #52

Status: ACTIVE
Owner: nsolland / ChatGPT execution worker
Canonical base: c06ad99b48b6bf99eae57af46ee38947e1721bd0
Branch: feat/long-horizon-harness-52

Owned files:
- lib/long_horizon_harness.py
- schemas/long-horizon-*.schema.json
- tests/test_long_horizon_harness.py
- config/ecosystem-adoptions.json
- docs/architecture/long-horizon-harness.md
- docs/build-orders/google-long-horizon-adoption-52.md
- bin/valo-orchestrator only if integration requires it

Dependencies:
- existing VALO Factory stdlib runtime
- external VAIG evaluation
- external REHT final authorization boundary
- RACS decision contract

Acceptance:
1. Runs can checkpoint and resume without replaying completed side effects.
2. Child work runs in isolated contexts with explicit owned files and bounded mission metadata.
3. Judge review is duty-separated, evidence-only, and cannot authorize or self-attest execution.
4. Memory compaction preserves immutable evidence references while bounding active context.
5. Sandbox lifecycle is explicit: create -> active -> sealed/released, with no authority effect.
6. Every consequence-bearing tool/action path requires an authorization callback representing VAIG -> REHT -> RACS immediately before execution.
7. No Google ADK or Vertex runtime dependency is introduced; patterns are adopted provider-neutrally.
