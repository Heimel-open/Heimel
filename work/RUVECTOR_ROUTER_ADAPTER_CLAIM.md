# RuVector Router Adapter Claim

Owner: ChatGPT / GPT-5.6 Sol
Status: ACTIVE
Canonical base: 301c2c76c9000b53581b85f7a93fb7f5e400b3ce
Branch: feat/ruvector-router-adapter

Owned files:
- lib/task_router.py
- bin/valo-route
- connectors/ruvector/package.json
- connectors/ruvector/router.cjs
- tests/test_task_router.py
- docs/architecture/semantic-router-adapter.md
- work/RUVECTOR_ROUTER_ADAPTER_CLAIM.md

Dependency:
- @ruvector/router pinned exactly to 0.1.30 inside the isolated connector.

Invariants:
- Routing is selection only. It grants no authority and executes nothing.
- REHT remains the execution authorization boundary.
- Router input uses precomputed embeddings; the connector does not own embedding/network access.
- Router adapters are replaceable through a provider-neutral Python interface.
- Unknown, malformed or authority-bearing router output fails closed.
