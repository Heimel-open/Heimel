# RELEASE.md — VAIG Release and Version Policy

Status: pilot-ready core  
Current maturity: pre-1.0 / pilot  
Branch: `claude/claude-md-docs-74t2jg`

---

## Current maturity level

VAIG is **pilot-ready**, not production-certified.

Allowed claim: testable runtime governance stack with 321/321 passing tests.

Not allowed to claim: enterprise production certification, regulatory approval, insurance acceptance.

See `TEST_EVIDENCE.md` for the full evidence map.

---

## Versioning scheme

VAIG follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

| Component | Meaning |
|---|---|
| MAJOR | Breaking API change or architectural redesign |
| MINOR | New feature, backward-compatible |
| PATCH | Bug fix, documentation, backward-compatible |

Current version: `0.x` (pre-1.0 pilot phase)

Pre-1.0 minor versions may contain breaking changes with a migration note.

---

## Stable API boundary (current)

The following interfaces are considered stable within the 0.x series:

| Interface | Module | Stability |
|---|---|---|
| `EvidenceCondition` states | `src/vaig/rrp/evidence.py` | stable |
| `RefusalLifecycle` state machine | `src/vaig/rrp/core.py` | stable |
| `RiskContract` policy interface | `src/vaig/rrp/risk_contract.py` | stable |
| RRP receipt schema | `src/vaig/rrp/receipt.py` | stable |
| `GateEvent` / `GateDecision` | `vaig/agent_loop/gate.py` | stable |
| `AgentLoop.run()` | `vaig/agent_loop/loop.py` | stable |
| `WORMLog.append()` / `verify()` | `vaig/worm.py` | stable |
| `OverlaySignals` / `aggregate()` | `vaig/management_overlay/` | stable |
| ACS packet schema | `vacs/schema/acs_packet.schema.json` | stable (draft) |
| ACS receipt schema | `vacs/schema/acs_receipt.schema.json` | stable (draft) |

The following are **unstable / experimental**:

| Interface | Reason |
|---|---|
| `vaig/management_overlay/api/status.py` render functions | Display format may change |
| `vaig/economy/` module | Extension point; interface evolving |
| `reference_implementation/` | Reference only; not a public API |
| WHY Gate wiring | Spec implemented, runtime wiring deferred |
| Purple out-of-band monitoring | Deferred |

---

## Breaking-change policy

- Breaking changes require a MAJOR version bump
- Breaking changes are documented in `CHANGELOG.md` (not yet created)
- A migration note is provided for any change to the stable API boundary
- No breaking changes are introduced in PATCH releases
- Pre-1.0: breaking changes may appear in MINOR releases with explicit notice

---

## Test gate for release

A release is blocked if any of the following fail:

1. `pytest -q tests/` — must be 0 failures, 0 errors
2. All stable-API modules must have direct test coverage
3. `TEST_EVIDENCE.md` must be updated with the new test count and commit
4. No new external claims may be added without corresponding evidence in `TEST_EVIDENCE.md`

Current gate status: **GREEN** (321/321, 2026-06-27)

---

## Security review status

| Area | Status |
|---|---|
| WORM hash-chain tamper detection | implemented, tested |
| Append-only enforcement (fcntl + fsync) | implemented, tested |
| XOR encryption (architecture only) | not AES-256 — not suitable for regulated deployment |
| Authority delegation + expiry | implemented, tested |
| Input validation at system boundary | partial — see `TEST_EVIDENCE.md` |
| Formal security audit | not conducted |
| Penetration testing | not conducted |
| CVE scanning | not conducted |

For regulated (Annex III) deployments: replace XOR encryption with AES-256-GCM and harden WORM storage backend before use.

---

## Release checklist (pre-1.0 pilot)

- [ ] All tests green
- [ ] TEST_EVIDENCE.md updated
- [ ] CHANGELOG.md entry written
- [ ] Breaking-change migration note (if applicable)
- [ ] Security review status updated
- [ ] No hardcoded secrets, API keys, or threshold values
- [ ] External claim boundary verified
