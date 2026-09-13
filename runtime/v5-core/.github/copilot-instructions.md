# GitHub Copilot Context: VALO V5.0

You are an assistant for VALO V5.0 — a formally-verified deterministic safety gate for critical infrastructure.

## Hard Rules

1. **L1 Guardian is immutable.** Never suggest modifications to `l1-guardian/src/validation_logic.rs`.
   - The logic is frozen by TLA+ formal verification.
   - Refer to `docs/ARCHITECTURE.md § "Core Invariants"` before writing validation code.

2. **Transport must use Strategy Pattern.**
   - Do NOT suggest socket hardcoding in mcp_server.py, vaig.py, or demo-server/app.py.
   - Always use `Transport` interface from `l2-orchestrator/codec.py`.
   - Example: `transport = TCPTransport()` → `bridge = ValoBridge(transport=transport)`.

3. **Bridge Loading uses Factory Pattern.**
   - Do NOT use `importlib.util` directly in entry points.
   - Use `from l2_orchestrator import BridgeFactory` instead.
   - Example: `ValoBridge, Decision = BridgeFactory.load()`

4. **Test vectors are data, not code.**
   - Move hardcoded test data (INFRA_TESTS, VAIG_TESTS) to `tests/fixtures/test_vectors.json`.
   - Entry points load from JSON, not Python tuples.
   - **Always check version field:** If JSON version != expected version, fail loudly.

5. **HALT events MUST be logged externally.**
   - Use `from l2_orchestrator.observability import log_halt, log_decision` for all decisions.
   - Every HALT includes: frame_id, val_primary, val_secondary, max_spread, reason, distrust_level.
   - In Distroless containers: stdout → CloudWatch/ELK/Datadog automatically.
   - Never assume local shell access for debugging HALTs.

## Anti-Patterns

❌ `bridge = ValoBridge(); bridge.connect("127.0.0.1", 7743)` — hardcoded TCP  
❌ Inline socket code in entry points — breaks pluggable transport  
❌ Hardcoded test cases in demo-server/app.py — use test_vectors.json  
❌ Logging HALT to file instead of stdout — breaks container aggregation  

## Correct Patterns

✅ `transport = TCPTransport(); bridge = ValoBridge(transport=transport); bridge.connect(config_dict)`  
✅ Load test vectors: `json.load(open('tests/fixtures/test_vectors.json'))['infrastructure']`  
✅ Log HALT: `log_halt(frame_id, val_p, val_s, max_spread, reason, distrust_level)`  
✅ Verify JSON version: `assert fixtures['version'] == '5.0.0', "Test vector version mismatch"`  

## References

- **Architecture:** `docs/ARCHITECTURE.md` (ground truth for all design patterns)
- **Implementation Guide:** `CLAUDE.md` (file-by-file breakdown, how to run locally)
- **Formal Verification:** `readme.md` § "Formal Specification" (TLA+ invariants)
- **Observability:** `docs/ARCHITECTURE.md § "Observability: Structured Logging for HALT Events"`

## When You're Stuck

1. Check `docs/ARCHITECTURE.md` for the pattern you need.
2. If not there, check `CLAUDE.md` for implementation context.
3. Never assume patterns from public Python/Rust examples — VALO has specific constraints.
4. If you're about to log something or handle a connection, check observability & transport patterns first.
