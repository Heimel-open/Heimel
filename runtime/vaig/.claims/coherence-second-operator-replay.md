# Claim — Coherence second-operator replay

Owner: ChatGPT
Status: complete
Canonical base: `aeaab37ae1eaf9b79dedb2a6c051609832ec5873`
Branch: `feat/coherence-second-operator-replay`
PR: `#196`

Primary objective:
- Provide a separately deployable VAIG second-operator service that deterministically replays the exact frozen pre-replay Coherence packet and returns a digest-bound replay artifact.

Owned files:
- `.claims/coherence-second-operator-replay.md`
- `vaig/coherence_replay.py`
- `vaig/coherence_replay_api.py`
- `tests/test_coherence_replay_service.py`
- `pyproject.toml`

Invariants:
- The service is evaluation-only and creates no execution authority or clearance.
- The frozen packet contains no prior replay outcome; second-operator execution is blind to the first outcome.
- The configured replay operator identity must differ from the evidence producer identity.
- The request packet digest must equal VAIG's own `replay_packet_digest` after canonical parsing.
- PASS is returned only when the canonical VAIG gate passes the replayed packet; other blockers remain OPEN/FAIL.
- The replay artifact and verification evidence are RFC 8785 + SHA-256 bound for platform interoperability.
- REHT remains the downstream execution-authorization boundary.

Validation coverage added:
- exact canonical replay packet PASS
- non-replay blocker remains OPEN
- packet digest mismatch fails
- evidence producer cannot be replay operator
- prior replay outcome rejected from frozen packet
- action retargeting rejected
- dedicated replay configuration and bearer token required
- health contract states no execution authority
- RFC 8785 artifact digest checked

Hosted GitHub Actions currently exits with the repository's existing `startup_failure` before jobs. The tests were therefore not executed by hosted Actions; no test failure was emitted.
