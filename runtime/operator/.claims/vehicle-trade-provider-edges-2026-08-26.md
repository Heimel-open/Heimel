# Claim — vehicle trade provider edges

Date: 2026-08-26
Owner: nsolland
Status: active
Canonical base: `ff9157a1bb2e97086d4dae9e1c458d9c3c11f263`
Branch: `feat/vehicle-trade-provider-edges`

Primary objective:
Expose provider-neutral Operator edges for governed vehicle purchase, transport booking, export/declaration and foreign sale without creating alternate authority paths.

Owned files:
- `src/valo_operator/adapters/vehicle_trade.py`
- `src/valo_operator/adapters/__init__.py`
- `tests/test_vehicle_trade_adapters.py`
- `.claims/vehicle-trade-provider-edges-2026-08-26.md`

Execution contract:
- provider differences live only in `VendorConfig` and environment configuration;
- credentials never enter action contracts or evidence payloads;
- every external mutation still requires the normal Operator -> REHT -> Gateway path;
- HTTP success is not treated as effect; ConfiguredVeritas must read external state back;
- purchase, transport, export and sale each use independent idempotent external edges;
- no adapter creates authority, pricing policy, candidate selection or negotiation policy.
