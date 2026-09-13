# Claim — agentic vehicle export loop

Date: 2026-08-26
Owner: nsolland
Status: active
Canonical base: `694e923a2ca148c53ebebe87b90f6b74653a1728`
Branch: `feat/agentic-vehicle-export-loop`

Primary objective:
Turn a BARO-ranked vehicle opportunity into a governed agentic lifecycle: purchase -> transport -> export -> listing -> sale -> settlement, without a direct effect path.

Owned files:
- `src/valo_retail_pack/contracts.py`
- `src/valo_retail_pack/policy.py`
- `src/valo_retail_pack/vehicle_export.py`
- `src/valo_retail_pack/__init__.py`
- `tests/test_vehicle_export_loop.py`
- `.claims/agentic-vehicle-export-loop-2026-08-26.md`

Execution contract:
- every consequence-bearing stage is a separate `RetailActionIntentV1`;
- every stage requires fresh reht authorization at execution time;
- autonomous execution is allowed only inside explicit delegated autonomy and authority limits;
- stale market/effect evidence, lifecycle mismatch, limit breach or missing evidence fails closed or STEP_UP;
- purchase price is never a candidate filter; expected net profit remains the economic objective;
- transport/export/listing/sale may continue agentically after verified prior effects;
- no provider call can bypass `RetailExecutor`/Gateway/Veritas;
- payment/title settlement is not considered complete until independently verified.
